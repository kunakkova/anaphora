from .morph import morph, normalize_word, get_pos
from .resources import all_pronouns, collective_nouns, common_gender_nouns
from .helpers import find_coord_groups, find_addressed_entity, get_speaker_context, get_attribution_entities
from .tokenization import get_sentences, get_words

def is_collective_noun(word):
    return normalize_word(word) in collective_nouns

def is_common_gender_noun(word):
    return normalize_word(word) in common_gender_nouns

class ReferentSearchState:
    START = 'START'
    LOCATE_SENTENCE = 'LOCATE_SENTENCE'
    EXTRACT_CONTEXT = 'EXTRACT_CONTEXT'
    TOKENIZE_CONTEXT = 'TOKENIZE_CONTEXT'
    COLLECT_NOMINALS = 'COLLECT_NOMINALS'
    ADD_COORD_GROUPS = 'ADD_COORD_GROUPS'
    FIND_PRONOUN_WORD = 'FIND_PRONOUN_WORD'
    ADD_ADDRESSED_ENTITY = 'ADD_ADDRESSED_ENTITY'
    ADD_SPEAKER_CONTEXT = 'ADD_SPEAKER_CONTEXT'
    DONE = 'DONE'


class ReferentSearchDFA:
    def __init__(self, text: str, pronoun_position: int):
        self.text = text
        self.pronoun_position = pronoun_position
        self.text_lower = text.lower()
        self.sentences = get_sentences(text)
        self.current_sentence_idx = 0
        self.current_sentence_start = 0
        self.start_sentence_idx = 0
        self.end_sentence_idx = 0
        self.search_text = ''
        self.word_positions = []
        self.pronoun_word = None
        self.candidates = []
        self.state = ReferentSearchState.START

    def add_candidate(self, word, start, end, pos, normalized, gender=None, number=None, is_group=False):
        self.candidates.append({
            'word': word,
            'start': start,
            'end': end,
            'pos': pos,
            'normalized': normalized,
            'gender': gender,
            'number': number,
            'is_group': is_group
        })

    def step(self) -> bool:
        if self.state == ReferentSearchState.START:
            self.state = ReferentSearchState.LOCATE_SENTENCE
            return True

        if self.state == ReferentSearchState.LOCATE_SENTENCE:
            current_pos = 0
            for i, sentence in enumerate(self.sentences):
                sentence_length = len(sentence)
                if current_pos <= self.pronoun_position < current_pos + sentence_length:
                    self.current_sentence_idx = i
                    self.current_sentence_start = current_pos
                    break
                current_pos += sentence_length
            self.start_sentence_idx = max(0, self.current_sentence_idx - 3)
            self.end_sentence_idx = self.current_sentence_idx
            self.state = ReferentSearchState.EXTRACT_CONTEXT
            return True

        if self.state == ReferentSearchState.EXTRACT_CONTEXT:
            relevant_sentences = self.sentences[self.start_sentence_idx:self.end_sentence_idx+1]
            if self.current_sentence_idx > 0:
                relevant_part = self.text_lower[self.current_sentence_start:self.pronoun_position]
                relevant_sentences[-1] = relevant_part
            else:
                relevant_sentences[0] = relevant_sentences[0][:self.pronoun_position]
            self.search_text = " ".join(relevant_sentences)
            self.state = ReferentSearchState.TOKENIZE_CONTEXT
            return True

        if self.state == ReferentSearchState.TOKENIZE_CONTEXT:
            words = get_words(self.search_text)
            current_pos = 0
            self.word_positions = []
            for word in words:
                start = self.search_text.find(word, current_pos)
                end = start + len(word)
                self.word_positions.append((word, start, end))
                current_pos = end
            self.state = ReferentSearchState.COLLECT_NOMINALS
            return True

        if self.state == ReferentSearchState.COLLECT_NOMINALS:
            for word, start, end in self.word_positions:
                parsed = morph.parse(word)[0]
                pos = parsed.tag.POS
                normalized_word = normalize_word(word)
                gender = parsed.tag.gender
                number = parsed.tag.number
                if pos == 'NOUN' or normalized_word in all_pronouns:
                    vy_forms = {'вы', 'вас', 'вам', 'вами'}
                    if normalized_word in vy_forms:
                        self.add_candidate(word, start, end, pos, normalized_word, None, 'sing')
                        self.add_candidate(word, start, end, pos, normalized_word, None, 'plur')
                    elif is_common_gender_noun(word):
                        self.add_candidate(word, start, end, pos, normalized_word, 'masc', number)
                        self.add_candidate(word, start, end, pos, normalized_word, 'femn', number)
                    elif is_collective_noun(word):
                        self.add_candidate(word, start, end, pos, normalized_word, gender, 'sing')
                        self.add_candidate(word, start, end, pos, normalized_word, gender, 'plur')
                    else:
                        self.add_candidate(word, start, end, pos, normalized_word, gender, number)
            self.state = ReferentSearchState.ADD_COORD_GROUPS
            return True

        if self.state == ReferentSearchState.ADD_COORD_GROUPS:
            full_search_text = " ".join(self.sentences[self.start_sentence_idx:self.end_sentence_idx+1])
            coord_groups = find_coord_groups(full_search_text)
            for group in coord_groups:
                if len(group) > 1:
                    group_text = " и ".join(group)
                    self.add_candidate(group_text, -1, -1, 'NOUN', group_text.lower(), None, 'plur', True)
            self.state = ReferentSearchState.FIND_PRONOUN_WORD
            return True

        if self.state == ReferentSearchState.FIND_PRONOUN_WORD:
            self.pronoun_word = None
            import re
            for m in re.finditer(r"[А-ЯЁа-яё]+", self.text):
                if m.start() <= self.pronoun_position < m.end():
                    self.pronoun_word = self.text[m.start():m.end()]
                    break
            self.state = ReferentSearchState.ADD_ADDRESSED_ENTITY
            return True

        if self.state == ReferentSearchState.ADD_ADDRESSED_ENTITY:
            if self.pronoun_word:
                for i in range(max(0, self.current_sentence_idx - 1), self.current_sentence_idx + 1):
                    if i < len(self.sentences):
                        sentence_to_check = self.sentences[i]
                        addressed_entity = find_addressed_entity(self.pronoun_word, sentence_to_check)
                        if addressed_entity:
                            words_in_address = addressed_entity.split()
                            main_noun = None
                            for w in words_in_address:
                                if get_pos(w) == 'NOUN':
                                    main_noun = w
                                    break
                            if main_noun:
                                parsed = morph.parse(main_noun)[0]
                                gender = parsed.tag.gender
                                number = parsed.tag.number
                            else:
                                gender = None
                                number = 'plur'
                            self.add_candidate(addressed_entity, -1, -1, 'NOUN', addressed_entity.lower(), gender, number)
                            break
            self.state = ReferentSearchState.ADD_SPEAKER_CONTEXT
            return True

        if self.state == ReferentSearchState.ADD_SPEAKER_CONTEXT:
            if self.pronoun_word:
                speaker = get_speaker_context(self.pronoun_word, self.text, self.pronoun_position)
                if speaker:
                    parsed = morph.parse(speaker)[0]
                    gender = parsed.tag.gender
                    number = parsed.tag.number
                    self.add_candidate(speaker, -1, -1, 'NOUN', speaker.lower(), gender, number)
                # Also add nouns from attribution (e.g., after quotes) as potential candidates
                # but only for third-person pronouns
                pron_parsed = morph.parse(self.pronoun_word)[0]
                if getattr(pron_parsed.tag, 'person', None) == '3per':
                    attribution_entities = get_attribution_entities(self.pronoun_word, self.text, self.pronoun_position)
                    for ent in attribution_entities:
                        parsed_e = morph.parse(ent)[0]
                        gender_e = parsed_e.tag.gender
                        number_e = parsed_e.tag.number
                        self.add_candidate(ent, -1, -1, 'NOUN', ent.lower(), gender_e, number_e)
            self.state = ReferentSearchState.DONE
            return True

        if self.state == ReferentSearchState.DONE:
            return False

        return False

    def run(self):
        while self.step():
            pass
        return self.candidates


def find_candidates(text, pronoun_position):
    dfa = ReferentSearchDFA(text, pronoun_position)
    return dfa.run()

