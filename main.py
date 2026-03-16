import os
import asyncio
import signal
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import ErrorEvent
from config import BOT_TOKEN, ADMIN_IDS

# Import routers
from handlers.start import router as start_router
from handlers.menfess import router as menfess_router
from handlers.admin import router as admin_router

# Import middleware
from middleware import RateLimitMiddleware, AdminLoggingMiddleware

# ========================
# LOGGING SETUP
# ========================

LOG_DIR = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(LOG_DIR, 'bot.log'), encoding='utf-8'),
    ]
)
logger = logging.getLogger(__name__)

# ========================
# INISIALISASI
# ========================

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# Daftarkan middleware
dp.message.middleware(RateLimitMiddleware())
dp.message.middleware(AdminLoggingMiddleware(admin_ids=ADMIN_IDS))

# Daftarkan router (urutan penting: start & admin dulu, menfess terakhir)
dp.include_router(start_router)
dp.include_router(admin_router)
dp.include_router(menfess_router)

# ========================
# GLOBAL ERROR HANDLER
# ========================

@dp.errors()
async def global_error_handler(event: ErrorEvent):
    logger.exception(
        f"Unhandled error: {event.exception}",
        exc_info=event.exception,
    )
    # Coba kirim notifikasi ke user jika bisa
    try:
        update = event.update
        if update and update.message:
            await update.message.reply(
                "⚠️ Terjadi kesalahan. Coba lagi nanti ya~"
            )
    except Exception:
        pass
    return True  # Error sudah di-handle

# ========================
# MAIN
# ========================

async def main():
    logger.info("🤖 Bot Sort Menfess sedang berjalan...")

    # Graceful shutdown handler
    loop = asyncio.get_event_loop()
    shutdown_event = asyncio.Event()

    def _signal_handler():
        logger.info("⏹ Menerima sinyal shutdown...")
        shutdown_event.set()

    # Register signal handlers (hanya di Unix, di Windows pakai try/except)
    try:
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, _signal_handler)
    except NotImplementedError:
        # Windows tidak support add_signal_handler, gunakan KeyboardInterrupt
        pass

    try:
        await dp.start_polling(bot)
    except (KeyboardInterrupt, SystemExit):
        logger.info("⏹ Bot dihentikan oleh user.")
    except Exception as e:
        logger.error(f"❌ Terjadi error saat polling: {e}")
    finally:
        logger.info("🔌 Menutup koneksi bot...")
        await bot.session.close()
        logger.info("✅ Bot berhenti dengan bersih.")

# Entry point
if __name__ == "__main__":
    asyncio.run(main())
