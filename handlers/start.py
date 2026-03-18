from aiogram import Router, types, Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
from aiogram import F
import html
import random
from db import add_user, add_report, get_user_post_count, latest_post, get_user_last_post
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

def template_keyboard() -> InlineKeyboardMarkup:
    rows = []
    tags = list(VALID_HASHTAGS.keys())
    for i in range(0, len(tags), 2):
        row = []
        for tag in tags[i:i+2]:
            row.append(InlineKeyboardButton(text=tag, callback_data=f"tpl:{tag}"))
        rows.append(row)
    rows.append([InlineKeyboardButton(text="🎲 Random prompt", callback_data="tpl:prompt")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def _template_text(tag: str) -> str:
    tag = tag.lower().strip()
    if tag not in VALID_HASHTAGS:
        return (
            "⚠️ Template tidak ditemukan.\n\n"
            "Ketik /template lagi untuk pilih hashtag."
        )
    desc = VALID_HASHTAGS[tag]
    examples = {
        "#sorta":  f"{tag} (tulis menfess kamu di sini...)\n\nContoh:\n{tag} aku suka kamu dari jauh tapi gengsi ngomong",
        "#kinda":  f"{tag} (curhat/sambat di sini...)\n\nContoh:\n{tag} capek banget hari ini, pengen istirahat",
        "#tellem": f"{tag} (konten sensitif/tw...)\n\nContoh:\n{tag} tw: mimpi buruk semalam dan masih kebayang",
        "#gonna":  f"{tag} (identitas TERBUKA)\n\nContoh:\n{tag} aku (nama kamu) mau minta maaf kemarin...",
        "#wanna":  f"{tag} (tanya biar dapet solusi)\n\nContoh:\n{tag} gimana cara move on yang bener?",
    }
    body = examples.get(tag, f"{tag} (tulis menfess kamu di sini...)")
    return (
        f"🧾 <b>Template {tag}</b>\n"
        f"ℹ️ {html.escape(desc)}\n\n"
        f"<code>{html.escape(body)}</code>\n\n"
        "Salin teks di atas, lalu kirim sebagai menfess ya."
    )

def _random_prompt_text() -> str:
    prompts = [
        "Ceritain 1 hal kecil yang bikin kamu senyum hari ini.",
        "Apa yang pengen kamu bilang ke seseorang tapi belum sempet?",
        "Kalau bisa ngulang 1 momen minggu ini, momen apa?",
        "Satu hal yang kamu syukuri akhir-akhir ini?",
        "Apa yang lagi kamu tunggu-tunggu sekarang?",
        "Hal paling random yang kepikiran kamu barusan?",
        "Kalimat yang pengen kamu denger dari seseorang itu apa?",
        "Kalau kamu bisa jujur 100%, kamu lagi ngerasa apa?",
    ]
    p = random.choice(prompts)
    return (
        "🎲 <b>Random prompt</b>\n\n"
        f"{html.escape(p)}\n\n"
        "Kamu bisa jawab pakai hashtag yang kamu mau. Contoh:\n"
        "<code>#sorta (jawaban kamu)</code>"
    )

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

@router.message(Command("template"))
async def template_cmd(message: types.Message):
    """
    /template
    Bantu user dengan format menfess siap-copas.
    """
    add_user(message.from_user.id, message.from_user.username or "")
    await message.reply(
        "🧾 <b>Pilih template hashtag</b>\n"
        "Klik salah satu tombol di bawah, nanti bot kirim format siap-copas.",
        reply_markup=template_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("tpl:"))
async def template_pick(callback: CallbackQuery):
    add_user(callback.from_user.id, callback.from_user.username or "")
    data = callback.data.split(":", 1)[1]
    await callback.answer()
    if data == "prompt":
        return await callback.message.reply(_random_prompt_text(), parse_mode="HTML")
    return await callback.message.reply(_template_text(data), parse_mode="HTML")


@router.message(Command("prompt"))
async def prompt_cmd(message: types.Message):
    """
    /prompt
    Kasih ide/pancingan menfess secara random.
    """
    add_user(message.from_user.id, message.from_user.username or "")
    await message.reply(_random_prompt_text(), parse_mode="HTML")


@router.message(Command("last"))
async def last_cmd(message: types.Message):
    """
    /last
    Ambil link menfess terakhir kamu yang berhasil terkirim.
    """
    user_id = message.from_user.id
    add_user(user_id, message.from_user.username or "")

    last = get_user_last_post(user_id)
    if not last or not last.get("url"):
        return await message.reply(
            "ℹ️ Belum ada link menfess terakhir yang tersimpan.\n"
            "Coba kirim menfess dulu, nanti bot akan kasih tombol link.",
            parse_mode="HTML",
        )

    url = last["url"]
    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔗 Lihat Postingan", url=url)]]
    )
    await message.reply(
        "🔗 Ini link menfess terakhir kamu di channel.",
        reply_markup=kb,
        parse_mode="HTML",
    )


@router.message(Command("mystats"))
async def mystats_cmd(message: types.Message):
    """
    /mystats
    Lihat ringkasan aktivitas kamu di bot.
    """
    user = message.from_user
    user_id = user.id
    add_user(user_id, user.username or "")

    count = get_user_post_count(user_id)
    last_text = latest_post(user_id) or ""
    preview = html.escape(last_text[:200]) + ("..." if len(last_text) > 200 else "") if last_text else "(belum ada)"

    last_link = get_user_last_post(user_id)
    kb = None
    if last_link and last_link.get("url"):
        kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🔗 Lihat Postingan Terakhir", url=last_link["url"])]]
        )

    await message.reply(
        "📊 <b>Statistik Kamu</b>\n\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        f"👤 Nama: {html.escape(user.full_name)}\n"
        f"📦 Total menfess terkirim: <b>{count}</b>\n\n"
        f"📝 <b>Preview terakhir:</b>\n{preview}",
        reply_markup=kb,
        parse_mode="HTML",
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
