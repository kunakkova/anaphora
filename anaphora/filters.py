import re
from typing import Iterable, Optional, Union, List, Dict
from .morph import normalize_word
from .helpers import is_subject_simple

def _is_animate(cand, morph):
    if cand['pos'] == 'NOUN':
        parsed = morph.parse(cand['word'])[0]
        return 'anim' in parsed.tag
    return True

def filter_personal_candidates(candidates, pronoun, morph, sentence_text, is_first_word=False):
    norm_pron = pronoun.lower()
    filtered = []
    parsed_pron = morph.parse(pronoun)[0]
    if pronoun.lower() == 'её':
        pron_gender = 'femn'
    else:
        pron_gender = parsed_pron.tag.gender
    pron_number = parsed_pron.tag.number
    for cand in candidates:
        if cand.get('is_group'):
            if cand['number'] == pron_number or pron_number is None:
                filtered.append(cand)
        elif pronoun not in {'Вы', 'Вам', 'Вас', 'Вами'}:
            if (cand['gender'] == pron_gender or pron_gender is None) and (cand['number'] == pron_number or pron_number is None):
                filtered.append(cand)
        else:
            filtered.append(cand)
    if norm_pron == 'ты':
        filtered = [cand for cand in filtered if _is_animate(cand, morph)]
    if pronoun in {'Вы', 'Вас', 'Вам', 'Вами'}:
        if is_first_word:
            filtered = [cand for cand in filtered if cand['number'] in ('sing', 'plur', None)]
        else:
            filtered = [cand for cand in filtered if cand['number'] == 'sing' or cand.get('is_group')]
    if norm_pron in {'вы', 'вас', 'вам', 'вами'} and pronoun[0].islower():
        filtered = [cand for cand in filtered if cand['number'] == 'plur' or cand.get('is_group')]
    return filtered

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

def filter_possessive_candidates(candidates, pronoun, morph, sentence_text):
    norm_pron = pronoun.lower()
    filtered = []
    pronoun_pos = sentence_text.lower().find(norm_pron)
    if pronoun_pos == -1:
        simple_clause = sentence_text
    else:
        simple_clause = find_simple_clause_with_pronoun(sentence_text, pronoun)
    first_and_second_person_prons = {'я', 'мы', 'ты', 'вы', 'меня', 'нас', 'тебя', 'вас', 'мне', 'нам', 'тебе', 'вам',
                                    'мой', 'наш', 'твой', 'ваш', 'свой'}
    has_1_2_person_pron = any(
        p in sentence_text.lower().split()
        for p in first_and_second_person_prons
    )
    if norm_pron in {'свой', 'своя', 'свои', 'своими', 'своих', 'свое', 'своей', 'своим', 'своем', 'своего', 'свою', 'своему'}:
        subject_candidates = [cand for cand in candidates if is_subject_simple(cand['word'], simple_clause, morph)]
        if subject_candidates:
            return subject_candidates
    elif norm_pron in {'его', 'её', 'ее'}:
        parsed_pron = morph.parse(pronoun)[0]
        pron_gender = parsed_pron.tag.gender
        pron_number = parsed_pron.tag.number
        for cand in candidates:
            if (cand['gender'] == pron_gender or pron_gender is None) and (cand['number'] == pron_number or pron_number is None):
                filtered.append(cand)
    elif norm_pron == 'их':
        for cand in candidates:
            if cand['number'] == 'plur':
                filtered.append(cand)
    elif norm_pron in {'твой', 'твоего', 'твоему', 'твоим', 'твоем', 'твоя', 'твою', 'твоей', 'твое', 'твои', 'твоих', 'твоими',
                       'мой', 'моего', 'моему', 'моим', 'моем', 'моя', 'мою', 'моей', 'мое', 'мои', 'моих', 'моими',
                       'ваш', 'вашего', 'вашему', 'вашим', 'вашем', 'ваша', 'вашу', 'вашей', 'ваше', 'ваши', 'ваших', 'вашими'}:
        filtered = candidates.copy()
        first_person_possessives = {'мой', 'моего', 'моему', 'моим', 'моем', 'моя', 'мою', 'моей', 'мое', 'мои', 'моих', 'моими'}
        second_person_possessives = {'твой', 'твоего', 'твоему', 'твоим', 'твоем', 'твоя', 'твою', 'твоей', 'твое', 'твои', 'твоих', 'твоими',
                                    'ваш', 'вашего', 'вашему', 'вашим', 'вашем', 'ваша', 'вашу', 'вашей', 'ваше', 'ваши', 'ваших', 'вашими'}
        if norm_pron in first_person_possessives:
            pron_person = '1per'
        elif norm_pron in second_person_possessives:
            pron_person = '2per'
        else:
            pron_person = None
        if pron_person in {'1per', '2per'}:
            personal_pron_candidates = []
            for cand in candidates:
                if cand['pos'] == 'NPRO' and cand['normalized'] in first_and_second_person_prons:
                    cand_person = morph.parse(cand['word'])[0].tag.person
                    if cand_person == pron_person:
                        personal_pron_candidates.append(cand)
            if personal_pron_candidates:
                return personal_pron_candidates
    if not filtered:
        pron_candidates = [cand for cand in candidates if cand['pos'] == 'NPRO']
        if pron_candidates:
            filtered = pron_candidates
    return filtered

