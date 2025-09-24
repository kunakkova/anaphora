from .morph import normalize_word

def load_lines(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return [line for line in f.read().splitlines() if line.strip()]

def load_word_set(filepath):
    return set(normalize_word(line) for line in load_lines(filepath))

