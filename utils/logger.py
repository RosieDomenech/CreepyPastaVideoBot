"""utils/logger.py — Simple console logger with emoji levels."""

from datetime import datetime


def log(message: str, level: str = "info"):
    timestamp = datetime.now().strftime("%H:%M:%S")
    icons = {"info": "ℹ️ ", "warn": "⚠️ ", "error": "❌"}
    icon = icons.get(level, "ℹ️ ")
    print(f"[{timestamp}] {icon} {message}")
