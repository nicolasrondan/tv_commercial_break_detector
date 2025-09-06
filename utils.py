import os
from ast import List
from datetime import datetime, timedelta
from typing import List as TypingList, Tuple, Optional

import cv2
import imagehash
from PIL import Image

from config import settings, spellcheck


def datetime_to_string(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def string_to_datetime(timestamp_str: str) -> datetime:
    return datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")


def get_end_timestamp(start_time_str: str, duration: int) -> str:
    dt = string_to_datetime(start_time_str)
    return datetime_to_string(dt + timedelta(seconds=duration - 1))


def get_ad_borders(ad_start_timestamp: str, ad_end_timestamp: str, start_date: str) -> Tuple[float, float]:
    ad_start_dt = string_to_datetime(ad_start_timestamp)
    ad_end_dt = string_to_datetime(ad_end_timestamp)
    video_start_dt = string_to_datetime(start_date)

    time_difference_inicio_to_start = (ad_start_dt - video_start_dt).total_seconds() * 1000
    time_difference_fin_to_start = (ad_end_dt - video_start_dt).total_seconds() * 1000

    return time_difference_inicio_to_start, time_difference_fin_to_start


def get_timestamp(milis: int, start_date: str) -> datetime:
    return timedelta(milliseconds=milis) + string_to_datetime(start_date)


def count_words_in_ocr(ocr: TypingList[str]) -> int:
    counter = 0
    for line in ocr:
        counter += len(line.split())
    return counter


def add_seconds_to_datetime(seconds: int, date_time: datetime) -> str:
    seconds_delta = timedelta(seconds=seconds)
    return datetime_to_string(date_time + seconds_delta)


def get_frame_dhash(frame) -> imagehash.ImageHash:
    img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    return imagehash.dhash(Image.fromarray(img))


def get_bumpers_dhashes(channel: str, folder: str = settings.BUMPER_DETECTION_DIR) -> TypingList[imagehash.ImageHash]:
    formatted_channel_name: str = format_channel_name(channel)
    dhashes: TypingList[imagehash.ImageHash] = []
    for file in os.listdir(folder):
        if file.startswith(formatted_channel_name):
            if file.endswith(".png") or file.endswith(".jpg"):
                bumper_image = cv2.imread(os.path.join(folder, file))
                bumper_dhash = get_frame_dhash(bumper_image)
                dhashes.append(bumper_dhash)
    return dhashes


classification_words: TypingList[set] = [
    settings.START_WORDS,
    settings.END_WORDS,
    settings.PUBLICITARIO_WORDS,
]

OCR_WORD_LIMIT: int = int(settings.OCR_WORD_LIMIT)


def classify_board(ocr: TypingList[str]) -> Optional[str]:
    to_return = [False, False, False, False, False, False, False]
    if count_words_in_ocr(ocr) <= OCR_WORD_LIMIT:
        for line in ocr:
            for word in line.split():
                candidates = spellcheck.candidates(word.lower())
                if candidates is not None:
                    flag_vec = [not candidates.isdisjoint(words) for words in classification_words]
                    to_return = [to_return[i] or flag for i, flag in enumerate(flag_vec)]
    if to_return == [False, True, True]:
        return settings.END_EVENT_NAME
    if to_return == [True, False, True]:
        return settings.START_EVENT_NAME
    return None

def format_channel_name(channel_name: str) -> str:
    formatted_channel: str = channel_name.strip().lower()
    formatted_channel_no_spaces: str = formatted_channel.replace(" ", "_")
    return formatted_channel_no_spaces