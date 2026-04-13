import logging
from typing import Optional
from datetime import datetime
from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
from config import REQUIRED_CHANNELS


# ========================
# STATUS BASE (OPEN / CLOSE)
# ========================

_POST_STATUS = {
    "is_open": True,
    "reason": None,       # alasan tutup (e.g. "paid promote")
    "reopen_at": None,    # waktu buka otomatis (datetime)
}


def set_post_status(
    status: bool,
    reason: Optional[str] = None,
    reopen_at: Optional[datetime] = None,
) -> None:
    """
    Mengubah status base (buka / tutup menfess).
    Bisa menyimpan alasan tutup dan jadwal buka otomatis.
    """
    _POST_STATUS["is_open"] = status
    _POST_STATUS["reason"] = reason if not status else None
    _POST_STATUS["reopen_at"] = reopen_at if not status else None

    if status:
        logging.info("[Post Status] Base dibuka")
    else:
        r = f" | Alasan: {reason}" if reason else ""
        logging.info(f"[Post Status] Base ditutup{r}")


def get_post_status() -> bool:
    """
    Mengambil status base saat ini.
    """
    return _POST_STATUS["is_open"]


def get_close_reason() -> Optional[str]:
    """
    Mengambil alasan base ditutup (None jika tidak ada / sedang buka).
    """
    return _POST_STATUS.get("reason")


def get_reopen_time() -> Optional[datetime]:
    """
    Mengambil waktu jadwal buka otomatis (None jika tidak ada).
    """
    return _POST_STATUS.get("reopen_at")


# ========================
# CHECK SUBSCRIPTION
# ========================

async def check_subscription(user_id: int, bot: Bot) -> bool:
    """
    Mengecek apakah user sudah join semua channel yang diwajibkan.

    Args:
        user_id (int): ID user Telegram
        bot (Bot): instance bot

    Returns:
        bool: True jika user join semua channel
    """

    for channel in REQUIRED_CHANNELS:
        try:
            member = await bot.get_chat_member(
                chat_id=channel,
                user_id=user_id
            )

            status = member.status

            # Debug log
            logging.info(
                f"[Subscription Check] User {user_id} di {channel} -> {status}"
            )

            if status not in (
                ChatMemberStatus.MEMBER,
                ChatMemberStatus.ADMINISTRATOR,
                ChatMemberStatus.CREATOR,
            ):
                logging.warning(
                    f"[Subscription] User {user_id} belum join {channel}"
                )
                return False

        except TelegramForbiddenError:
            logging.error(
                f"[Subscription] Bot tidak punya akses ke channel {channel}"
            )
            return False

        except TelegramBadRequest as e:
            logging.error(
                f"[Subscription] Channel salah atau tidak ditemukan: {channel} | {e}"
            )
            return False

        except Exception as e:
            logging.exception(
                f"[Subscription] Error saat cek user {user_id} di {channel}: {e}"
            )
            return False

    return True


# ========================
# LINK POSTINGAN CHANNEL
# ========================

async def build_channel_post_link(bot: Bot, chat_id: int, message_id: int) -> Optional[str]:
    """
    Bangun link menuju postingan yang dikirim ke channel.

    - Channel public: https://t.me/<username>/<message_id>
    - Channel private: https://t.me/c/<internal_id>/<message_id>
      (internal_id = abs(chat_id) - 1000000000000)
    """
    try:
        chat = await bot.get_chat(chat_id)
        username = getattr(chat, "username", None)
        if username:
            return f"https://t.me/{username}/{message_id}"
    except Exception as e:
        logging.warning(f"[Post Link] Gagal ambil username chat {chat_id}: {e}")

    try:
        # Telegram private channel link format
        abs_id = abs(int(chat_id))
        if abs_id >= 1000000000000:
            internal_id = abs_id - 1000000000000
            return f"https://t.me/c/{internal_id}/{message_id}"
    except Exception as e:
        logging.warning(f"[Post Link] Gagal build private link untuk {chat_id}: {e}")

    return None
