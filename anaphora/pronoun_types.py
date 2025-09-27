from .morph import get_pos, normalize_word
from .resources import (
    personal_pronouns,
    possessive_pronouns,
    ambiguous_pronouns,
    reflexive_pronouns,
    relative_pronouns,
)


class PronounTypeState:
    START = "START"
    NORMALIZE = "NORMALIZE"
    CHECK_AMBIGUOUS = "CHECK_AMBIGUOUS"
    DISAMBIGUATE_BY_NEXT_POS = "DISAMBIGUATE_BY_NEXT_POS"
    CHECK_PERSONAL = "CHECK_PERSONAL"
    CHECK_POSSESSIVE = "CHECK_POSSESSIVE"
    CHECK_REFLEXIVE = "CHECK_REFLEXIVE"
    CHECK_RELATIVE = "CHECK_RELATIVE"
    DONE = "DONE"


class PronounTypeDFA:
    def __init__(self, word: str, next_word: str | None):
        self.original_word = word
        self.next_word = next_word
        self.word_norm: str | None = None
        self.next_pos: str | None = None
        self.result_type: str | None = None
        self.state: str = PronounTypeState.START

    def step(self) -> bool:
        if self.state == PronounTypeState.START:
            self.state = PronounTypeState.NORMALIZE
            return True

        if self.state == PronounTypeState.NORMALIZE:
            self.word_norm = normalize_word(self.original_word)
            self.next_pos = get_pos(self.next_word)
            self.state = PronounTypeState.CHECK_AMBIGUOUS
            return True

        if self.state == PronounTypeState.CHECK_AMBIGUOUS:
            if self.word_norm in ambiguous_pronouns:
                self.state = PronounTypeState.DISAMBIGUATE_BY_NEXT_POS
            else:
                self.state = PronounTypeState.CHECK_PERSONAL
            return True

        if self.state == PronounTypeState.DISAMBIGUATE_BY_NEXT_POS:
            if self.next_pos == 'NOUN':
                self.result_type = 'притяжательное'
            else:
                self.result_type = 'личное'
            self.state = PronounTypeState.DONE
            return True

        if self.state == PronounTypeState.CHECK_PERSONAL:
            if self.word_norm in personal_pronouns:
                self.result_type = 'личное'
                self.state = PronounTypeState.DONE
            else:
                self.state = PronounTypeState.CHECK_POSSESSIVE
            return True

        if self.state == PronounTypeState.CHECK_POSSESSIVE:
            if self.word_norm in possessive_pronouns:
                self.result_type = 'притяжательное'
                self.state = PronounTypeState.DONE
            else:
                self.state = PronounTypeState.CHECK_REFLEXIVE
            return True

        if self.state == PronounTypeState.CHECK_REFLEXIVE:
            if self.word_norm in reflexive_pronouns:
                self.result_type = 'возвратное'
                self.state = PronounTypeState.DONE
            else:
                self.state = PronounTypeState.CHECK_RELATIVE
            return True

        if self.state == PronounTypeState.CHECK_RELATIVE:
            if self.word_norm in relative_pronouns:
                self.result_type = 'относительное'
            else:
                self.result_type = None
            self.state = PronounTypeState.DONE
            return True

        if self.state == PronounTypeState.DONE:
            return False

        return False

    def run(self) -> str | None:
        while self.step():
            pass
        return self.result_type


def determine_pronoun_type(word, next_word):
    dfa = PronounTypeDFA(word, next_word)
    return dfa.run()

