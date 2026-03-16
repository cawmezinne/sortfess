from aiogram import Router, types, Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
from aiogram import F
from db import add_user, add_report
from config import REQUIRED_CHANNELS, VALID_HASHTAGS
from utils import get_post_status

router = Router()

# Tombol subscribe
def sub_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="命 ｡ Base Menfess", url="https://t.me/sortfess")],
        [InlineKeyboardButton(text="命 ｡ Heart Heart", url="https://t.me/fiIIyourheart")],
        [InlineKeyboardButton(text="✦ Done Subscribe", callback_data="check_sub")]
        ])

# Tombol info setelah subscribe
def info_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="✸ Rules", url="https://t.me/sortfess/5")],
    [InlineKeyboardButton(text="𖥔 Admin", url="https://t.me/sortfess/6")]
    ])

# Format list hashtag
def hashtag_info() -> str:
    return "\n".join([f"• <b>{tag}</b> → {desc}" for tag, desc in VALID_HASHTAGS.items()])

# ========================
# /start
# ========================

@router.message(Command("start"))
async def start_cmd(message: types.Message):
    add_user(message.from_user.id, message.from_user.username or "")

    caption = (
        "<b>⾕ — Welcome to Sort Menfess!</b>\n\n"
        "Mau kirim confess buat orang? Pengakuan? Sambat? Atau bahkan cerita hal diluar nurul?\n"
        "Gampang kok! Cukup pake hashtag sesuai jenisnya:\n\n"
        f"{hashtag_info()}\n\n"
        "Tapi subscribe dulu ya sebelum ngirim menfess, klik tombol di bawah ini. ⬇"
    )

    await message.answer_photo(
        photo="https://raw.githubusercontent.com/zarcoza/sortfess/main/banner.png",
        caption=caption,
        reply_markup=sub_keyboard(),
        parse_mode="HTML"
    )

# ========================
# /myid
# ========================

@router.message(Command("myid"))
async def myid_cmd(message: types.Message):
    user = message.from_user
    username = f"@{user.username}" if user.username else "(tidak ada)"
    await message.reply(
        f"👤 <b>Info Kamu</b>\n\n"
        f"🆔 ID: <code>{user.id}</code>\n"
        f"📛 Nama: {user.full_name}\n"
        f"🔗 Username: {username}",
        parse_mode="HTML"
    )

# ========================
# /status
# ========================

@router.message(Command("status"))
async def status_cmd(message: types.Message):
    is_open = get_post_status()
    if is_open:
        await message.reply("✅ Base sedang <b>BUKA</b>! Silakan kirim menfess~", parse_mode="HTML")
    else:
        await message.reply("🔒 Base sedang <b>TUTUP</b>. Tunggu dibuka lagi ya~", parse_mode="HTML")

# ========================
# /hashtags
# ========================

@router.message(Command("hashtags"))
async def hashtags_cmd(message: types.Message):
    await message.reply(
        f"📌 <b>Daftar Hashtag SortFess</b>\n\n{hashtag_info()}\n\n"
        "Gunakan salah satu hashtag di atas saat mengirim menfess ya!",
        parse_mode="HTML"
    )

# ========================
# /report
# ========================

@router.message(Command("report"))
async def report_cmd(message: types.Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        return await message.reply(
            "❗ Format: <code>/report &lt;alasan&gt;</code>\n"
            "Contoh: <code>/report menfess ini mengandung ujaran kebencian</code>",
            parse_mode="HTML"
        )

    reason = parts[1]
    # Cek apakah reply ke pesan
    reply_text = ""
    if message.reply_to_message:
        reply_text = message.reply_to_message.text or message.reply_to_message.caption or "[media]"
    else:
        reply_text = "(tidak ada pesan yang di-reply)"

    report_id = add_report(
        reporter_id=message.from_user.id,
        message_text=reply_text,
        reason=reason
    )

    await message.reply(
        f"✅ Laporan #{report_id} telah dikirim ke admin.\n"
        "Terima kasih sudah membantu menjaga base! 🙏"
    )

# ========================
# Callback: Check Subscription
# ========================

@router.callback_query(F.data == "check_sub")
async def check_subscription(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    all_joined = True

    for channel in REQUIRED_CHANNELS:
        try:
            member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status in ["left", "kicked"]:
                all_joined = False
                break
        except Exception as e:
            print(f"Error checking subscription: {e}")
            all_joined = False
            break

    await callback.answer()

    try:
        await callback.message.delete()
    except Exception:
        pass

    if all_joined:
        try:
            await bot.send_message(
                chat_id=user_id,
                text="☆ Oke kamu sudah subscribe, bisa mulai ngirim menfess yaa!",
                reply_markup=info_keyboard(),
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"Gagal kirim pesan ke user: {e}")
    else:
        try:
            await bot.send_message(
                chat_id=user_id,
                text="𖦹 Waduh kamu belum subscribe nih, subscribe dulu yaa!",
                reply_markup=sub_keyboard(),
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"Gagal kirim pesan ke user: {e}")
