import time
import logging
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import Message
from config import COOLDOWN_SECONDS

# ========================
# Rate Limit (Cooldown 2 menit per user)
# ========================

class RateLimitMiddleware(BaseMiddleware):
    """Membatasi user mengirim menfess dengan jeda 2 menit."""

    def __init__(self):
        self._last_sent: Dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ) -> Any:
        if not isinstance(event, Message):
            return await handler(event, data)

        # Cooldown dimatikan
        if COOLDOWN_SECONDS <= 0:
            return await handler(event, data)

        user_id = event.from_user.id if event.from_user else None
        if user_id is None:
            return await handler(event, data)

        # Skip rate limit untuk command (hanya berlaku untuk menfess)
        if event.text and event.text.startswith('/'):
            return await handler(event, data)

        now = time.time()
        last = self._last_sent.get(user_id, 0)
        diff = now - last

        if diff < COOLDOWN_SECONDS:
            remaining = int(COOLDOWN_SECONDS - diff)
            mins = remaining // 60
            secs = remaining % 60
            time_str = f"{mins} menit {secs} detik" if mins > 0 else f"{secs} detik"
            await event.reply(
                f"⏳ Sabar ya kak, tunggu {time_str} lagi sebelum kirim menfess berikutnya~"
            )
            return  # Stop, jangan lanjutkan ke handler

        self._last_sent[user_id] = now
        return await handler(event, data)


# ========================
# Admin Command Logger
# ========================

class AdminLoggingMiddleware(BaseMiddleware):
    """Log semua command admin."""

    def __init__(self, admin_ids: set):
        self._admin_ids = admin_ids

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ) -> Any:
        if (
            isinstance(event, Message)
            and event.from_user
            and event.from_user.id in self._admin_ids
            and event.text
            and event.text.startswith('/')
        ):
            logging.info(f"[ADMIN CMD] {event.from_user.id} -> {event.text}")

        return await handler(event, data)
