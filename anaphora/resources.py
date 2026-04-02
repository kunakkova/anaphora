from .data_loader import load_word_set
from .morph import normalize_word, morph

DATA_DIR = 'data/'

personal_pronouns = load_word_set(DATA_DIR + 'Личные.txt')
possessive_pronouns = load_word_set(DATA_DIR + 'Притяжательные.txt')
ambiguous_pronouns = load_word_set(DATA_DIR + 'Лично-притяжательные.txt')
reflexive_pronouns = load_word_set(DATA_DIR + 'Возвратные.txt')
relative_pronouns = load_word_set(DATA_DIR + 'Относительные.txt')

_demonstrative_base = load_word_set(DATA_DIR + 'Указательные.txt')
demonstrative_pronouns = set(_demonstrative_base)
for base in _demonstrative_base:
    parsed = morph.parse(base)
    if parsed:
        for form in parsed[0].lexeme:
            demonstrative_pronouns.add(normalize_word(form.word))

collective_nouns = load_word_set(DATA_DIR + 'Собирательные.txt')
common_gender_nouns = load_word_set(DATA_DIR + 'Общий род.txt')
idioms = load_word_set(DATA_DIR + 'Идиомы.txt')

all_pronouns = (
    personal_pronouns |
    possessive_pronouns |
    ambiguous_pronouns |
    reflexive_pronouns |
    relative_pronouns |
    demonstrative_pronouns
)

