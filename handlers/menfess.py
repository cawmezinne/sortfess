import asyncio
import html
import logging
from aiogram import Router, types, F, Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from filters import contains_bad_word
from config import VALID_HASHTAGS, CHANNEL_ID, AUTO_DELETE_HOURS
from utils import check_subscription, get_post_status
from handlers.start import sub_keyboard
from db import (
    add_user,
    is_banned,
    count_hashtags,
    log_post,
    add_pending_menfess
)

router = Router()

# Cache sementara untuk konfirmasi (user_id -> data menfess)
_pending_confirm = {}

# ========================
# VALIDASI HELPERS
# ========================

async def _validate_user(message: types.Message, bot: Bot) -> bool:
    """Validasi umum: banned, base tutup, subscription."""
    user_id = message.from_user.id
    add_user(user_id, message.from_user.username or "")

    if is_banned(user_id):
        await message.reply("Maaf kamu telah diblokir dari mengirim menfess.")
        return False

    if not get_post_status():
        await message.reply("♬ ˖ ࣪  Base lagi rehat beb. Nanti balik lagi ya~")
        return False

    if not await check_subscription(user_id, bot):
        await message.reply(
            "Eits, belum join base nih!\nYuk follow dulu channel kita biar bisa kirim menfess 🤍",
            reply_markup=sub_keyboard()
        )
        return False

    return True


def _validate_text(text: str) -> str | None:
    """Validasi teks/caption. Return error message atau None jika valid."""
    if len(text) < 10:
        return "Pesanmu terlalu pendek kak, coba tambahkan lebih banyak ya~"

    if contains_bad_word(text):
        return "Ups, no toxic zone ya ma bro. Jaga omongan dong~"

    text_lower = text.lower()
    if not any(tag in text_lower for tag in VALID_HASHTAGS):
        return "Tambahin hashtag dulu dong \nContoh: #sorta pengen martabak"

    wrong_tags = [w for w in text_lower.split() if w.startswith('#') and w not in VALID_HASHTAGS]
    if wrong_tags:
        return "Kayaknya ada typo di hashtag kamu deh \nCek lagi yaa!"

    return None


def _confirmation_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Kirim", callback_data="confirm_send"),
            InlineKeyboardButton(text="❌ Batal", callback_data="confirm_cancel")
        ]
    ])


async def _schedule_auto_delete(bot: Bot, chat_id: int, message_id: int):
    """Auto-delete pesan di channel setelah X jam."""
    if AUTO_DELETE_HOURS <= 0:
        return
    await asyncio.sleep(AUTO_DELETE_HOURS * 3600)
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception as e:
        logging.warning(f"[Auto-Delete] Gagal hapus pesan {message_id}: {e}")


def _is_tellem(text: str) -> bool:
    return '#tellem' in text.lower()


# ========================
# TEXT MENFESS
# ========================

@router.message(F.text & ~F.text.startswith("/"))
async def handle_text_menfess(message: types.Message, bot: Bot):
    if not await _validate_user(message, bot):
        return

    text = message.text.strip()
    error = _validate_text(text)
    if error:
        return await message.reply(error)

    user_id = message.from_user.id

    # Simpan ke pending confirm
    _pending_confirm[user_id] = {
        "type": "text",
        "text": text,
        "username": message.from_user.username or "",
        "full_name": message.from_user.full_name,
    }

    preview = html.escape(text[:200]) + ("..." if len(text) > 200 else "")
    await message.reply(
        f"📝 <b>Preview Menfess:</b>\n\n{preview}\n\n"
        "Yakin mau kirim ke base?",
        reply_markup=_confirmation_keyboard(),
        parse_mode="HTML"
    )


# ========================
# PHOTO MENFESS
# ========================

@router.message(F.photo)
async def handle_photo_menfess(message: types.Message, bot: Bot):
    if not await _validate_user(message, bot):
        return

    caption = message.caption or ""
    error = _validate_text(caption)
    if error:
        return await message.reply(error)

    user_id = message.from_user.id
    _pending_confirm[user_id] = {
        "type": "photo",
        "text": caption,
        "file_id": message.photo[-1].file_id,
        "username": message.from_user.username or "",
        "full_name": message.from_user.full_name,
    }

    await message.reply(
        "📷 Foto siap dikirim ke base.\nYakin mau kirim?",
        reply_markup=_confirmation_keyboard()
    )


# ========================
# DOCUMENT MENFESS
# ========================

@router.message(F.document)
async def handle_document_menfess(message: types.Message, bot: Bot):
    if not await _validate_user(message, bot):
        return

    caption = message.caption or ""
    error = _validate_text(caption)
    if error:
        return await message.reply(error)

    user_id = message.from_user.id
    _pending_confirm[user_id] = {
        "type": "document",
        "text": caption,
        "file_id": message.document.file_id,
        "username": message.from_user.username or "",
        "full_name": message.from_user.full_name,
    }

    await message.reply(
        "📄 Dokumen siap dikirim ke base.\nYakin mau kirim?",
        reply_markup=_confirmation_keyboard()
    )


# ========================
# VOICE MENFESS
# ========================

@router.message(F.voice)
async def handle_voice_menfess(message: types.Message, bot: Bot):
    if not await _validate_user(message, bot):
        return

    caption = message.caption or ""
    # Voice note boleh tanpa caption, tapi kalau ada caption harus valid
    if caption:
        error = _validate_text(caption)
        if error:
            return await message.reply(error)

    user_id = message.from_user.id
    _pending_confirm[user_id] = {
        "type": "voice",
        "text": caption,
        "file_id": message.voice.file_id,
        "username": message.from_user.username or "",
        "full_name": message.from_user.full_name,
    }

    await message.reply(
        "🎤 Voice note siap dikirim ke base.\nYakin mau kirim?",
        reply_markup=_confirmation_keyboard()
    )


