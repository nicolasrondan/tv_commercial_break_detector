import os
import time
from datetime import datetime
from typing import Any, List, Optional, Tuple

import cv2
import pandas as pd
from scenedetect import ContentDetector, SceneManager, StatsManager, open_video
from tqdm import tqdm

from config import reader, settings
from utils import classify_board, datetime_to_string, get_frame_dhash, format_channel_name


def get_event_times(events_dataframe: pd.DataFrame) -> List[int]:
    event_times: List[int] = []
    for _, event_row in events_dataframe.iterrows():
        event_times.append(parse_time_to_seconds(event_row.video_time))
    return event_times


def parse_time_to_seconds(time_minutes_seconds: str) -> int:
    str_time = time.strptime(time_minutes_seconds, "%M:%S")
    seconds = str_time.tm_min * 60 + str_time.tm_sec
    return seconds


def get_scene_duration(scene: pd.Series) -> float:
    return float(scene["End_Seconds"]) - float(scene["Start_Seconds"])


def list_scenes(scenes: pd.DataFrame, fps_second: int, f_skip_factor: int) -> List[int]:
    scenes_list: List[int] = []
    time_skip: float = f_skip_factor / fps_second

    for _, scene in scenes.iterrows():
        scene_duration = get_scene_duration(scene)
        if settings.BUMPER_TIME_WINDOW[0] < scene_duration < settings.BUMPER_TIME_WINDOW[1]:
            n = 1
            while n * time_skip < scene_duration:
                scenes_list.append(int(scene["Start_Frames"]) + n * f_skip_factor)
                n += 1

    return scenes_list


def count_words_in_ocr(ocr: List[str]) -> int:
    counter: int = 0
    for line in ocr:
        counter += len(line.split())
    return counter


def find_new_bumpers_sbd(
    scenes_df: pd.DataFrame, video_path: str
) -> Tuple[Optional[Any], Optional[Any], Optional[Any], Optional[Any]]:
    video_capture = cv2.VideoCapture(video_path)
    fps: float = video_capture.get(cv2.CAP_PROP_FPS)
    video_scenes: List[int] = list_scenes(scenes_df, int(fps), 10)  # skip frame factor
    video_scenes.sort()
    video_scenes_unique: List[int] = []
    for num in video_scenes:
        if video_scenes.count(num) == 1:
            video_scenes_unique.append(num)

    frame_count: int = 0
    success: bool = True

    images_inicio: List[Any] = []
    images_fin: List[Any] = []
    for frame_number in tqdm(video_scenes_unique, desc="Analyzing scene for bumpers"):
        while success:
            success, image = video_capture.read()

            if not success:
                frame_count += 1
                break

            if frame_count == frame_number:
                frame_text: List[str] = reader.readtext(image, detail=0)
                placa_detected: str = classify_board(frame_text)
                print(f"Frame {frame_count} classified as {placa_detected}")
                if placa_detected == settings.START_EVENT_NAME:
                    images_inicio.append(image)

                if placa_detected == settings.END_EVENT_NAME:
                    images_fin.append(image)

                frame_count += 1
                break
            frame_count += 1

    video_capture.release()
    inicio_image, inicio_hash = (
        (images_inicio[0], get_frame_dhash(images_inicio[0])) if len(images_inicio) > 0 else (None, None)
    )
    fin_image, fin_hash = (images_fin[0], get_frame_dhash(images_fin[0])) if len(images_fin) > 0 else (None, None)

    return inicio_image, inicio_hash, fin_image, fin_hash


def find_scenes(video_path: str, detector: Any) -> pd.DataFrame:
    video = open_video(video_path)
    scene_manager = SceneManager(stats_manager=StatsManager())
    scene_manager.add_detector(detector)
    scene_manager.detect_scenes(video)

    scenes_df = pd.DataFrame(
        columns=[
            "Start_Timecode",
            "Start_Seconds",
            "Start_Frames",
            "End_Timecode",
            "End_Seconds",
            "End_Frames",
        ]
    )
    scene_list = scene_manager.get_scene_list()
    num_scenes = len(scene_list)
    for idx, scene in enumerate(tqdm(scene_list, desc="Detecting scenes for bumper detection", unit="scene")):
        scene_dict = {
            "Start_Timecode": scene[0].get_timecode(),
            "Start_Seconds": scene[0].get_seconds(),
            "Start_Frames": scene[0].get_frames(),
            "End_Timecode": scene[1].get_timecode(),
            "End_Seconds": scene[1].get_seconds(),
            "End_Frames": scene[1].get_frames(),
        }
        scenes_df = pd.concat([scenes_df, pd.DataFrame(scene_dict, index=[0])], ignore_index=True)

    return scenes_df


def new_bumper_detection(video: str, channel: str) -> str:
    scene_df_content: pd.DataFrame = find_scenes(video, ContentDetector(threshold=11))
    inicio_image, inicio_hash, fin_image, fin_hash = find_new_bumpers_sbd(scene_df_content, video)

    if str(inicio_hash) == "TERMINATED":
        return "TERMINATED"
    current_date: datetime = datetime.now()

    formatted_channel: str = format_channel_name(channel)
    formatted_date: str = datetime_to_string(current_date).replace(" ", "_")
    if inicio_hash is not None and fin_hash is not None:
        start_bumper_path: str = os.path.join(
            settings.BUMPER_DETECTION_DIR,
            f"{formatted_channel}-{settings.START_EVENT_NAME}-{formatted_date}.jpg",
        )
        
        save_bumper(start_bumper_path, inicio_image)

        end_bumper_path: str = os.path.join(
            settings.BUMPER_DETECTION_DIR,
            f"{formatted_channel}-{settings.END_EVENT_NAME}-{formatted_date}.jpg",
        )

        save_bumper(end_bumper_path, fin_image)
    return "SUCCESS"


def save_bumper(path: str, bumper: Any) -> None:
    cv2.imwrite(path, bumper)
