from typing import Dict, Any, Optional, List, Tuple
from .tokenization import find_pronoun_indices
from .pronoun_types import determine_pronoun_type
from .candidates import find_candidates
from .filters import (
    filter_personal_candidates,
    filter_possessive_candidates,
    filter_relative_candidates,
)
from .reflexive import filter_reflexive_candidates
from .resources import idioms
from .ranking import rank_candidates
from .morph import normalize_word, morph


class DFAState:
    START = "START"
    PRONOUN_DETECTED = "PRONOUN_DETECTED"
    TYPE_DETERMINED = "TYPE_DETERMINED"
    CANDIDATES_FOUND = "CANDIDATES_FOUND"
    FILTERED = "FILTERED"
    RANKED = "RANKED"
    ANNOTATED = "ANNOTATED"
    END = "END"


class AnaphoraDFA:
    def __init__(self, text: str):
        self.original_text: str = text
        self.result_text: str = text
        self.offset: int = 0
        self.pronoun_spans: List[Tuple[int, int]] = find_pronoun_indices(text)
        self.current_index: int = 0
        self.current_pronoun_span: Optional[Tuple[int, int]] = None
        self.current_pronoun: Optional[str] = None
        self.current_type: Optional[str] = None
        self.candidates: Optional[List[Dict[str, Any]]] = None
        self.filtered: Optional[Any] = None
        self.reference_word: Optional[str] = None
        self.state: str = DFAState.START

    def has_more(self) -> bool:
        return self.current_index < len(self.pronoun_spans)

    def step(self) -> bool:
        if self.state == DFAState.START:
            if not self.has_more():
                self.state = DFAState.END
                return False
            self.current_pronoun_span = self.pronoun_spans[self.current_index]
            s, e = self.current_pronoun_span
            self.current_pronoun = self.original_text[s:e]
            self.state = DFAState.PRONOUN_DETECTED
            return True

        if self.state == DFAState.PRONOUN_DETECTED:
            s, e = self.current_pronoun_span
            next_word = None
            if e < len(self.original_text):
                import re
                m = re.search(r"\b[а-яёА-ЯЁ]+\b", self.original_text[e:])
                if m:
                    next_word = m.group(0)
            self.current_type = determine_pronoun_type(self.current_pronoun, next_word)
            self.state = DFAState.TYPE_DETERMINED
            return True

        if self.state == DFAState.TYPE_DETERMINED:
            s, _ = self.current_pronoun_span
            self.candidates = find_candidates(self.original_text, s)
            self.state = DFAState.CANDIDATES_FOUND
            return True

        if self.state == DFAState.CANDIDATES_FOUND:
            text = self.original_text
            pron = self.current_pronoun
            pron_norm = normalize_word(pron)
            if self.current_type == 'личное':
                self.filtered = filter_personal_candidates(self.candidates, pron, morph, text)
            elif self.current_type == 'притяжательное':
                self.filtered = filter_possessive_candidates(self.candidates, pron_norm, morph, text)
            elif self.current_type == 'возвратное':
                self.filtered = filter_reflexive_candidates(self.candidates, pron, morph, text, idioms)
            elif self.current_type == 'относительное':
                self.filtered = filter_relative_candidates(self.candidates, pron, morph, text)
            else:
                self.filtered = self.candidates
            self.state = DFAState.FILTERED
            return True

        if self.state == DFAState.FILTERED:
            s, _ = self.current_pronoun_span
            filtered = self.filtered
            if isinstance(filtered, list):
                if len(filtered) > 1:
                    ranked = rank_candidates(filtered, s, self.original_text, morph)
                    self.reference_word = ranked[0]['word'] if ranked else 'None'
                elif len(filtered) == 1:
                    self.reference_word = filtered[0]['word']
                else:
                    self.reference_word = 'None'
            elif filtered is None:
                self.reference_word = 'None'
            else:
                self.reference_word = filtered.get('word', 'None')
            self.state = DFAState.RANKED
            return True

        if self.state == DFAState.RANKED:
            def recursive_resolve_reference(reference_word: str, text: str, depth: int = 0, max_depth: int = 5) -> str:
                if depth > max_depth or reference_word == 'None':
                    return reference_word
                pronoun_pos = None
                for start, end in find_pronoun_indices(text):
                    if text[start:end] == reference_word:
                        pronoun_pos = start
                        break
                if pronoun_pos is None:
                    return reference_word
                # determine type for the reference pronoun
                next_word = None
                if end < len(text):
                    import re
                    m = re.search(r"\b[а-яёА-ЯЁ]+\b", text[end:])
                    if m:
                        next_word = m.group(0)
                ptype = determine_pronoun_type(reference_word, next_word)
                cands = find_candidates(text, pronoun_pos)
                if ptype == 'личное':
                    filt = filter_personal_candidates(cands, reference_word, morph, text)
                elif ptype == 'притяжательное':
                    filt = filter_possessive_candidates(cands, normalize_word(reference_word), morph, text)
                elif ptype == 'возвратное':
                    filt = filter_reflexive_candidates(cands, reference_word, morph, text, idioms)
                elif ptype == 'относительное':
                    filt = filter_relative_candidates(cands, reference_word, morph, text)
                else:
                    filt = cands
                if isinstance(filt, list):
                    preferred = [c for c in filt if c.get('pos') != 'NPRO']
                    pool = preferred if preferred else filt
                    if len(pool) > 1:
                        ranked2 = rank_candidates(pool, pronoun_pos, text, morph)
                        new_ref = ranked2[0]['word'] if ranked2 else 'None'
                    elif len(pool) == 1:
                        new_ref = pool[0]['word']
                    else:
                        new_ref = 'None'
                elif filt is None:
                    new_ref = 'None'
                else:
                    new_ref = filt.get('word', 'None')
                if new_ref == reference_word or new_ref == 'None':
                    return new_ref
                return recursive_resolve_reference(new_ref, text, depth + 1, max_depth)

            self.reference_word = recursive_resolve_reference(self.reference_word, self.original_text)
            _, e = self.current_pronoun_span
            annotation = f" [{self.reference_word}]"
            insert_pos = e + self.offset
            self.result_text = self.result_text[:insert_pos] + annotation + self.result_text[insert_pos:]
            self.offset += len(annotation)
            self.state = DFAState.ANNOTATED
            return True

        if self.state == DFAState.ANNOTATED:
            self.current_index += 1
            self.current_pronoun_span = None
            self.current_pronoun = None
            self.current_type = None
            self.candidates = None
            self.filtered = None
            self.reference_word = None
            self.state = DFAState.START
            return True

        if self.state == DFAState.END:
            return False

        return False

    def run(self) -> str:
        while self.step():
            pass
        return self.result_text


