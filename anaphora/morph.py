import pymorphy3

morph = pymorphy3.MorphAnalyzer()

def get_pos(word):
    if word is None:
        return None
    p = morph.parse(word)[0]
    return p.tag.POS

def normalize_word(word: str) -> str:
    return word.lower().replace('ё', 'е')

