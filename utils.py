import logging
from typing import Optional
from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
from config import REQUIRED_CHANNELS


# ========================
# STATUS BASE (OPEN / CLOSE)
# ========================

_POST_STATUS = {"is_open": True}


def set_post_status(status: bool) -> None:
    """
    Mengubah status base (buka / tutup menfess)
    """
    _POST_STATUS["is_open"] = status

    if status:
        logging.info("[Post Status] Base dibuka")
    else:
        logging.info("[Post Status] Base ditutup")


def get_post_status() -> bool:
    """
    Mengambil status base saat ini
    """
    return _POST_STATUS["is_open"]


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
