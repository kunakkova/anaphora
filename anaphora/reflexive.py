from typing import Iterable, Optional, Union, List, Dict
import re
from .helpers import is_subject_simple

class ReflexiveFilterState:
    START = 'START'
    PRECHECK_IDIOMS = 'PRECHECK_IDIOMS'
    PREPARE = 'PREPARE'
    SPLIT_LEFT_RIGHT = 'SPLIT_LEFT_RIGHT'
    SELECT_LEFT = 'SELECT_LEFT'
    FALLBACK_RIGHT = 'FALLBACK_RIGHT'
    DONE = 'DONE'


class ReflexiveFilterDFA:
    def __init__(self, candidates: Iterable[Dict], pronoun: str, morph, sentence_text: str, idioms: Optional[Iterable[str]] = None):
        self.candidates = list(candidates or [])
        self.pronoun = pronoun
        self.morph = morph
        self.sentence_text = sentence_text or ""
        self.idioms = list(idioms or [])
        self.state = ReflexiveFilterState.START
        self.sent_low = self.sentence_text.lower()
        self.pron_low = (self.pronoun or '').lower().strip()
        self.pron_start = -1
        self.left_candidates: List[Dict] = []
        self.right_candidates: List[Dict] = []
        self.result: Optional[Union[Dict, List[Dict]]] = None

    def _is_plural_token(self, candidate: Dict) -> bool:
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

    def _collect_subject_group_by_text(self, subject: Dict) -> List[Dict]:
        if subject is None:
            return []
        group = [subject]
        subj_start = subject.get("start", 0)
        subj_end = subject.get("end", subj_start)
        for c in self.candidates:
            if c is subject:
                continue
            cstart = c.get("start", 0)
            cend = c.get("end", cstart)
            left, right = sorted((subj_end, cstart))
            between = self.sentence_text[left:right].lower()
            if re.search(r'\bи\b', between) or re.search(r',\s*и\b', between):
                pos = (c.get("pos") or "").upper()
                if pos in {"NOUN", "PROPN", "PRON"}:
                    group.append(c)
        group = sorted({id(x): x for x in group}.values(),
                       key=lambda x: x.get("start", 0))
        return group

    def _sort_by_closest_left(self, candidates_list):
        return sorted(candidates_list,
                      key=lambda c: self.pron_start - c.get("end", c.get("start", 0)),
                      reverse=True)

    def _sort_by_closest_right(self, candidates_list):
        return sorted(candidates_list,
                      key=lambda c: c.get("start", 0) - self.pron_start)

    def step(self) -> bool:
        if self.state == ReflexiveFilterState.START:
            self.state = ReflexiveFilterState.PRECHECK_IDIOMS
            return True

        if self.state == ReflexiveFilterState.PRECHECK_IDIOMS:
            for idi in self.idioms:
                if idi and idi.lower() in self.sent_low:
                    self.result = None
                    self.state = ReflexiveFilterState.DONE
                    return True
            self.state = ReflexiveFilterState.PREPARE
            return True

        if self.state == ReflexiveFilterState.PREPARE:
            self.pron_start = self.sent_low.find(self.pron_low)
            if self.pron_start == -1:
                self.result = None
                self.state = ReflexiveFilterState.DONE
                return True
            self.left_candidates = [c for c in self.candidates if c.get("start", float("inf")) < self.pron_start]
            self.right_candidates = [c for c in self.candidates if c.get("start", 0) > self.pron_start]
            self.state = ReflexiveFilterState.SPLIT_LEFT_RIGHT
            return True

        if self.state == ReflexiveFilterState.SPLIT_LEFT_RIGHT:
            plural_subject_groups = []
            single_subjects = []
            plural_groups = []
            single_words = []
            for c in self.left_candidates:
                word = c.get("word", "")
                is_subject = word and is_subject_simple(word, self.sentence_text, self.morph)
                is_plural = self._is_plural_token(c)
                if is_plural and is_subject:
                    plural_subject_groups.append(c)
                elif is_subject:
                    single_subjects.append(c)
                elif is_plural:
                    plural_groups.append(c)
                else:
                    single_words.append(c)
            if plural_subject_groups:
                subject = self._sort_by_closest_left(plural_subject_groups)[0]
                group = self._collect_subject_group_by_text(subject)
                self.result = group if group else subject
                self.state = ReflexiveFilterState.DONE
                return True
            if single_subjects:
                subject = self._sort_by_closest_left(single_subjects)[0]
                self.result = subject
                self.state = ReflexiveFilterState.DONE
                return True
            if plural_groups:
                subject = self._sort_by_closest_left(plural_groups)[0]
                group = self._collect_subject_group_by_text(subject)
                self.result = group if group else subject
                self.state = ReflexiveFilterState.DONE
                return True
            if single_words:
                nouns_pronouns = [c for c in single_words
                                  if c.get("pos", "").upper() in {"NOUN", "PROPN", "PRON"}]
                if nouns_pronouns:
                    self.result = self._sort_by_closest_left(nouns_pronouns)[0]
                else:
                    self.result = self._sort_by_closest_left(single_words)[0]
                self.state = ReflexiveFilterState.DONE
                return True
            self.state = ReflexiveFilterState.FALLBACK_RIGHT
            return True

        if self.state == ReflexiveFilterState.FALLBACK_RIGHT:
            if self.right_candidates:
                plural_subject_groups_right = []
                single_subjects_right = []
                plural_groups_right = []
                single_words_right = []
                for c in self.right_candidates:
                    word = c.get("word", "")
                    is_subject = word and is_subject_simple(word, self.sentence_text, self.morph)
                    is_plural = self._is_plural_token(c)
                    if is_plural and is_subject:
                        plural_subject_groups_right.append(c)
                    elif is_subject:
                        single_subjects_right.append(c)
                    elif is_plural:
                        plural_groups_right.append(c)
                    else:
                        single_words_right.append(c)
                if plural_subject_groups_right:
                    subject = self._sort_by_closest_right(plural_subject_groups_right)[0]
                    group = self._collect_subject_group_by_text(subject)
                    self.result = group if group else subject
                elif single_subjects_right:
                    self.result = self._sort_by_closest_right(single_subjects_right)[0]
                elif plural_groups_right:
                    subject = self._sort_by_closest_right(plural_groups_right)[0]
                    group = self._collect_subject_group_by_text(subject)
                    self.result = group if group else subject
                elif single_words_right:
                    nouns_pronouns = [c for c in single_words_right
                                      if c.get("pos", "").upper() in {"NOUN", "PROPN", "PRON"}]
                    if nouns_pronouns:
                        self.result = self._sort_by_closest_right(nouns_pronouns)[0]
                    else:
                        self.result = self._sort_by_closest_right(single_words_right)[0]
            self.state = ReflexiveFilterState.DONE
            return True

        if self.state == ReflexiveFilterState.DONE:
            return False

        return False

    def run(self) -> Optional[Union[Dict, List[Dict]]]:
        while self.step():
            pass
        return self.result

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
    dfa = ReflexiveFilterDFA(candidates, pronoun, morph, sentence_text, idioms)
    return dfa.run()

