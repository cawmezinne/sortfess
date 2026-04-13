import asyncio
import html
import logging

from aiogram import Router, types, F, Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from filters import contains_bad_word
from config import VALID_HASHTAGS, CHANNEL_ID, AUTO_DELETE_HOURS
from utils import check_subscription, get_post_status, get_close_reason, build_channel_post_link
from handlers.start import sub_keyboard

from db import (
    add_user,
    is_banned,
    count_hashtags,
    log_post,
    add_pending_menfess,
    upsert_user_last_post
)

router = Router()

_pending_confirm = {}


# ========================
# VALIDASI USER
# ========================

async def validate_user(message: types.Message, bot: Bot) -> bool:
    user_id = message.from_user.id
    add_user(user_id, message.from_user.username or "")

    if is_banned(user_id):
        await message.reply("❌ Kamu telah diblokir dari base ini.")
        return False

    if not get_post_status():
        reason = get_close_reason()
        text = "🔒 Base sedang rehat."
        if reason:
            text += f"\n📝 Keterangan: <i>{html.escape(reason)}</i>"
        text += "\n\nCoba lagi nanti ya."
        await message.reply(text, parse_mode="HTML")
        return False

    if not await check_subscription(user_id, bot):
        await message.reply(
            "⚠️ Kamu harus join semua channel dulu sebelum kirim menfess.",
            reply_markup=sub_keyboard()
        )
        return False

    return True


# ========================
# VALIDASI TEKS
# ========================

def validate_text(text: str, allow_empty: bool = False):
    if allow_empty and not text:
        return None

    if len(text) < 10:
        return "⚠️ Pesan terlalu pendek."

    if contains_bad_word(text):
        return "⚠️ Pesan mengandung kata terlarang."

    text_lower = text.lower()

    if not any(tag in text_lower for tag in VALID_HASHTAGS):
        return "⚠️ Tambahkan hashtag yang valid."

    wrong_tags = [
        word for word in text_lower.split()
        if word.startswith("#") and word not in VALID_HASHTAGS
    ]

    if wrong_tags:
        return "⚠️ Hashtag tidak dikenali."

    return None


# ========================
# KEYBOARD KONFIRMASI
# ========================

def confirm_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Kirim",
                    callback_data="confirm_send"
                ),
                InlineKeyboardButton(
                    text="❌ Batal",
                    callback_data="confirm_cancel"
                )
            ]
        ]
    )

def post_link_keyboard(url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔗 Lihat Postingan", url=url)]
        ]
    )


# ========================
# AUTO DELETE
# ========================

async def auto_delete(bot: Bot, chat_id: int, message_id: int):
    if AUTO_DELETE_HOURS <= 0:
        return

    await asyncio.sleep(AUTO_DELETE_HOURS * 3600)

    try:
        await bot.delete_message(chat_id, message_id)
    except Exception as e:
        logging.warning(f"[AutoDelete] Gagal hapus pesan: {e}")


# ========================
# TEXT MENFESS
# ========================

@router.message(F.text & ~F.text.startswith("/"))
async def handle_text(message: types.Message, bot: Bot):

    if not await validate_user(message, bot):
        return

    text = message.text.strip()

    error = validate_text(text)
    if error:
        return await message.reply(error)

    user_id = message.from_user.id

    _pending_confirm[user_id] = {
        "type": "text",
        "text": text,
        "username": message.from_user.username or "",
        "full_name": message.from_user.full_name
    }

    preview = html.escape(text[:200])

    await message.reply(
        f"📝 <b>Preview:</b>\n\n{preview}\n\nKirim menfess?",
        reply_markup=confirm_keyboard(),
        parse_mode="HTML"
    )


# ========================
# PHOTO MENFESS
# ========================

@router.message(F.photo)
async def handle_photo(message: types.Message, bot: Bot):

    if not await validate_user(message, bot):
        return

    caption = message.caption or ""

    error = validate_text(caption)
    if error:
        return await message.reply(error)

    user_id = message.from_user.id

    _pending_confirm[user_id] = {
        "type": "photo",
        "text": caption,
        "file_id": message.photo[-1].file_id,
        "username": message.from_user.username or "",
        "full_name": message.from_user.full_name
    }

    await message.reply(
        "📷 Foto siap dikirim. Kirim sekarang?",
        reply_markup=confirm_keyboard()
    )


# ========================
# DOCUMENT MENFESS
# ========================

@router.message(F.document)
async def handle_document(message: types.Message, bot: Bot):

    if not await validate_user(message, bot):
        return

    caption = message.caption or ""

    error = validate_text(caption)
    if error:
        return await message.reply(error)

    user_id = message.from_user.id

    _pending_confirm[user_id] = {
        "type": "document",
        "text": caption,
        "file_id": message.document.file_id,
        "username": message.from_user.username or "",
        "full_name": message.from_user.full_name
    }

    await message.reply(
        "📄 Dokumen siap dikirim. Kirim sekarang?",
        reply_markup=confirm_keyboard()
    )


# ========================
# VIDEO MENFESS
# ========================

