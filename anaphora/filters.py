import re
from typing import Iterable, Optional, Union, List, Dict
from .morph import normalize_word
from .helpers import is_subject_simple

class PersonalFilterState:
    START = 'START'
    PARSE_PRONOUN = 'PARSE_PRONOUN'
    MATCH_GENDER_NUMBER = 'MATCH_GENDER_NUMBER'
    APPLY_SPECIAL_RULES = 'APPLY_SPECIAL_RULES'
    DONE = 'DONE'


class PersonalFilterDFA:
    def __init__(self, candidates, pronoun, morph, sentence_text, is_first_word=False):
        self.candidates = list(candidates or [])
        self.pronoun = pronoun
        self.morph = morph
        self.sentence_text = sentence_text
        self.is_first_word = is_first_word
        self.state = PersonalFilterState.START
        self.filtered: List[Dict] = []
        self.norm_pron = None
        self.pron_gender = None
        self.pron_number = None

    def step(self) -> bool:
        if self.state == PersonalFilterState.START:
            self.norm_pron = (self.pronoun or '').lower()
            self.state = PersonalFilterState.PARSE_PRONOUN
            return True

        if self.state == PersonalFilterState.PARSE_PRONOUN:
            parsed_pron = self.morph.parse(self.pronoun)[0]
            if self.pronoun.lower() == 'её':
                self.pron_gender = 'femn'
            else:
                self.pron_gender = parsed_pron.tag.gender
            self.pron_number = parsed_pron.tag.number
            self.state = PersonalFilterState.MATCH_GENDER_NUMBER
            return True

        if self.state == PersonalFilterState.MATCH_GENDER_NUMBER:
            filtered = []
            for cand in self.candidates:
                if cand.get('is_group'):
                    if cand['number'] == self.pron_number or self.pron_number is None:
                        filtered.append(cand)
                elif self.pronoun not in {'Вы', 'Вам', 'Вас', 'Вами'}:
                    if ((cand['gender'] == self.pron_gender or self.pron_gender is None)
                        and (cand['number'] == self.pron_number or self.pron_number is None)):
                        filtered.append(cand)
                else:
                    filtered.append(cand)
            self.filtered = filtered
            self.state = PersonalFilterState.APPLY_SPECIAL_RULES
            return True

        if self.state == PersonalFilterState.APPLY_SPECIAL_RULES:
            filtered = self.filtered
            if self.norm_pron == 'ты':
                filtered = [cand for cand in filtered if _is_animate(cand, self.morph)]
            if self.pronoun in {'Вы', 'Вас', 'Вам', 'Вами'}:
                if self.is_first_word:
                    filtered = [cand for cand in filtered if cand['number'] in ('sing', 'plur', None)]
                else:
                    filtered = [cand for cand in filtered if cand['number'] == 'sing' or cand.get('is_group')]
            if self.norm_pron in {'вы', 'вас', 'вам', 'вами'} and self.pronoun and self.pronoun[0].islower():
                filtered = [cand for cand in filtered if cand['number'] == 'plur' or cand.get('is_group')]
            self.filtered = filtered
            self.state = PersonalFilterState.DONE
            return True

        if self.state == PersonalFilterState.DONE:
            return False

        return False

    def run(self):
        while self.step():
            pass
        return self.filtered

def _is_animate(cand, morph):
    if cand['pos'] == 'NOUN':
        parsed = morph.parse(cand['word'])[0]
        return 'anim' in parsed.tag
    return True

def filter_personal_candidates(candidates, pronoun, morph, sentence_text, is_first_word=False):
    dfa = PersonalFilterDFA(candidates, pronoun, morph, sentence_text, is_first_word)
    return dfa.run()

def split_to_simple_clauses(complex_sentence):
    delimiters = r',|;|:|—|(?<= )и(?= )|(?<= )а(?= )|(?<= )но(?= )'
    clauses = re.split(delimiters, complex_sentence)
    clauses = [cl.strip() for cl in clauses if cl.strip()]
    return clauses

def find_simple_clause_with_pronoun(text, pronoun):
    clauses = split_to_simple_clauses(text)
    norm_pron = pronoun.lower()
    for clause in clauses:
        if re.search(r'\b' + re.escape(norm_pron) + r'\b', clause.lower()):
            return clause
    return text

class PossessiveFilterState:
    START = 'START'
    PREPARE = 'PREPARE'
    HANDLE_SVOY = 'HANDLE_SVOY'
    HANDLE_EGO_EE = 'HANDLE_EGO_EE'
    HANDLE_IX = 'HANDLE_IX'
    HANDLE_1_2_POSSESSIVES = 'HANDLE_1_2_POSSESSIVES'
    FALLBACK_PRONOUNS = 'FALLBACK_PRONOUNS'
    DONE = 'DONE'


