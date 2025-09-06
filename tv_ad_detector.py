from datetime import datetime, timedelta
import os
from typing import Any, Dict, List, Union

import cv2
import imagehash
from apscheduler.schedulers.background import BackgroundScheduler

from config import logger, reader, settings, spellcheck
from shot_boundary_detection import new_bumper_detection
import argparse
from utils import (
    add_seconds_to_datetime,
    classify_board,
    datetime_to_string,
    get_ad_borders,
    get_end_timestamp,
    get_frame_dhash,
    get_timestamp,
    string_to_datetime,
    get_bumpers_dhashes,
)

DHASH_THRESHOLD = int(settings.DHASH_THRESHOLD)
BOARD_TIME_SEPARATION = int(settings.BOARD_TIME_SEPARATION)
MAX_CORRUPT_FRAMES = int(settings.MAX_CORRUPT_FRAMES)
DHASH_FREQUENCY = int(settings.DHASH_FREQUENCY)
VIDEO_END_PADDING_FRAMES = int(settings.VIDEO_END_PADDING_FRAMES)

placa_inicio: str = settings.START_EVENT_NAME
placa_fin: str = settings.END_EVENT_NAME


def process_events(
    events: Dict[str, Any], start_time_str: str, duration: Union[int, float]
) -> Dict[str, List[Dict[str, str]]]:
    reduced_data: List[Dict[str, str]] = []
    last_event_type: Union[str, None] = None
    last_timestamp_dt: Union[datetime, None] = None
    event_list = list(events["items"].items())

    for timestamp_str, event_type in event_list:
        current_timestamp_dt = string_to_datetime(timestamp_str)

        if last_event_type is None and event_type == placa_fin:
            reduced_data.append({placa_inicio: start_time_str, placa_fin: timestamp_str})

        elif event_type != last_event_type:
            if event_type == placa_fin:
                reduced_data.append(
                    {
                        placa_inicio: datetime_to_string(last_timestamp_dt),
                        placa_fin: timestamp_str,
                    }
                )

        elif (current_timestamp_dt - last_timestamp_dt) > timedelta(seconds=BOARD_TIME_SEPARATION):
            if last_event_type == placa_inicio:
                reduced_data.append(
                    {
                        placa_inicio: datetime_to_string(last_timestamp_dt),
                        placa_fin: datetime_to_string(current_timestamp_dt - timedelta(seconds=1)),
                    }
                )
            else:
                reduced_data.append(
                    {
                        placa_inicio: add_seconds_to_datetime(1, last_timestamp_dt),
                        placa_fin: datetime_to_string(current_timestamp_dt),
                    }
                )

        if timestamp_str == event_list[-1][0] and event_type == placa_inicio:
            reduced_data.append(
                {
                    placa_inicio: timestamp_str,
                    placa_fin: get_end_timestamp(start_time_str, duration),
                }
            )

        last_event_type = event_type
        last_timestamp_dt = current_timestamp_dt

    return {"items": reduced_data}


def process_frame_easyocr(
    frame: Any,
    current_time: datetime = datetime.now(),
    events: Dict[str, Any] = {"items": {}},
    update_events: bool = True,
) -> str:
    frame_text: List[str] = reader.readtext(frame, detail=0)
    manual_classification: str = classify_board(frame_text)
    if manual_classification == placa_fin or manual_classification == placa_inicio and update_events:
        events["items"][datetime_to_string(current_time)] = manual_classification
    return manual_classification


def check_hash_similarity(all_hashes: List[imagehash.ImageHash], found_hash: imagehash.ImageHash) -> bool:
    for h in all_hashes:
        if h - found_hash < DHASH_THRESHOLD:
            return True
    return False


