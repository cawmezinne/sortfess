import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN', '')
CHANNEL_ID = int(os.getenv('CHANNEL_ID', '-1002538940104'))
ADMIN_IDS = set(int(x) for x in os.getenv('ADMIN_IDS', '').split(',') if x.strip())
REQUIRED_CHANNELS = [x.strip() for x in os.getenv('REQUIRED_CHANNELS', '').split(',') if x.strip()]

# Auto-delete menfess setelah X jam (0 = nonaktif)
AUTO_DELETE_HOURS = int(os.getenv('AUTO_DELETE_HOURS', '0'))

# Cooldown per user dalam detik
# 0 = nonaktif (tanpa limit)
COOLDOWN_SECONDS = int(os.getenv('COOLDOWN_SECONDS', '0'))

# Daftar hashtag yang valid untuk menfess
VALID_HASHTAGS = {
    '#sorta': 'Kirim menfess bebas rp/rl',
    '#kinda': 'Buat sambat/curhat',
    '#tellem': 'Buat yang berbau tabu & horror (NSFW, TW, hal-hal diluar nalar, dll)',
    '#gonna': 'Menfess terbuka dengan nama asli, bisa ditujukan ke orang-orang tertentu',
    '#wanna': 'Hashtag buat yang mau nanya biar dapet solusi'
}