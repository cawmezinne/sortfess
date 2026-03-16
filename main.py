import os
import asyncio
import signal
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import ErrorEvent

# ========================
# CONFIG (langsung di kode)
# ========================

BOT_TOKEN = "7685483291:AAHUPE6n4gsNSkdGMgdqhaXmXhLn7xUrG0s"
CHANNEL_ID = -1002538940104

ADMIN_IDS = [1538087933, 7608777733]

REQUIRED_CHANNELS = [
    "@sortfess",
    "@fiIIyourheart"
]

AUTO_DELETE_HOURS = 24
COOLDOWN_SECONDS = 120


# ========================
# IMPORT ROUTERS
# ========================

from handlers.start import router as start_router
from handlers.menfess import router as menfess_router
from handlers.admin import router as admin_router

# ========================
# IMPORT MIDDLEWARE
# ========================

from middleware import RateLimitMiddleware, AdminLoggingMiddleware

# ========================
# LOGGING SETUP
# ========================

LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(LOG_DIR, "bot.log"), encoding="utf-8"),
    ],
)

logger = logging.getLogger(__name__)

# ========================
# INISIALISASI BOT
# ========================

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

dp = Dispatcher()

# ========================
# REGISTER MIDDLEWARE
# ========================

dp.message.middleware(RateLimitMiddleware())
dp.message.middleware(AdminLoggingMiddleware(admin_ids=ADMIN_IDS))

# ========================
# REGISTER ROUTERS
# ========================

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

    try:
        update = event.update
        if update and update.message:
            await update.message.reply(
                "⚠️ Terjadi kesalahan. Coba lagi nanti ya~"
            )
    except Exception:
        pass

    return True


# ========================
# MAIN
# ========================

async def main():
    logger.info("🤖 Bot Sort Menfess sedang berjalan...")
    
    chat = await bot.get_chat(-1002538940104)
    print(chat)

    loop = asyncio.get_event_loop()

    def shutdown():
        logger.info("⏹ Shutdown signal diterima")

    try:
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, shutdown)
    except NotImplementedError:
        pass

    try:
        await dp.start_polling(bot)
    except (KeyboardInterrupt, SystemExit):
        logger.info("⏹ Bot dihentikan")
    finally:
        logger.info("🔌 Menutup koneksi bot...")
        await bot.session.close()
        logger.info("✅ Bot berhenti dengan bersih.")


if __name__ == "__main__":
    asyncio.run(main())
