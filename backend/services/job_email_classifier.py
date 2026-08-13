"""Message classification for career-related Gmail messages."""

from services.gmail_handshake_scraper import (
    infer_message_type,
    is_trackable_message_type,
)

__all__ = [
    "infer_message_type",
    "is_trackable_message_type",
]
