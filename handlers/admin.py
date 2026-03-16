from aiogram import Router, types, Bot
from aiogram.filters import Command
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
from db import (
    get_all_users, get_last_posts, get_top_hashtags,
    ban_user, unban_user, is_banned, latest_post,
    add_admin_id, remove_admin_id, get_admin_ids, get_user_by_id,
    get_all_banned_users, clear_banlist, get_ban_reason,
    get_user_post_count, get_pending_menfess_list,
    get_pending_menfess_by_id, remove_pending_menfess,
    get_reports, clear_reports
)
from utils import set_post_status
from config import CHANNEL_ID
import asyncio
import logging
import html

router = Router()
admin_set = set(get_admin_ids())

def is_admin(user_id: int) -> bool:
    return user_id in admin_set

def extract_user_id_arg(message: types.Message):
    parts = message.text.split()
    return int(parts[1]) if len(parts) >= 2 and parts[1].isdigit() else None

# ========================
# BROADCAST & BALAS
# ========================

@router.message(Command("broadcast"))
async def broadcast_handler(message: types.Message):
    if not is_admin(message.from_user.id):
        return await message.reply(f"Maaf, kamu bukan admin.\nID kamu: <code>{message.from_user.id}</code>", parse_mode="HTML")

    msg = message.text[len("/broadcast"):].strip()
    if not msg:
        return await message.reply("Isi dulu dong pesannya.\nContoh: /broadcast Halo semua!")

    users = get_all_users()
    total, sent, failed = len(users), 0, 0

    await message.reply(f"📤 Broadcast dimulai ke {total} user...")

    for uid in users:
        try:
            await message.bot.send_message(uid, f"📢 <b>Broadcast Admin:</b>\n\n{msg}", parse_mode="HTML")
            sent += 1
            await asyncio.sleep(0.05)
        except (TelegramForbiddenError, TelegramBadRequest):
            failed += 1
        except Exception as e:
            logging.error(f"Gagal kirim ke {uid}: {e}")
            failed += 1

    await message.reply(
        f"📣 Broadcast selesai!\n"
        f"👥 Total user: {total}\n"
        f"✅ Terkirim: {sent}\n"
        f"❌ Gagal: {failed}"
    )

@router.message(Command("balas"))
async def reply_user(message: types.Message):
    if not is_admin(message.from_user.id):
        return await message.reply(f"❌ Kamu bukan admin.\nID kamu: <code>{message.from_user.id}</code>", parse_mode="HTML")

    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        return await message.reply("❗ Format salah.\nGunakan: /balas <user_id> <pesan>")

    try:
        user_id = int(parts[1])
        reply_msg = parts[2]
        await message.bot.send_message(user_id, f"👩‍💻 <b>Balasan Admin:</b>\n\n{reply_msg}", parse_mode="HTML")
        await message.reply("✅ Pesan berhasil dikirim!")
    except TelegramForbiddenError:
        await message.reply("❌ Gagal kirim. User mungkin telah memblokir bot.")
    except TelegramBadRequest:
        await message.reply("❌ Gagal kirim. Mungkin user_id tidak valid.")
    except Exception as e:
        await message.reply(f"⚠️ Terjadi error:\n<code>{e}</code>", parse_mode="HTML")

# ========================
# KONTROL BASE
# ========================

@router.message(Command("tutup"))
async def tutup_base(message: types.Message):
    if is_admin(message.from_user.id):
        set_post_status(False)
        await message.reply("🔒 <b>Base ditutup sementara.</b>\nLagi istirahat dulu yaa~ 😴", parse_mode="HTML")

@router.message(Command("buka"))
async def buka_base(message: types.Message):
    if is_admin(message.from_user.id):
        set_post_status(True)
        await message.reply("✅ <b>Base sudah dibuka lagi!</b>\nSilakan kirim menfess sekarang ya! 🚀", parse_mode="HTML")

# ========================
# STATISTIK
# ========================

@router.message(Command("stat"))
async def show_stats(message: types.Message):
    if is_admin(message.from_user.id):
        total = len(get_all_users())
        banned_count = len(get_all_banned_users())
        top = get_top_hashtags(3)
        top_text = "\n".join([f"  • {tag}: {count}x" for tag, count in top]) if top else "  Belum ada data"
        await message.reply(
            f"📊 <b>Statistik SortFess</b>\n\n"
            f"👥 Total pengguna: <b>{total}</b>\n"
            f"🚫 User diblokir: <b>{banned_count}</b>\n\n"
            f"🔥 <b>Top Hashtag:</b>\n{top_text}",
            parse_mode="HTML"
        )