@router.message(F.video)
async def handle_video(message: types.Message, bot: Bot):

    if not await validate_user(message, bot):
        return

    caption = message.caption or ""

    error = validate_text(caption)
    if error:
        return await message.reply(error)

    user_id = message.from_user.id

    _pending_confirm[user_id] = {
        "type": "video",
        "text": caption,
        "file_id": message.video.file_id,
        "username": message.from_user.username or "",
        "full_name": message.from_user.full_name
    }

    await message.reply(
        "🎬 Video siap dikirim. Kirim sekarang?",
        reply_markup=confirm_keyboard()
    )


# ========================
# STICKER MENFESS
# ========================

@router.message(F.sticker)
async def handle_sticker(message: types.Message, bot: Bot):

    if not await validate_user(message, bot):
        return

    user_id = message.from_user.id

    _pending_confirm[user_id] = {
        "type": "sticker",
        "text": "",
        "file_id": message.sticker.file_id,
        "username": message.from_user.username or "",
        "full_name": message.from_user.full_name
    }

    await message.reply(
        "🎨 Stiker siap dikirim. Kirim sekarang?",
        reply_markup=confirm_keyboard()
    )


# ========================
# CONFIRM SEND
# ========================

@router.callback_query(F.data == "confirm_send")
async def confirm_send(callback: CallbackQuery, bot: Bot):

    user_id = callback.from_user.id
    data = _pending_confirm.pop(user_id, None)

    await callback.answer()

    if not data:
        return await callback.message.edit_text(
            "⚠️ Menfess sudah kadaluarsa."
        )

    try:
        await callback.message.delete()
    except Exception:
        pass

    text = data["text"]
    content_type = data["type"]

    # Stiker tidak butuh hashtag, skip log hashtag & post log teks jika kosong
    if content_type != "sticker":
        count_hashtags(text)
        log_post(user_id, text)
    else:
        log_post(user_id, "[sticker]")

    # Bangun teks yang dikirim ke channel
    text_lower = text.lower()
    if "#gonna" in text_lower:
        username = data.get("username") or ""
        full_name = data.get("full_name") or "(tanpa nama)"
        mention = f"@{username}" if username else "(tidak ada username)"
        forward_text = (
            f"{text}\n\n"
            f"👤 Nama  : {full_name}\n"
            f"🆔 ID    : <code>{user_id}</code>\n"
            f"🔗 User : {mention}"
        )
    else:
        forward_text = text

    # Jika #tellem → masuk pending approval
    if "#tellem" in text_lower and content_type != "sticker":
        file_id = data.get("file_id")
        pending_id = add_pending_menfess(user_id, content_type, text, file_id)
        await bot.send_message(
            user_id,
            f"⏳ Menfess <b>#tellem</b> kamu sudah masuk antrian review (ID: #{pending_id}).\n"
            "Admin akan segera mengecek. Terima kasih!",
            parse_mode="HTML"
        )
        return

    sent = None

    try:

        if content_type == "text":
            sent = await bot.send_message(
                CHANNEL_ID,
                forward_text,
                parse_mode="HTML"
            )

        elif content_type == "photo":
            sent = await bot.send_photo(
                CHANNEL_ID,
                data["file_id"],
                caption=forward_text,
                parse_mode="HTML"
            )

        elif content_type == "document":
            sent = await bot.send_document(
                CHANNEL_ID,
                data["file_id"],
                caption=forward_text,
                parse_mode="HTML"
            )

        elif content_type == "video":
            sent = await bot.send_video(
                CHANNEL_ID,
                data["file_id"],
                caption=forward_text,
                parse_mode="HTML"
            )

        elif content_type == "sticker":
            sent = await bot.send_sticker(
                CHANNEL_ID,
                data["file_id"]
            )

    except Exception as e:

        logging.error(f"[Menfess] Gagal kirim: {e}")

        return await bot.send_message(
            user_id,
            "❌ Gagal mengirim menfess."
        )

    await bot.send_message(
        user_id,
        "✅ Menfess berhasil dikirim!"
    )

    # Kirim link postingan (kalau bisa dibangun)
    if sent:
        url = await build_channel_post_link(bot, CHANNEL_ID, sent.message_id)
        if url:
            try:
                upsert_user_last_post(user_id, url, sent.message_id)
            except Exception as e:
                logging.warning(f"[LastPost] Gagal simpan last post user {user_id}: {e}")
            await bot.send_message(
                user_id,
                "🔗 Ini link menfess kamu di channel.",
                reply_markup=post_link_keyboard(url)
            )

    if sent and AUTO_DELETE_HOURS > 0:
        asyncio.create_task(
            auto_delete(bot, CHANNEL_ID, sent.message_id)
        )


# ========================
# CANCEL
# ========================

@router.callback_query(F.data == "confirm_cancel")
async def confirm_cancel(callback: CallbackQuery):

    user_id = callback.from_user.id

    _pending_confirm.pop(user_id, None)

    await callback.answer("Dibatalkan")

    try:
        await callback.message.edit_text(
            "❌ Menfess dibatalkan."
        )
    except Exception:
        pass
