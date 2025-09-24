from .data_loader import load_word_set

DATA_DIR = 'data/'

personal_pronouns = load_word_set(DATA_DIR + 'Личные.txt')
possessive_pronouns = load_word_set(DATA_DIR + 'Притяжательные.txt')
ambiguous_pronouns = load_word_set(DATA_DIR + 'Лично-притяжательные.txt')
reflexive_pronouns = load_word_set(DATA_DIR + 'Возвратные.txt')
relative_pronouns = load_word_set(DATA_DIR + 'Относительные.txt')

collective_nouns = load_word_set(DATA_DIR + 'Собирательные.txt')
common_gender_nouns = load_word_set(DATA_DIR + 'Общий род.txt')
idioms = load_word_set(DATA_DIR + 'Идиомы.txt')

all_pronouns = (
    personal_pronouns |
    possessive_pronouns |
    ambiguous_pronouns |
    reflexive_pronouns |
    relative_pronouns
)

