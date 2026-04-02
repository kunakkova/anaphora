import re
from typing import List, Dict, Any, Optional, Tuple
from .morph import morph, normalize_word
from .resources import all_pronouns, collective_nouns, common_gender_nouns
from .tokenization import get_sentences, get_words
from .helpers import find_coord_groups


DEMONSTRATIVE_SKIP_PHRASES = {
    ('тот', 'же'), ('тот', 'самый'),
    ('та', 'же'), ('та', 'самая'),
    ('те', 'же'), ('те', 'самые'),
}

RELATIVE_AFTER_DEMONSTRATIVE = {
    'кто', 'кого', 'кому', 'кем', 'ком',
    'что', 'чего', 'чему', 'чем',
    'который', 'которая', 'которое', 'которые',
    'которого', 'которой', 'которому', 'которым', 'котором',
    'которых', 'которыми', 'которую'
}


def _collect_candidates_from_text(text: str, morph_analyzer,) -> List[Dict[str, Any]]:
    words = get_words(text)
    candidates = []
    current_pos = 0
    for word in words:
        start = text.find(word, current_pos)
        if start == -1:
            current_pos += 1
            continue
        end = start + len(word)
        current_pos = end
        parsed = morph_analyzer.parse(word)[0]
        pos = parsed.tag.POS
        normalized_word = normalize_word(word)
        gender = parsed.tag.gender
        number = parsed.tag.number
        if pos == 'NOUN' or normalized_word in all_pronouns:
            if normalized_word in {'вы', 'вас', 'вам', 'вами'}:
                candidates.append({
                    'word': word, 'start': start, 'end': end, 'pos': pos,
                    'normalized': normalized_word, 'gender': None, 'number': 'sing', 'is_group': False
                })
                candidates.append({
                    'word': word, 'start': start, 'end': end, 'pos': pos,
                    'normalized': normalized_word, 'gender': None, 'number': 'plur', 'is_group': False
                })
            elif _is_common_gender_noun(word):
                candidates.append({
                    'word': word, 'start': start, 'end': end, 'pos': pos,
                    'normalized': normalized_word, 'gender': 'masc', 'number': number, 'is_group': False
                })
                candidates.append({
                    'word': word, 'start': start, 'end': end, 'pos': pos,
                    'normalized': normalized_word, 'gender': 'femn', 'number': number, 'is_group': False
                })
            elif _is_collective_noun(word):
                candidates.append({
                    'word': word, 'start': start, 'end': end, 'pos': pos,
                    'normalized': normalized_word, 'gender': gender, 'number': 'sing', 'is_group': False
                })
                candidates.append({
                    'word': word, 'start': start, 'end': end, 'pos': pos,
                    'normalized': normalized_word, 'gender': gender, 'number': 'plur', 'is_group': False
                })
            else:
                candidates.append({
                    'word': word, 'start': start, 'end': end, 'pos': pos,
                    'normalized': normalized_word, 'gender': gender, 'number': number, 'is_group': False
                })
    return candidates


def _is_collective_noun(word: str) -> bool:
    return normalize_word(word) in collective_nouns


def _is_common_gender_noun(word: str) -> bool:
    return normalize_word(word) in common_gender_nouns


def _get_next_word_after_pronoun(text: str, pron_start: int, pron_end: int) -> Optional[str]:
    after = text[pron_end:]
    m = re.search(r'[\s,]+([а-яёА-ЯЁ]+)', after)
    if m:
        return normalize_word(m.group(1))
    return None


def _should_skip_demonstrative(pronoun: str, text: str, pron_start: int, pron_end: int) -> bool:
    norm_pron = normalize_word(pronoun)
    next_word = _get_next_word_after_pronoun(text, pron_start, pron_end)
    if next_word is None:
        return False
    if (norm_pron, next_word) in DEMONSTRATIVE_SKIP_PHRASES:
        return True
    if next_word in RELATIVE_AFTER_DEMONSTRATIVE:
        return True
    return False


def find_demonstrative_candidates(text: str, pronoun_position: int, pronoun: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    sentences = get_sentences(text)
    current_pos = 0
    current_sentence_idx = -1
    current_sentence_start = 0
    current_sentence_text = ''
    for i, sent in enumerate(sentences):
        sent_len = len(sent)
        if current_pos <= pronoun_position < current_pos + sent_len:
            current_sentence_idx = i
            current_sentence_start = current_pos
            current_sentence_text = sent
            break
        current_pos += sent_len

    if current_sentence_idx < 0:
        return [], []

    rel_start = pronoun_position - current_sentence_start
    same_sentence_before = current_sentence_text[:rel_start]
    same_candidates = _collect_candidates_from_text(same_sentence_before, morph)
    coord_groups = find_coord_groups(same_sentence_before)
    for group in coord_groups:
        if len(group) > 1:
            group_text = ' и '.join(group)
            same_candidates.append({
                'word': group_text, 'start': -1, 'end': -1, 'pos': 'NOUN',
                'normalized': group_text.lower(), 'gender': None, 'number': 'plur', 'is_group': True
            })

    prev_sentence_candidates = []
    if current_sentence_idx > 0:
        prev_sentence = sentences[current_sentence_idx - 1]
        prev_sentence_candidates = _collect_candidates_from_text(prev_sentence, morph)
        coord_prev = find_coord_groups(prev_sentence)
        for group in coord_prev:
            if len(group) > 1:
                group_text = ' и '.join(group)
                prev_sentence_candidates.append({
                    'word': group_text, 'start': -1, 'end': -1, 'pos': 'NOUN',
                    'normalized': group_text.lower(), 'gender': None, 'number': 'plur', 'is_group': True
                })

    return same_candidates, prev_sentence_candidates


def filter_demonstrative_candidates(same_sentence_candidates: List[Dict[str, Any]], prev_sentence_candidates: List[Dict[str, Any]], pronoun: str, morph_analyzer, text: str, pron_start: int, pron_end: int) -> Optional[Dict[str, Any]]:
    if _should_skip_demonstrative(pronoun, text, pron_start, pron_end):
        return None

    parsed_pron = morph_analyzer.parse(pronoun)[0]
    pron_gender = parsed_pron.tag.gender
    pron_number = parsed_pron.tag.number

    def matches_gender_number(cand: Dict) -> bool:
        if cand.get('is_group'):
            return cand.get('number') == pron_number or pron_number is None
        return (
            (cand.get('gender') == pron_gender or pron_gender is None)
            and (cand.get('number') == pron_number or pron_number is None)
        )

    suitable_same = [c for c in same_sentence_candidates if matches_gender_number(c)]
    if suitable_same:
        return suitable_same[-1]

    suitable_prev = [c for c in prev_sentence_candidates if matches_gender_number(c)]
    if suitable_prev:
        return suitable_prev[-1]

    return None
