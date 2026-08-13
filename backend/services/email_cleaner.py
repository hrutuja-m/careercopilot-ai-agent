"""Email body decoding and cleanup helpers for the career email pipeline.

The implementation lives in gmail_handshake_scraper because Gmail is the
only connected provider today. These exports make the pipeline boundary
explicit for callers and documentation.
"""

from services.gmail_handshake_scraper import (
    clean_html,
    decode_base64url,
    extract_message_body,
    get_header,
)

__all__ = [
    "clean_html",
    "decode_base64url",
    "extract_message_body",
    "get_header",
]
