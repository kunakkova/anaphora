from .morph import get_pos, normalize_word
from .resources import (
    personal_pronouns,
    possessive_pronouns,
    ambiguous_pronouns,
    reflexive_pronouns,
    relative_pronouns,
)

def determine_pronoun_type(word, next_word):
    w = normalize_word(word)
    pos_next = get_pos(next_word)
    if w in ambiguous_pronouns:
        if pos_next == 'NOUN':
            return 'притяжательное'
        else:
            return 'личное'
    elif w in personal_pronouns:
        return 'личное'
    elif w in possessive_pronouns:
        return 'притяжательное'
    elif w in reflexive_pronouns:
        return 'возвратное'
    elif w in relative_pronouns:
        return 'относительное'
    else:
        return None

