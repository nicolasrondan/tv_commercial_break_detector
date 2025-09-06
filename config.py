import logging
import os

import easyocr
from spellchecker import SpellChecker


def to_boolean(value: str) -> bool:
    TRUE_STRINGS = [True, "true", "yes", "y", "enable", "enabled", "1"]
    FALSE_STRINGS = [False, "false", "no", "n", "disable", "disabled", "0"]
    if value.lower() in TRUE_STRINGS:
        return True
    if value.lower() in FALSE_STRINGS:
        return False
    raise ValueError(f"Unknown boolean value '{value}'")


class Settings:
    # DETECTION SETTINGS
    OCR_WORD_LIMIT = os.getenv("OCR_WORD_LIMIT") or 20
    MAX_CORRUPT_FRAMES = os.getenv("MAX_CORRUPT_FRAMES") or 1200
    DHASH_FREQUENCY = (
        os.getenv("DHASH_FREQUENCY") or 8
    )  # one in every x frames is processed
    DHASH_THRESHOLD = os.getenv("DHASH_THRESHOLD") or 8
    BOARD_TIME_SEPARATION = os.getenv("BOARD_TIME_SEPARATION") or 2  # time in seconds
    DETECTION_TIMEOUT = os.getenv("DETECTION_TIMEOUT") or 3600  # seconds
    VIDEO_END_PADDING_FRAMES = os.getenv("VIDEO_END_PADDING_FRAMES") or 15
    # WORDS
    START_WORDS = {
        "inicio",
        "inicia",
        "comienza",
        "empieza",
        "arranca",
        "comenzo",
        "empezo",
        "arranco",
        "comenzó",
        "empezó",
        "arrancó",
    }

    END_WORDS = {
        "fin",
        "finaliza",
        "termina",
        "acaba",
        "concluye",
        "concluyo",
        "termino",
        "finalizo",
        "terminó",
        "finalizó",
    }

    PUBLICITARIO_WORDS = {"publicitario"}

    # DB

    START_EVENT_NAME = os.getenv("START_EVENT_NAME") or "start"
    END_EVENT_NAME = os.getenv("END_EVENT_NAME") or "end"

    # KEYS

    BUMPER_DETECTION_DIR = (
        os.getenv("BUMPER_DETECTION_DIR") or "./bumpers/"
    )
    TV_SCHEDULES_SBD = os.getenv("TV_SCHEDULES_SBD") or [6, 23]
    BUMPER_TIME_WINDOW = os.getenv("BUMPER_TIME_WINDOW") or [1.3, 5]
    
    OCR_LANGUAGES = ["es"]
    SPELLCHECKER_LANGUAGE = "es"
    SPELLCHECKER_REMOVE_WORDS = ["jqué", "e", "d"]

settings = Settings()

spellcheck = SpellChecker(language=settings.SPELLCHECKER_LANGUAGE)
spellcheck.word_frequency.remove_words(settings.SPELLCHECKER_REMOVE_WORDS)

# Cargo el idioma para usar OCR
reader = easyocr.Reader(settings.OCR_LANGUAGES)
logger = logging.getLogger(__name__)