# ========================
# VIDEO MENFESS (NEW)
# ========================

@router.message(F.video)
async def handle_video_menfess(message: types.Message, bot: Bot):
    if not await _validate_user(message, bot):
        return

    caption = message.caption or ""
    error = _validate_text(caption)
    if error:
        return await message.reply(error)

    user_id = message.from_user.id
    _pending_confirm[user_id] = {
        "type": "video",
        "text": caption,
        "file_id": message.video.file_id,
        "username": message.from_user.username or "",
        "full_name": message.from_user.full_name,
    }

    await message.reply(
        "🎬 Video siap dikirim ke base.\nYakin mau kirim?",
        reply_markup=_confirmation_keyboard()
    )


# ========================
# VIDEO NOTE MENFESS (NEW)
# ========================

@router.message(F.video_note)
async def handle_video_note_menfess(message: types.Message, bot: Bot):
    if not await _validate_user(message, bot):
        return

    user_id = message.from_user.id
    _pending_confirm[user_id] = {
        "type": "video_note",
        "text": "",
        "file_id": message.video_note.file_id,
        "username": message.from_user.username or "",
        "full_name": message.from_user.full_name,
    }

    await message.reply(
        "🔵 Video note siap dikirim ke base.\nYakin mau kirim?",
        reply_markup=_confirmation_keyboard()
    )


# ========================
# STICKER MENFESS
# ========================

@router.message(F.sticker)
async def handle_sticker_menfess(message: types.Message, bot: Bot):
    if not await _validate_user(message, bot):
        return

    user_id = message.from_user.id
    _pending_confirm[user_id] = {
        "type": "sticker",
        "text": "[STIKER]",
        "file_id": message.sticker.file_id,
        "username": message.from_user.username or "",
        "full_name": message.from_user.full_name,
    }

    await message.reply(
        "🧩 Stiker siap dikirim ke base.\nYakin mau kirim?",
        reply_markup=_confirmation_keyboard()
    )


# ========================
# CONFIRMATION CALLBACK
# ========================

@router.callback_query(F.data == "confirm_send")
async def confirm_send(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    data = _pending_confirm.pop(user_id, None)

    await callback.answer()

    if not data:
        return await callback.message.edit_text("⏳ Menfess ini sudah kadaluarsa. Silakan kirim ulang.")

    try:
        await callback.message.delete()
    except Exception:
        pass

    text = data["text"]
    content_type = data["type"]

    # === APPROVAL MODE untuk #tellem ===
    if _is_tellem(text):
        menfess_id = add_pending_menfess(
            user_id=user_id,
            content_type=content_type,
            text=text,
            file_id=data.get("file_id")
        )
        await bot.send_message(
            user_id,
            f"⏳ Menfess #tellem kamu (#{menfess_id}) sedang menunggu persetujuan admin.\n"
            "Kamu akan diberi notifikasi saat di-approve/reject."
        )
        return

    # === KIRIM LANGSUNG ===
    count_hashtags(text)
    log_post(user_id, text)

    # Build forward text untuk #gonna
    if '#gonna' in text.lower():
        username = data.get("username", "")
        full_name = data.get("full_name", "")
        mention = f"@{username}" if username else "(tidak ada username)"
        forward_text = (
            f"{text}\n\n"
            f"👤 Nama  : {full_name}\n"
            f"🆔 ID    : <code>{user_id}</code>\n"
            f"🔗 User : {mention}"
        )
    else:
        forward_text = text

    sent = None
    try:
        if content_type == "text":
            sent = await bot.send_message(chat_id=CHANNEL_ID, text=forward_text, parse_mode="HTML")
        elif content_type == "photo":
            sent = await bot.send_photo(chat_id=CHANNEL_ID, photo=data["file_id"], caption=forward_text, parse_mode="HTML")
        elif content_type == "document":
            sent = await bot.send_document(chat_id=CHANNEL_ID, document=data["file_id"], caption=forward_text, parse_mode="HTML")
        elif content_type == "voice":
            sent = await bot.send_voice(chat_id=CHANNEL_ID, voice=data["file_id"], caption=forward_text or None, parse_mode="HTML")
        elif content_type == "video":
            sent = await bot.send_video(chat_id=CHANNEL_ID, video=data["file_id"], caption=forward_text, parse_mode="HTML")
        elif content_type == "video_note":
            sent = await bot.send_video_note(chat_id=CHANNEL_ID, video_note=data["file_id"])
        elif content_type == "sticker":
            sent = await bot.send_sticker(chat_id=CHANNEL_ID, sticker=data["file_id"])
    except Exception as e:
        logging.error(f"[Menfess] Gagal kirim ke channel: {e}")
        await bot.send_message(user_id, "❌ Gagal mengirim menfess. Coba lagi nanti ya~")
        return

    await bot.send_message(user_id, "Done kak! Fess kamu udah terbang ke base ✈️")

    # Schedule auto-delete
    if sent and AUTO_DELETE_HOURS > 0:
        asyncio.create_task(_schedule_auto_delete(bot, CHANNEL_ID, sent.message_id))


@router.callback_query(F.data == "confirm_cancel")
async def confirm_cancel(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    _pending_confirm.pop(user_id, None)

    await callback.answer("❌ Dibatalkan")

    try:
        await callback.message.edit_text("❌ Menfess dibatalkan. Kamu bisa kirim ulang kapan saja~")
    except Exception:
        pass