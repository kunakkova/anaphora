import re
from nltk.tokenize import sent_tokenize, word_tokenize
from .resources import all_pronouns
from .morph import normalize_word

def find_pronoun_indices(text: str):
    pattern = r'\b[а-яё]+\b'
    lower_text = text.lower()
    matches = re.finditer(pattern, lower_text)
    indices = []
    for match in matches:
        word = match.group()
        normalized_word = normalize_word(word)
        if normalized_word in all_pronouns:
            start = match.start()
            end = match.end()
            indices.append((start, end))
    return indices

def get_sentences(text: str):
    return sent_tokenize(text, language='russian')

def get_words(text: str):
    return word_tokenize(text, language='russian')