def filter_relative_candidates(candidates, pronoun, morph, sentence_text):
    norm_pron = pronoun.lower()
    pronoun_pos = sentence_text.lower().find(pronoun)
    comma_index = sentence_text.rfind(',', 0, pronoun_pos)
    if comma_index == -1:
        main_part = sentence_text
    else:
        main_part = sentence_text[:comma_index]
    after_pronoun_pos = pronoun_pos + len(pronoun)
    next_word = None
    match_next_word = re.search(r'\b[а-яёА-ЯЁ]+\b', sentence_text[after_pronoun_pos:])
    if match_next_word:
        next_word = match_next_word.group(0)
    def is_next_word_verb(word):
        if not word:
            return False
        parsed = morph.parse(word)[0]
        return 'VERB' in parsed.tag or 'INFN' in parsed.tag
    for cand in reversed(candidates):
        if cand.get('start', -1) > comma_index:
            continue
        pos = cand.get('pos')
        if norm_pron in {'кто', 'кого', 'кому', 'кем', 'ком'}:
            if not is_next_word_verb(next_word):
                continue
            if pos == 'NOUN':
                parsed = morph.parse(cand['word'])[0]
                if 'anim' in parsed.tag:
                    return [cand]
        elif norm_pron in {'что', 'чего', 'чем', 'чему', 'которое'}:
            if not is_next_word_verb(next_word):
                continue
            if pos == 'NOUN':
                parsed = morph.parse(cand['word'])[0]
                if 'inan' in parsed.tag:
                    return [cand]
        elif norm_pron in {'который', 'которая', 'которого', 'которую', 'которым', 'котором', 'которой', 'которому',
                          'чей', 'чья', 'чьего', 'чьей', 'чьим', 'чьему'}:
            parsed_pron = morph.parse(pronoun)[0]
            if pos == 'NOUN':
                parsed_c = morph.parse(cand['word'])[0]
                if (parsed_c.tag.number == parsed_pron.tag.number and
                    (parsed_c.tag.gender == parsed_pron.tag.gender or parsed_c.tag.gender is None)):
                    return [cand]
        elif norm_pron in {'которые', 'чьи', 'которых', 'чьих', 'которыми', 'чьими', 'которым', 'чьим'}:
            parsed_pron = morph.parse(pronoun)[0]
            pron_number = parsed_pron.tag.number
            suitable_candidates = []
            for cand in candidates:
                pos = cand.get('pos')
                is_group = cand.get('is_group', False)
                parsed_c = morph.parse(cand['word'])[0]
                if is_group:
                    if cand.get('number') == pron_number:
                        suitable_candidates.append(cand)
                else:
                    if (parsed_c.tag.gender == parsed_pron.tag.gender and
                        parsed_c.tag.number == pron_number):
                        suitable_candidates.append(cand)
            if suitable_candidates:
                return suitable_candidates
    return []

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

