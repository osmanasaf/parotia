import logging
from typing import Optional

try:
    from langdetect import detect
except Exception:  # pragma: no cover
    detect = None  # type: ignore

try:
    from deep_translator import GoogleTranslator
except Exception:  # pragma: no cover
    GoogleTranslator = None  # type: ignore


logger = logging.getLogger(__name__)


class LanguageService:
    """Basit dil tespiti ve İngilizce çeviri servisi.

    - SRP: Sadece dil tespiti ve çeviri işinden sorumlu.
    - Dış bağımlılıklar yoksa graceful fallback uygular.
    """

    def detect_language(self, text: str) -> str:
        if not text or not text.strip():
            return "en"
        if detect is None:
            logger.warning("langdetect unavailable, defaulting language to 'en'")
            return "en"
        try:
            code = detect(text)
            return code or "en"
        except Exception:
            return "en"

    def translate_to_english(self, text: str, source_lang: Optional[str] = None) -> str:
        if not text or not text.strip():
            return ""
        # Eğer zaten İngilizce ise çeviri gereksiz
        if (source_lang or "en").startswith("en"):
            return text
        if GoogleTranslator is None:
            logger.warning("GoogleTranslator unavailable, skipping translation")
            return text
        try:
            translator = GoogleTranslator(source=source_lang or "auto", target="en")
            return translator.translate(text) or text
        except Exception:
            return text


