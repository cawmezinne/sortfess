from aiogram import Bot
from aiogram.types import ChatMember
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
from config import REQUIRED_CHANNELS
import logging

# Status global untuk membuka/menutup fitur menfess
_POST_STATUS = {"is_open": True}

def set_post_status(status: bool) -> None:
    """
    Atur status buka/tutup base.
    Args:
        status (bool): True untuk buka, False untuk tutup.
    """
    _POST_STATUS["is_open"] = status
    logging.info(f"[Post Status] Diubah menjadi {'Buka' if status else 'Tutup'}")

def get_post_status() -> bool:
    """
    Ambil status saat ini dari base.
    Returns:
        bool: True jika base dibuka, False jika ditutup.
    """
    return _POST_STATUS["is_open"]

async def check_subscription(user_id: int, bot: Bot) -> bool:
    """
    Periksa apakah user sudah bergabung ke semua channel wajib.

    Args:
        user_id (int): ID Telegram user
        bot (Bot): Instance bot

    Returns:
        bool: True jika user tergabung di semua channel, False jika belum atau terjadi error.
    """
    for channel_id in REQUIRED_CHANNELS:
        try:
            member: ChatMember = await bot.get_chat_member(chat_id=channel_id, user_id=user_id)
            if member.status not in {"member", "administrator", "creator"}:
                logging.warning(f"[Subscription] User {user_id} belum join channel {channel_id}")
                return False
        except (TelegramForbiddenError, TelegramBadRequest) as e:
            logging.error(f"[Subscription] Gagal cek channel {channel_id} untuk user {user_id}: {e}")
            return False
        except Exception as e:
            logging.exception(f"[Subscription] Error tidak diketahui saat cek user {user_id} di {channel_id}: {e}")
            return False
    return True
