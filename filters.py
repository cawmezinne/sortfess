import re
from typing import List

# ✨ Filter kata kasar/non‑aktif (semua dibebaskan)
BAD_WORDS_REGEX = {}

def contains_bad_word(text: str) -> bool:
    """Saat ini filter dimatikan: selalu False."""
    return False

# (opsional) Jika kamu ingin tahu kata mana yang terdeteksi:
def find_bad_words(text: str) -> List[str]:
    """Filter dimatikan: tidak ada kata yang dianggap terlarang."""
    return []
