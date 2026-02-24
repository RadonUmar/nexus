from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv


# Load environment variables early
load_dotenv()


REPO_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    hyperspell_api_key: str
    hyperspell_enabled: bool

    railway_email_api: str
    railway_email_inbox_api: str

    base_dir: Path
    data_dir: Path
    desktop_dir: Path
    static_dir: Path
    templates_dir: Path
    processed_emails_file: Path



def _require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"{name} not found in .env file. Please create a .env file with your {name}.")
    return value


def load_settings() -> Settings:
    openai_api_key = _require_env("OPENAI_API_KEY")
    hyperspell_api_key = os.getenv("HYPERSPELL_API_KEY", "").strip()

    base_dir = REPO_ROOT
    data_dir = base_dir / "data"
    desktop_dir = data_dir / "Desktop"
    static_dir = base_dir / "static"
    templates_dir = base_dir / "templates"

    data_dir.mkdir(exist_ok=True)
    desktop_dir.mkdir(exist_ok=True)
    static_dir.mkdir(exist_ok=True)
    templates_dir.mkdir(exist_ok=True)

    return Settings(
        openai_api_key=openai_api_key,
        hyperspell_api_key=hyperspell_api_key,
        hyperspell_enabled=bool(hyperspell_api_key),
        railway_email_api=os.getenv(
            "RAILWAY_EMAIL_API",
            "https://web-production-02ec.up.railway.app/compose-send",
        ),
        railway_email_inbox_api=os.getenv(
            "RAILWAY_EMAIL_INBOX_API",
            "https://web-production-02ec.up.railway.app/emails",
        ),
        base_dir=base_dir,
        data_dir=data_dir,
        desktop_dir=desktop_dir,
        static_dir=static_dir,
        templates_dir=templates_dir,
        processed_emails_file=base_dir / "processed_email_ids.json",
    )


settings = load_settings()