class PossessiveFilterDFA:
    def __init__(self, candidates, pronoun, morph, sentence_text):
        self.candidates = list(candidates or [])
        self.pronoun = pronoun
        self.morph = morph
        self.sentence_text = sentence_text
        self.state = PossessiveFilterState.START
        self.norm_pron = None
        self.filtered: List[Dict] = []
        self.simple_clause = sentence_text

    def step(self) -> bool:
        if self.state == PossessiveFilterState.START:
            self.norm_pron = (self.pronoun or '').lower()
            self.state = PossessiveFilterState.PREPARE
            return True

        if self.state == PossessiveFilterState.PREPARE:
            pronoun_pos = self.sentence_text.lower().find(self.norm_pron)
            if pronoun_pos == -1:
                self.simple_clause = self.sentence_text
            else:
                self.simple_clause = find_simple_clause_with_pronoun(self.sentence_text, self.pronoun)
            self.state = PossessiveFilterState.HANDLE_SVOY
            return True

        if self.state == PossessiveFilterState.HANDLE_SVOY:
            if self.norm_pron in {'свой', 'своя', 'свои', 'своими', 'своих', 'свое', 'своей', 'своим', 'своем', 'своего', 'свою', 'своему'}:
                subject_candidates = [cand for cand in self.candidates if is_subject_simple(cand['word'], self.simple_clause, self.morph)]
                if subject_candidates:
                    self.filtered = subject_candidates
                    self.state = PossessiveFilterState.DONE
                    return True
            self.state = PossessiveFilterState.HANDLE_EGO_EE
            return True

        if self.state == PossessiveFilterState.HANDLE_EGO_EE:
            if self.norm_pron in {'его', 'её', 'ее'}:
                parsed_pron = self.morph.parse(self.pronoun)[0]
                pron_gender = parsed_pron.tag.gender
                pron_number = parsed_pron.tag.number
                self.filtered = [cand for cand in self.candidates
                                 if (cand['gender'] == pron_gender or pron_gender is None)
                                 and (cand['number'] == pron_number or pron_number is None)]
                self.state = PossessiveFilterState.DONE
                return True
            self.state = PossessiveFilterState.HANDLE_IX
            return True

        if self.state == PossessiveFilterState.HANDLE_IX:
            if self.norm_pron == 'их':
                self.filtered = [cand for cand in self.candidates if cand['number'] == 'plur']
                self.state = PossessiveFilterState.DONE
                return True
            self.state = PossessiveFilterState.HANDLE_1_2_POSSESSIVES
            return True

        if self.state == PossessiveFilterState.HANDLE_1_2_POSSESSIVES:
            if self.norm_pron in {'твой', 'твоего', 'твоему', 'твоим', 'твоем', 'твоя', 'твою', 'твоей', 'твое', 'твои', 'твоих', 'твоими',
                                   'мой', 'моего', 'моему', 'моим', 'моем', 'моя', 'мою', 'моей', 'мое', 'мои', 'моих', 'моими',
                                   'ваш', 'вашего', 'вашему', 'вашим', 'вашем', 'ваша', 'вашу', 'вашей', 'ваше', 'ваши', 'ваших', 'вашими'}:
                filtered = self.candidates.copy()
                first_and_second_person_prons = {'я', 'мы', 'ты', 'вы', 'меня', 'нас', 'тебя', 'вас', 'мне', 'нам', 'тебе', 'вам',
                                                'мой', 'наш', 'твой', 'ваш', 'свой'}
                first_person_possessives = {'мой', 'моего', 'моему', 'моим', 'моем', 'моя', 'мою', 'моей', 'мое', 'мои', 'моих', 'моими'}
                second_person_possessives = {'твой', 'твоего', 'твоему', 'твоим', 'твоем', 'твоя', 'твою', 'твоей', 'твое', 'твои', 'твоих', 'твоими',
                                            'ваш', 'вашего', 'вашему', 'вашим', 'вашем', 'ваша', 'вашу', 'вашей', 'ваше', 'ваши', 'ваших', 'вашими'}
                if self.norm_pron in first_person_possessives:
                    pron_person = '1per'
                elif self.norm_pron in second_person_possessives:
                    pron_person = '2per'
                else:
                    pron_person = None
                if pron_person in {'1per', '2per'}:
                    personal_pron_candidates = []
                    for cand in self.candidates:
                        if cand['pos'] == 'NPRO' and cand['normalized'] in first_and_second_person_prons:
                            cand_person = self.morph.parse(cand['word'])[0].tag.person
                            if cand_person == pron_person:
                                personal_pron_candidates.append(cand)
                    if personal_pron_candidates:
                        self.filtered = personal_pron_candidates
                        self.state = PossessiveFilterState.DONE
                        return True
                self.filtered = filtered
            self.state = PossessiveFilterState.FALLBACK_PRONOUNS
            return True

        if self.state == PossessiveFilterState.FALLBACK_PRONOUNS:
            if not self.filtered:
                pron_candidates = [cand for cand in self.candidates if cand['pos'] == 'NPRO']
                if pron_candidates:
                    self.filtered = pron_candidates
            self.state = PossessiveFilterState.DONE
            return True

        if self.state == PossessiveFilterState.DONE:
            return False

        return False

    def run(self):
        while self.step():
            pass
        return self.filtered


