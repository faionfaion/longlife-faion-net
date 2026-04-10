"""Telegram Bot API helpers."""

from __future__ import annotations

import logging

import requests

logger = logging.getLogger(__name__)


def send_text(
    chat_id: str,
    caption: str,
    preview_url: str | None = None,
    silent: bool = False,
    button_url: str | None = None,
    button_text: str = "Читати повністю \u2192",
    bot_token: str = "",
) -> int | None:
    """Send a text message with optional OG link preview."""
    api = f"https://api.telegram.org/bot{bot_token}"

    # Prepend invisible link for OG preview (use NBSP, not ZWS)
    text = caption
    if preview_url:
        text = f'<a href="{preview_url}">\u00a0</a>{caption}'

    link_opts: dict = {
        "prefer_large_media": True,
        "show_above_text": True,
    }
    if preview_url:
        link_opts["url"] = preview_url

    payload = {
        "chat_id": int(chat_id),
        "text": text,
        "parse_mode": "HTML",
        "link_preview_options": link_opts,
    }

    if silent:
        payload["disable_notification"] = True

    if button_url:
        payload["reply_markup"] = {
            "inline_keyboard": [[{"text": button_text, "url": button_url}]]
        }

    try:
        resp = requests.post(f"{api}/sendMessage", json=payload, timeout=30)
        r = resp.json()
        if r.get("ok"):
            return r["result"]["message_id"]
        logger.error("TG send error: %s", r.get("description"))
    except Exception:
        logger.error("TG send failed", exc_info=True)

    return None


def send_photo(
    chat_id: str,
    image_path: str,
    caption: str,
    bot_token: str = "",
    silent: bool = False,
) -> int | None:
    """Send a photo with caption."""
    api = f"https://api.telegram.org/bot{bot_token}"

    try:
        data = {"chat_id": chat_id, "caption": caption, "parse_mode": "HTML"}
        if silent:
            data["disable_notification"] = "true"
        with open(image_path, "rb") as f:
            resp = requests.post(
                f"{api}/sendPhoto",
                data=data,
                files={"photo": f},
                timeout=30,
            )
        r = resp.json()
        if r.get("ok"):
            return r["result"]["message_id"]
        logger.error("TG photo error: %s", r.get("description"))
    except Exception:
        logger.error("TG photo send failed", exc_info=True)

    return None


def add_reaction(
    chat_id: str,
    msg_id: int,
    emoji: str,
    bot_token: str = "",
) -> None:
    """Add a reaction emoji to a message."""
    api = f"https://api.telegram.org/bot{bot_token}"

    try:
        requests.post(
            f"{api}/setMessageReaction",
            json={
                "chat_id": int(chat_id),
                "message_id": msg_id,
                "reaction": [{"type": "emoji", "emoji": emoji}],
            },
            timeout=10,
        )
    except Exception:
        logger.warning("Failed to add reaction", exc_info=True)
