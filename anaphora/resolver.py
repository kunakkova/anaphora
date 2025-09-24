import re
import nltk
from .morph import morph, normalize_word
from .tokenization import find_pronoun_indices
from .pronoun_types import determine_pronoun_type
from .candidates import find_candidates
from .filters import filter_personal_candidates, filter_possessive_candidates, filter_relative_candidates
from .reflexive import filter_reflexive_candidates
from .resources import idioms
from .ranking import rank_candidates

nltk.download('punkt', quiet=True)
nltk.download('punkt_tab', quiet=True)

def resolve_pronouns(text):
    pronoun_indices = find_pronoun_indices(text)
    result_text = text
    offset = 0

    def recursive_resolve_reference(reference_word, text, morph, depth=0, max_depth=5):
        if depth > max_depth or reference_word == 'None':
            return reference_word
        pronoun_pos = None
        for start, end in find_pronoun_indices(text):
            if text[start:end] == reference_word:
                pronoun_pos = start
                break
        if pronoun_pos is None:
            return reference_word
        pronoun_type = determine_pronoun_type(reference_word, None)
        candidates = find_candidates(text, pronoun_pos)
        if pronoun_type == 'личное':
            filtered_candidates = filter_personal_candidates(candidates, reference_word, morph, text)
        elif pronoun_type == 'притяжательное':
            norm_pronoun = normalize_word(reference_word)
            filtered_candidates = filter_possessive_candidates(candidates, norm_pronoun, morph, text)
        elif pronoun_type == 'возвратное':
            filtered_candidates = filter_reflexive_candidates(candidates, reference_word, morph, text, idioms)
        elif pronoun_type == 'относительное':
            filtered_candidates = filter_relative_candidates(candidates, reference_word, morph, text)
        else:
            filtered_candidates = candidates
        if isinstance(filtered_candidates, list):
            if len(filtered_candidates) > 1:
                ranked = rank_candidates(filtered_candidates, pronoun_pos, text, morph)
                new_ref = ranked[0]['word'] if ranked else 'None'
            elif len(filtered_candidates) == 1:
                new_ref = filtered_candidates[0]['word']
            else:
                new_ref = 'None'
        elif filtered_candidates is None:
            new_ref = 'None'
        else:
            new_ref = filtered_candidates.get('word', 'None')
        if new_ref == reference_word or new_ref == 'None':
            return new_ref
        else:
            return recursive_resolve_reference(new_ref, text, morph, depth+1, max_depth)

    for start, end in pronoun_indices:
        pronoun = text[start:end]
        norm_pronoun = normalize_word(pronoun)
        next_word_start = end
        next_word = None
        if next_word_start < len(text):
            next_match = re.search(r'\b[а-яёА-ЯЁ]+\b', text[next_word_start:])
            if next_match:
                next_word = next_match.group(0)
        pronoun_type = determine_pronoun_type(pronoun, next_word)
        candidates = find_candidates(text, start)
        if pronoun_type == 'личное':
            filtered_candidates = filter_personal_candidates(candidates, pronoun, morph, text)
        elif pronoun_type == 'притяжательное':
            filtered_candidates = filter_possessive_candidates(candidates, norm_pronoun, morph, text)
        elif pronoun_type == 'возвратное':
            filtered_candidates = filter_reflexive_candidates(candidates, pronoun, morph, text, idioms)
        elif pronoun_type == 'относительное':
            filtered_candidates = filter_relative_candidates(candidates, pronoun, morph, text)
        else:
            filtered_candidates = candidates
        if isinstance(filtered_candidates, list):
            if len(filtered_candidates) > 1:
                ranked = rank_candidates(filtered_candidates, start, text, morph)
                reference = ranked[0]['word'] if ranked else 'None'
            elif len(filtered_candidates) == 1:
                reference = filtered_candidates[0]['word']
            else:
                reference = 'None'
        elif filtered_candidates is None:
            reference = 'None'
        else:
            reference = filtered_candidates.get('word', 'None')
        reference = recursive_resolve_reference(reference, text, morph)
        annotation = f" [{reference}]"
        insert_pos = end + offset
        result_text = result_text[:insert_pos] + annotation + result_text[insert_pos:]
        offset += len(annotation)
    return result_text