def bumper_dhash_detector(
    video_file: str, dhashes: List[imagehash.ImageHash], start_date_str: str
) -> Union[Dict[str, Any], str]:
    try:
        events: Dict[str, Any] = {"items": {}}
        cap = cv2.VideoCapture(video_file)
        max_corrupt_frames: int = MAX_CORRUPT_FRAMES
        frame_counter: int = 0
        logger.debug(f"bumper_dhash_detector: processing video with {cap.get(cv2.CAP_PROP_FRAME_COUNT)} frames")

        while cap.isOpened():
            # Captura de frames
            ret, frame = cap.read()
            frame_counter += 1

            if frame_counter >= (cap.get(cv2.CAP_PROP_FRAME_COUNT) - VIDEO_END_PADDING_FRAMES):
                cap.release()
                break

            if ret:
                if frame_counter % DHASH_FREQUENCY == 0:
                    frame_hash = get_frame_dhash(frame)
                    is_board = check_hash_similarity(dhashes, frame_hash)
                    if is_board:
                        process_frame_easyocr(
                            frame,
                            get_timestamp(cap.get(cv2.CAP_PROP_POS_MSEC), start_date_str),
                            events,
                        )

            else:
                max_corrupt_frames -= 1
                logger.debug(
                    f"bumper_dhash_detector frame {frame_counter} is corrupted: corrupted counter {MAX_CORRUPT_FRAMES - max_corrupt_frames}/{MAX_CORRUPT_FRAMES}"
                )

                if max_corrupt_frames == 0:
                    logger.error("Processing video file: " + video_file + " Corrupt video")
                    cap.release()
                    return "CORRUPT"

    except Exception as e:
        logger.error("Processing video file: " + video_file + " Error: " + str(e))
        return "ERROR"
    return events


def placa_detector(
    video_file: str, duration: Union[int, float], dhashes: List[str], start_date_str: str, channel: str
) -> Union[Dict[str, Any], str]:
    try:
        dhashes
        has_run_sbd: bool = False
        original_dhashes_length: int = len(dhashes)
        if original_dhashes_length == 0:
            logger.info(f"No Bumpers available for Channel: {channel} running bumper discovery")
            sbd_result = new_bumper_detection(video_file, channel)
            if sbd_result == "TERMINATED":
                return sbd_result
            dhashes = [imagehash.hex_to_hash(dhash) for dhash in get_bumpers_dhashes(channel)] or []
            if len(dhashes) == 0:
                logger.error("No Bumpers available for detection for: " + video_file + " Channel: " + channel)
                return "ERROR"
            has_run_sbd = True
        raw_events = bumper_dhash_detector(video_file, dhashes, start_date_str)
        if type(raw_events) is str:
            return raw_events
        events = process_events(raw_events, start_date_str, duration)

        # Si process_events devuelve una lista vacia se corre el shot boundary
        video_date = string_to_datetime(start_date_str)
        video_hour = video_date.hour
        min_hour = settings.TV_SCHEDULES_SBD[0]
        max_hour = settings.TV_SCHEDULES_SBD[1]

        if len(events["items"]) == 0 and min_hour < video_hour < max_hour and not has_run_sbd:
            sbd_result = new_bumper_detection(video_file, channel)
            if sbd_result == "TERMINATED":
                return sbd_result
            dhashes = [imagehash.hex_to_hash(dhash) for dhash in get_bumpers_dhashes(channel)] or []

            if len(dhashes) == original_dhashes_length:
                return events

            raw_events = bumper_dhash_detector(video_file, dhashes, start_date_str)
            if type(raw_events) is str:
                return raw_events
            events = process_events(raw_events, start_date_str, duration)
        return events

    except Exception as e:
        logger.error("Processing video file: " + video_file + " Error: " + str(e))
        return "ERROR"
    
    
if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="TV Ad Detector")
    parser.add_argument("--channel_name", type=str, default="test_channel", help="Name of the TV channel")
    parser.add_argument("--video_file", type=str, help="Path to the video file")
    parser.add_argument(
        "--start_date",
        type=str,
        default=datetime.now().strftime("%Y-%m-%d 00:00:00"),
        help="Start date of the video in 'YYYY-MM-DD HH:MM:SS' format (default: today at 00:00:00)",
    )
    parser.add_argument("--duration", type=int, help="Duration of the video in seconds")
    args = parser.parse_args()

    # Example usage: get bumpers dhashes and video duration
    dhashes = get_bumpers_dhashes(args.channel_name)
    cap = cv2.VideoCapture(args.video_file)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    if args.duration:
        duration = args.duration
    else:
        duration = frame_count / fps if fps > 0 else 0
    
    cap.release()

    # Assume start_date_str is now

    if not os.path.exists(settings.BUMPER_DETECTION_DIR):
        os.makedirs(settings.BUMPER_DETECTION_DIR)
        
    result = placa_detector(
        args.video_file,
        duration,
        dhashes,
        args.start_date,
        args.channel_name,
    )
    print(result)