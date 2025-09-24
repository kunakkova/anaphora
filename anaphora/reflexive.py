from typing import Iterable, Optional, Union, List, Dict
import re
from .helpers import is_subject_simple

def _is_plural_token(candidate: Dict) -> bool:
    if not candidate:
        return False
    num = candidate.get('number')
    if num:
        num_s = str(num).lower()
        if any(x in num_s for x in ("plur", "pl", "plural", "мн")):
            return True
    if candidate.get("is_group"):
        return True
    if candidate.get("word", "").lower() in {"они", "мы", "вы"}:
        return True
    return False

def _collect_subject_group_by_text(subject: Dict,
                                   candidates: List[Dict],
                                   sentence_text: str) -> List[Dict]:
    if subject is None:
        return []
    group = [subject]
    subj_start = subject.get("start", 0)
    subj_end = subject.get("end", subj_start)
    for c in candidates:
        if c is subject:
            continue
        cstart = c.get("start", 0)
        cend = c.get("end", cstart)
        left, right = sorted((subj_end, cstart))
        between = sentence_text[left:right].lower()
        if re.search(r'\bи\b', between) or re.search(r',\s*и\b', between):
            pos = (c.get("pos") or "").upper()
            if pos in {"NOUN", "PROPN", "PRON"}:
                group.append(c)
    group = sorted({id(x): x for x in group}.values(),
                   key=lambda x: x.get("start", 0))
    return group

def filter_reflexive_candidates(candidates: Iterable[Dict],
                                pronoun: str,
                                morph,
                                sentence_text: str,
                                idioms: Optional[Iterable[str]] = None
                                ) -> Optional[Union[Dict, List[Dict]]]:
    idioms = list(idioms or [])
    sent_low = (sentence_text or "").lower()
    pron_low = (pronoun or "").lower().strip()
    for idi in idioms:
        if idi and idi.lower() in sent_low:
            return None
    candidates = [
        c for c in (candidates or [])
        if c.get("word", "").lower() not in {"себя", "собой", "самого себя"}
    ]
    pron_pos = sent_low.find(pron_low)
    if pron_pos == -1:
        return None
    pron_start = pron_pos
    left_candidates = [c for c in candidates if c.get("start", float("inf")) < pron_start]
    plural_subject_groups = []
    single_subjects = []
    plural_groups = []
    single_words = []
    for c in left_candidates:
        word = c.get("word", "")
        is_subject = word and is_subject_simple(word, sentence_text, morph)
        is_plural = _is_plural_token(c)
        if is_plural and is_subject:
            plural_subject_groups.append(c)
        elif is_subject:
            single_subjects.append(c)
        elif is_plural:
            plural_groups.append(c)
        else:
            single_words.append(c)
    def sort_by_closest(candidates_list):
        return sorted(candidates_list,
                     key=lambda c: pron_start - c.get("end", c.get("start", 0)),
                     reverse=True)
    if plural_subject_groups:
        subject = sort_by_closest(plural_subject_groups)[0]
        group = _collect_subject_group_by_text(subject, candidates, sentence_text)
        return group if group else subject
    if single_subjects:
        subject = sort_by_closest(single_subjects)[0]
        return subject
    if plural_groups:
        subject = sort_by_closest(plural_groups)[0]
        group = _collect_subject_group_by_text(subject, candidates, sentence_text)
        return group if group else subject
    if single_words:
        nouns_pronouns = [c for c in single_words
                         if c.get("pos", "").upper() in {"NOUN", "PROPN", "PRON"}]
        if nouns_pronouns:
            return sort_by_closest(nouns_pronouns)[0]
        return sort_by_closest(single_words)[0]
    right_candidates = [c for c in candidates if c.get("start", 0) > pron_start]
    if right_candidates:
        plural_subject_groups_right = []
        single_subjects_right = []
        plural_groups_right = []
        single_words_right = []
        for c in right_candidates:
            word = c.get("word", "")
            is_subject = word and is_subject_simple(word, sentence_text, morph)
            is_plural = _is_plural_token(c)
            if is_plural and is_subject:
                plural_subject_groups_right.append(c)
            elif is_subject:
                single_subjects_right.append(c)
            elif is_plural:
                plural_groups_right.append(c)
            else:
                single_words_right.append(c)
        def sort_right_by_closest(candidates_list):
            return sorted(candidates_list,
                         key=lambda c: c.get("start", 0) - pron_start)
        if plural_subject_groups_right:
            subject = sort_right_by_closest(plural_subject_groups_right)[0]
            group = _collect_subject_group_by_text(subject, candidates, sentence_text)
            return group if group else subject
        if single_subjects_right:
            return sort_right_by_closest(single_subjects_right)[0]
        if plural_groups_right:
            subject = sort_right_by_closest(plural_groups_right)[0]
            group = _collect_subject_group_by_text(subject, candidates, sentence_text)
            return group if group else subject
        if single_words_right:
            nouns_pronouns = [c for c in single_words_right
                             if c.get("pos", "").upper() in {"NOUN", "PROPN", "PRON"}]
            if nouns_pronouns:
                return sort_right_by_closest(nouns_pronouns)[0]
            return sort_right_by_closest(single_words_right)[0]
    return None