def filter_possessive_candidates(candidates, pronoun, morph, sentence_text):
    dfa = PossessiveFilterDFA(candidates, pronoun, morph, sentence_text)
    return dfa.run()

class RelativeFilterState:
    START = 'START'
    PREPARE = 'PREPARE'
    SCAN_CANDIDATES = 'SCAN_CANDIDATES'
    DONE = 'DONE'


class RelativeFilterDFA:
    def __init__(self, candidates, pronoun, morph, sentence_text):
        self.candidates = list(candidates or [])
        self.pronoun = pronoun
        self.morph = morph
        self.sentence_text = sentence_text
        self.state = RelativeFilterState.START
        self.norm_pron = None
        self.comma_index = -1
        self.next_word = None
        self.filtered: List[Dict] = []

    def _is_next_word_verb(self, word):
        if not word:
            return False
        parsed = self.morph.parse(word)[0]
        return 'VERB' in parsed.tag or 'INFN' in parsed.tag

    def step(self) -> bool:
        if self.state == RelativeFilterState.START:
            self.norm_pron = (self.pronoun or '').lower()
            self.state = RelativeFilterState.PREPARE
            return True

        if self.state == RelativeFilterState.PREPARE:
            pronoun_pos = self.sentence_text.lower().find(self.pronoun)
            self.comma_index = self.sentence_text.rfind(',', 0, pronoun_pos)
            after_pronoun_pos = pronoun_pos + len(self.pronoun)
            match_next_word = re.search(r'\b[а-яёА-ЯЁ]+\b', self.sentence_text[after_pronoun_pos:])
            if match_next_word:
                self.next_word = match_next_word.group(0)
            self.state = RelativeFilterState.SCAN_CANDIDATES
            return True

        if self.state == RelativeFilterState.SCAN_CANDIDATES:
            for cand in reversed(self.candidates):
                if cand.get('start', -1) > self.comma_index:
                    continue
                pos = cand.get('pos')
                if self.norm_pron in {'кто', 'кого', 'кому', 'кем', 'ком'}:
                    if not self._is_next_word_verb(self.next_word):
                        continue
                    if pos == 'NOUN':
                        parsed = self.morph.parse(cand['word'])[0]
                        if 'anim' in parsed.tag:
                            self.filtered = [cand]
                            break
                elif self.norm_pron in {'что', 'чего', 'чем', 'чему', 'которое'}:
                    if not self._is_next_word_verb(self.next_word):
                        continue
                    if pos == 'NOUN':
                        parsed = self.morph.parse(cand['word'])[0]
                        if 'inan' in parsed.tag:
                            self.filtered = [cand]
                            break
                elif self.norm_pron in {'который', 'которая', 'которого', 'которую', 'которым', 'котором', 'которой', 'которому',
                                        'чей', 'чья', 'чьего', 'чьей', 'чьим', 'чьему'}:
                    parsed_pron = self.morph.parse(self.pronoun)[0]
                    if pos == 'NOUN':
                        parsed_c = self.morph.parse(cand['word'])[0]
                        if (parsed_c.tag.number == parsed_pron.tag.number and
                            (parsed_c.tag.gender == parsed_pron.tag.gender or parsed_c.tag.gender is None)):
                            self.filtered = [cand]
                            break
                elif self.norm_pron in {'которые', 'чьи', 'которых', 'чьих', 'которыми', 'чьими', 'которым', 'чьим'}:
                    parsed_pron = self.morph.parse(self.pronoun)[0]
                    pron_number = parsed_pron.tag.number
                    suitable_candidates = []
                    for c in self.candidates:
                        is_group = c.get('is_group', False)
                        parsed_c = self.morph.parse(c['word'])[0]
                        if is_group:
                            if c.get('number') == pron_number:
                                suitable_candidates.append(c)
                        else:
                            if (parsed_c.tag.gender == parsed_pron.tag.gender and
                                parsed_c.tag.number == pron_number):
                                suitable_candidates.append(c)
                    if suitable_candidates:
                        self.filtered = suitable_candidates
                        break
            self.state = RelativeFilterState.DONE
            return True

        if self.state == RelativeFilterState.DONE:
            return False

        return False

    def run(self):
        while self.step():
            pass
        return self.filtered


def filter_relative_candidates(candidates, pronoun, morph, sentence_text):
    dfa = RelativeFilterDFA(candidates, pronoun, morph, sentence_text)
    return dfa.run()

def contains_idiom_with_pronoun(pronoun, text, idioms):
    pronoun_norm = normalize_word(pronoun)
    from nltk.tokenize import sent_tokenize
    sentences = sent_tokenize(text, language='russian')
    for sentence in sentences:
        if pronoun_norm in normalize_word(sentence):
            sentence_no_commas = re.sub(r',', '', sentence)
            sentence_norm = normalize_word(sentence_no_commas)
            for idiom in idioms:
                if idiom in sentence_norm and pronoun_norm in idiom:
                    return True
    return False

