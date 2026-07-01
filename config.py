import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL: str | None = os.getenv("OPENAI_BASE_URL", None)
DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///psy.db")
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
BOT_PROXY: str | None = os.getenv("BOT_PROXY", None)
