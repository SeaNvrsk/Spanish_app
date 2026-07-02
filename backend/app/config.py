import os
from datetime import date
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

# Absolute paths so the key is found no matter the working directory.
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ROOT_DIR = os.path.dirname(_BACKEND_DIR)
# Later files override earlier ones; the project-root .env takes precedence.
_ENV_FILES = (os.path.join(_BACKEND_DIR, ".env"), os.path.join(_ROOT_DIR, ".env"))


class Settings(BaseSettings):
    """Application configuration loaded from environment / .env file."""

    model_config = SettingsConfigDict(env_file=_ENV_FILES, env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Español para la Familia"
    # IMPORTANT: override in production via .env
    secret_key: str = "change-me-in-production-please-use-a-long-random-string"
    access_token_expire_minutes: int = 60 * 24 * 30  # 30 days
    algorithm: str = "HS256"

    database_url: str = "sqlite:///./espanol.db"

    # CORS: comma separated list of allowed origins. "*" allows all (dev only).
    cors_origins: str = "*"

    # --- AI / Text-to-Speech ---
    # OpenAI-compatible key for high quality Mexican Spanish audio. Optional:
    # if empty, the frontend falls back to the browser's built-in es-MX voice.
    openai_api_key: str = ""
    openai_tts_model: str = "gpt-4o-mini-tts"
    # "coral" and "sage" are warm, natural voices that handle Spanish well.
    openai_tts_voice: str = "coral"
    openai_base_url: str = "https://api.openai.com/v1"
    openai_chat_model: str = "gpt-4o-mini"
    openai_image_model: str = "gpt-image-1"
    openai_image_quality: str = "medium"
    openai_image_size: str = "1024x1024"  # API minimum; downscaled after download
    openai_image_save_px: int = 512  # flashcards on phone (~max 144px CSS)
    openai_image_save_format: str = "webp"  # webp | png
    # Comma-separated admin emails (excluded from family rankings; can view all stats).
    admin_emails: str = "an.mexico@icloud.com"

    # Family program calendar: day 1 unlocks on this date; one new lesson slot per day.
    program_start_date: date = date(2026, 7, 1)


@lru_cache
def get_settings() -> Settings:
    return Settings()