@router.message(Command("tophashtag"))
async def top_hashtag_cmd(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    top = get_top_hashtags(10)
    if not top:
        return await message.reply("ℹ️ Belum ada data hashtag.")
    lines = [f"  {i+1}. <b>{tag}</b> — {count}x" for i, (tag, count) in enumerate(top)]
    await message.reply("📈 <b>Top Hashtag:</b>\n\n" + "\n".join(lines), parse_mode="HTML")

@router.message(Command("last10"))
async def last_10_posters(message: types.Message):
    if is_admin(message.from_user.id):
        posts = get_last_posts()
        if not posts:
            return await message.reply("ℹ️ Belum ada menfess terbaru.")
        result_lines = [
            f"👤 <b>{uid}</b>:\n{html.escape(text[:200]) + '...' if len(text) > 200 else html.escape(text)}"
            for uid, text in posts
        ]
        await message.reply("🕵️‍♂️ <b>Riwayat Pengirim Terakhir:</b>\n\n" + "\n\n".join(result_lines), parse_mode="HTML")

# ========================
# MANAJEMEN PENGGUNA (BAN/UNBAN)
# ========================

@router.message(Command("ban"))
async def ban_cmd(message: types.Message):
    if not is_admin(message.from_user.id):
        return

    parts = message.text.split(maxsplit=2)
    if len(parts) < 2 or not parts[1].isdigit():
        return await message.reply("❗ Format salah.\nContoh: <code>/ban 123456789</code>\nAtau: <code>/ban 123456789 spam</code>", parse_mode="HTML")

    uid = int(parts[1])
    reason = parts[2] if len(parts) >= 3 else None

    if uid == message.from_user.id:
        return await message.reply("⚠️ Kamu tidak bisa blokir diri sendiri 😅")

    ban_user(uid, reason)
    reason_text = f"\n📝 Alasan: {html.escape(reason)}" if reason else ""
    await message.reply(f"🚫 User <code>{uid}</code> telah diblokir.{reason_text}", parse_mode="HTML")

@router.message(Command("unban"))
async def unban_cmd(message: types.Message):
    if is_admin(message.from_user.id):
        uid = extract_user_id_arg(message)
        if uid is None:
            return await message.reply("❗ Format salah.\nContoh: <code>/unban 123456789</code>", parse_mode="HTML")
        unban_user(uid)
        await message.reply(f"✅ User <code>{uid}</code> sudah tidak diblokir lagi.", parse_mode="HTML")

@router.message(Command("listban"))
async def list_banned_users(message: types.Message):
    if is_admin(message.from_user.id):
        banned = get_all_banned_users()
        if not banned:
            return await message.reply("✅ Tidak ada user yang sedang diblokir.")
        lines = []
        for uid, reason in banned:
            line = f"• <code>{uid}</code>"
            if reason:
                line += f" — {html.escape(reason)}"
            lines.append(line)
        text = "🚫 <b>Daftar User Terblokir:</b>\n" + "\n".join(lines)
        await message.reply(text, parse_mode="HTML")

@router.message(Command("clearban"))
async def clearban_cmd(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    clear_banlist()
    await message.reply("🗑️ Semua user sudah di-unban.")

@router.message(Command("cekuser"))
async def cekuser_cmd(message: types.Message):
    if not is_admin(message.from_user.id):
        return

    uid = extract_user_id_arg(message)
    if uid is None:
        return await message.reply("❗ Format: <code>/cekuser 123456789</code>", parse_mode="HTML")

    user = get_user_by_id(uid)
    banned = is_banned(uid)
    post_count = get_user_post_count(uid)
    reason = get_ban_reason(uid) if banned else None

    if not user:
        return await message.reply(f"ℹ️ User <code>{uid}</code> tidak ditemukan di database.", parse_mode="HTML")

    username = user.get("username")
    status = "🚫 Diblokir" if banned else "✅ Aktif"
    reason_text = f"\n📝 Alasan ban: {html.escape(reason)}" if reason else ""

    await message.reply(
        f"👤 <b>Info User</b>\n\n"
        f"🆔 ID: <code>{uid}</code>\n"
        f"🔗 Username: {'@' + username if username else '(tidak ada)'}\n"
        f"📊 Jumlah post: {post_count}\n"
        f"📌 Status: {status}{reason_text}",
        parse_mode="HTML"
    )

# ========================
# MANAJEMEN ADMIN
# ========================

@router.message(Command("addadmin"))
async def add_admin_cmd(message: types.Message):
    if is_admin(message.from_user.id):
        uid = extract_user_id_arg(message)
        if uid is None:
            return await message.reply("Format: /addadmin <user_id>")
        if is_admin(uid):
            return await message.reply(f"⚠️ User <code>{uid}</code> sudah menjadi admin.", parse_mode="HTML")
        add_admin_id(uid)
        admin_set.add(uid)
        await message.reply(f"✅ User <code>{uid}</code> telah ditambahkan sebagai admin.", parse_mode="HTML")

@router.message(Command("deladmin"))
async def del_admin_cmd(message: types.Message):
    if is_admin(message.from_user.id):
        uid = extract_user_id_arg(message)
        if uid is None:
            return await message.reply("Format: /deladmin <user_id>")
        if not is_admin(uid):
            return await message.reply(f"⚠️ User <code>{uid}</code> bukan admin.", parse_mode="HTML")
        remove_admin_id(uid)
        admin_set.discard(uid)
        await message.reply(f"🗑️ User <code>{uid}</code> telah dihapus dari admin.", parse_mode="HTML")

@router.message(Command("listadmin"))
async def list_admin_cmd(message: types.Message):
    if is_admin(message.from_user.id):
        if not admin_set:
            return await message.reply("Belum ada admin terdaftar.")
        result = []
        for uid in sorted(admin_set):
            user = get_user_by_id(uid)
            uname = user.get("username") if user else None
            if uname:
                line = f"• <code>{uid}</code> [<i>@{uname}</i>]"
            else:
                line = f"• <code>{uid}</code>"
            result.append(line)
        await message.reply("👑 <b>Daftar Admin Aktif:</b>\n\n" + "\n".join(result), parse_mode="HTML")

# ========================
# APPROVAL MODE (PENDING MENFESS)
# ========================

@router.message(Command("pending"))
async def pending_cmd(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    pending = get_pending_menfess_list(10)
    if not pending:
        return await message.reply("✅ Tidak ada menfess pending.")
    lines = []
    for p in pending:
        preview = html.escape((p["text"] or "")[:100])
        lines.append(
            f"📝 <b>ID #{p['id']}</b> | User: <code>{p['user_id']}</code>\n"
            f"   Tipe: {p['content_type']} | {p['created_at']}\n"
            f"   {preview}{'...' if len(p['text'] or '') > 100 else ''}"
        )
    await message.reply("📋 <b>Antrian Menfess Pending:</b>\n\n" + "\n\n".join(lines), parse_mode="HTML")

@router.message(Command("approve"))
async def approve_cmd(message: types.Message, bot: Bot):
    if not is_admin(message.from_user.id):
        return

    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        return await message.reply("❗ Format: <code>/approve &lt;id&gt;</code>", parse_mode="HTML")

    menfess_id = int(parts[1])
    menfess = get_pending_menfess_by_id(menfess_id)
    if not menfess:
        return await message.reply(f"❌ Menfess #{menfess_id} tidak ditemukan.")

    try:
        if menfess["content_type"] == "text":
            sent = await bot.send_message(
                chat_id=CHANNEL_ID,
                text=menfess["text"],
                parse_mode="HTML"
            )
        elif menfess["content_type"] == "photo":
            sent = await bot.send_photo(
                chat_id=CHANNEL_ID,
                photo=menfess["file_id"],
                caption=menfess["text"],
                parse_mode="HTML"
            )
        elif menfess["content_type"] == "document":
            sent = await bot.send_document(
                chat_id=CHANNEL_ID,
                document=menfess["file_id"],
                caption=menfess["text"],
                parse_mode="HTML"
            )
        elif menfess["content_type"] == "video":
            sent = await bot.send_video(
                chat_id=CHANNEL_ID,
                video=menfess["file_id"],
                caption=menfess["text"],
                parse_mode="HTML"
            )
        else:
            sent = await bot.send_message(
                chat_id=CHANNEL_ID,
                text=menfess["text"] or "[Konten tidak diketahui]",
                parse_mode="HTML"
            )

        remove_pending_menfess(menfess_id)

        # Notifikasi ke pengirim
        try:
            await bot.send_message(
                menfess["user_id"],
                "✅ Menfess #tellem kamu sudah di-approve dan dikirim ke base!"
            )
        except Exception:
            pass

        await message.reply(f"✅ Menfess #{menfess_id} di-approve dan dikirim ke channel.")
    except Exception as e:
        await message.reply(f"❌ Gagal kirim: <code>{html.escape(str(e))}</code>", parse_mode="HTML")

@router.message(Command("reject"))
async def reject_cmd(message: types.Message, bot: Bot):
    if not is_admin(message.from_user.id):
        return

    parts = message.text.split(maxsplit=2)
    if len(parts) < 2 or not parts[1].isdigit():
        return await message.reply("❗ Format: <code>/reject &lt;id&gt; [alasan]</code>", parse_mode="HTML")

    menfess_id = int(parts[1])
    reason = parts[2] if len(parts) >= 3 else "Tidak sesuai ketentuan"
    menfess = get_pending_menfess_by_id(menfess_id)

    if not menfess:
        return await message.reply(f"❌ Menfess #{menfess_id} tidak ditemukan.")

    remove_pending_menfess(menfess_id)

    # Notifikasi ke pengirim
    try:
        await bot.send_message(
            menfess["user_id"],
            f"❌ Menfess #tellem kamu ditolak.\n📝 Alasan: {reason}"
        )
    except Exception:
        pass

    await message.reply(f"🗑️ Menfess #{menfess_id} ditolak.\nAlasan: {reason}")

# ========================
# REPORTS
# ========================

@router.message(Command("reports"))
async def reports_cmd(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    reports = get_reports(10)
    if not reports:
        return await message.reply("✅ Tidak ada laporan.")
    lines = []
    for r in reports:
        lines.append(
            f"🔴 <b>Report #{r['id']}</b>\n"
            f"   Reporter: <code>{r['reporter_id']}</code>\n"
            f"   Alasan: {html.escape(r['reason'])}\n"
            f"   Pesan: {html.escape((r['message_text'] or '')[:100])}\n"
            f"   Waktu: {r['created_at']}"
        )
    await message.reply("📋 <b>Laporan Terbaru:</b>\n\n" + "\n\n".join(lines), parse_mode="HTML")

@router.message(Command("clearreports"))
async def clearreports_cmd(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    clear_reports()
    await message.reply("🗑️ Semua laporan sudah dihapus.")

# ========================
# HELP ADMIN
# ========================

@router.message(Command("help_admin"))
async def help_admin(message: types.Message):
    if not is_admin(message.from_user.id):
        return await message.reply("🚫 Khusus admin yaa.")
    help_text = (
        "📖 <b>Panel Bantuan Admin — SortFess</b>\n\n"
        "🔊 <b>Broadcast & Balas</b>\n"
        "• <code>/broadcast &lt;pesan&gt;</code>\n"
        "• <code>/balas &lt;user_id&gt; &lt;pesan&gt;</code>\n\n"
        "🚪 <b>Kontrol Base</b>\n"
        "• <code>/tutup</code> / <code>/buka</code>\n\n"
        "📊 <b>Statistik</b>\n"
        "• <code>/stat</code>\n"
        "• <code>/tophashtag</code>\n"
        "• <code>/last10</code>\n\n"
        "🔒 <b>Manajemen Pengguna</b>\n"
        "• <code>/ban &lt;user_id&gt; [alasan]</code>\n"
        "• <code>/unban &lt;user_id&gt;</code>\n"
        "• <code>/listban</code> / <code>/clearban</code>\n"
        "• <code>/cekuser &lt;user_id&gt;</code>\n\n"
        "🛡 <b>Manajemen Admin</b>\n"
        "• <code>/addadmin &lt;user_id&gt;</code>\n"
        "• <code>/deladmin &lt;user_id&gt;</code>\n"
        "• <code>/listadmin</code>\n\n"
        "📋 <b>Approval Mode (#tellem)</b>\n"
        "• <code>/pending</code> — lihat antrian\n"
        "• <code>/approve &lt;id&gt;</code>\n"
        "• <code>/reject &lt;id&gt; [alasan]</code>\n\n"
        "📢 <b>Reports</b>\n"
        "• <code>/reports</code>\n"
        "• <code>/clearreports</code>\n"
    )
    await message.reply(help_text, parse_mode="HTML")
