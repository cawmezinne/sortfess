import re
from typing import List

# ✨ Kumpulan pola regex untuk deteksi kata kasar & variasinya
BAD_WORDS_REGEX = {
    'asu':       r'a[\$s5]?[^\w]*u+',
    'wts':       r'w[3e][t7][e3][sz5]+',
    'bangsat':   r'b[a4]ngs[a@]t',
    'kontol':    r'k[o0]nt[o0]l',
    'memek':     r'm[e3]m[e3]k',
    'wtb':       r'w[\W_]*[t7][\W_]*[b8]',
    'yatim':     r'y[\W_]*[a4][\W_]*t[\W_]*[i1][\W_]*[m]',
    'piatu':     r'p[\W_]*[i1][\W_]*[a4][\W_]*t[\W_]*[u]',
    'jual':      r'j[\W_]*u[\W_]*[a4][\W_]*[l1]',
    'jualan':    r'j[\W_]*u[\W_]*[a4][\W_]*[l1][\W_]*[a4][\W_]*n',
    'kinci':     r'k[\W_]*[i1][\W_]*n[\W_]*c[\W_]*[i1]',
    'freelance': r'f[\W_]*r[\W_]*[e3]{2}[\W_]*l[\W_]*[a4][\W_]*n[\W_]*c[\W_]*[e3]',
    'jb':        r'j[\W_]*[b8]',
}

def contains_bad_word(text: str) -> bool:
    """Cek apakah teks mengandung kata kasar."""
    text = text.lower()
    return any(re.search(pattern, text) for pattern in BAD_WORDS_REGEX.values())

# (opsional) Jika kamu ingin tahu kata mana yang terdeteksi:
def find_bad_words(text: str) -> List[str]:
    """Kembalikan daftar kata kasar yang terdeteksi dalam teks."""
    text = text.lower()
    detected = []
    for word, pattern in BAD_WORDS_REGEX.items():
        if re.search(pattern, text):
            detected.append(word)
    return detected
