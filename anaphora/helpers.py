import re
from nltk.tokenize import word_tokenize
from .morph import morph, get_pos

def smart_capitalize(original, normal):
    if original and original[0].isupper():
        return normal.capitalize()
    return normal

def find_coord_groups(sentence):
    patterns = [
        r'((?:и\s+[А-ЯЁа-яё]+\s*,\s*)+(и\s+[А-ЯЁа-яё]+))',
        r'((?:[А-ЯЁа-яё]+,\s*)+[А-ЯЁа-яё]+\s+и\s+[А-ЯЁа-яё]+)',
        r'([А-ЯЁа-яё]+\s+и\s+[А-ЯЁа-яё]+)',
        r'((?:[А-ЯЁа-яё]+,\s+)+[А-ЯЁа-яё]+)',
        r'([А-ЯЁа-яё]+\s+с\s+[А-ЯЁа-яё]+)',
    ]
    results = []
    spans = []
    for pattern in patterns:
        for match in re.finditer(pattern, sentence):
            start, end = match.start(), match.end()
            if any(s <= start and e >= end or start <= s and end >= e for s, e in spans):
                continue
            group = match.group()
            tokens = word_tokenize(group, language='russian')
            names = []
            i = 0
            while i < len(tokens):
                w = tokens[i]
                norm = morph.parse(w)[0].normal_form
                pos = morph.parse(w)[0].tag.POS
                if pos == 'NOUN':
                    names.append(smart_capitalize(w, norm))
                if w.lower() in {'и', 'или', 'с'} and i + 1 < len(tokens):
                    i += 1
                    continue
                i += 1
            if len(names) > 1:
                results.append(names)
                spans.append((start, end))
    return results

def find_addressed_entity(pronoun, sentence):
    norm_pronoun = pronoun.lower()
    match = re.search(r'\b' + re.escape(norm_pronoun) + r'\b', sentence.lower())
    if not match:
        return None
    start_pos = match.end()
    pattern = r',\s*([А-ЯЁа-яё]+(?:\s+[А-ЯЁа-яё]+)*)\s*,'
    for m in re.finditer(pattern, sentence[start_pos:]):
        addressed = m.group(1).strip()
        words = addressed.split()
        has_noun = False
        for w in words:
            pos = get_pos(w)
            if pos == 'NOUN':
                has_noun = True
                break
        if has_noun:
            return addressed
    return None

def get_speaker_context(pronoun, text, pronoun_pos):
    norm_pronoun = pronoun.lower()
    quotes_pattern = r'«[^«»]*?»|\"[^\"]*?\"'
    speeches = list(re.finditer(quotes_pattern, text))
    if pronoun_pos is not None and pronoun_pos != -1:
        for s in speeches:
            if s.start() <= pronoun_pos < s.end():
                before = text[:s.start()].strip()
                after = text[s.end():].strip()
                before_author_match = re.search(r'([А-ЯЁа-яё]+\s+[А-ЯЁа-яё]+|[А-ЯЁа-яё]+)\s*[:,-]\s*$', before)
                if before_author_match:
                    candidate = before_author_match.group(1).strip()
                    words = re.findall(r'[А-ЯЁа-яё]+', candidate)
                    if words:
                        last_two = words[-2:] if len(words) >= 2 else words
                        name_parts = []
                        for w in last_two:
                            if get_pos(w) == 'NOUN':
                                name_parts.append(w)
                        if name_parts:
                            return " ".join(name_parts)
                    return candidate
                tail = re.sub(r'^[\s,.\-–—]+', '', after)
                tokens = re.findall(r'[А-ЯЁа-яё]+', tail)
                i = 0
                while i < len(tokens) and get_pos(tokens[i]) != 'NOUN':
                    i += 1
                if i < len(tokens):
                    name_parts = [tokens[i]]
                    if i + 1 < len(tokens) and get_pos(tokens[i + 1]) == 'NOUN':
                        name_parts.append(tokens[i + 1])
                    return " ".join(name_parts)
                return None
    lines = text.split('\n')
    pronoun_in_speech_line = False
    for line in lines:
        if line.strip().startswith('-') and norm_pronoun in line.lower():
            pronoun_in_speech_line = True
            break
    if pronoun_in_speech_line:
        for i, line in enumerate(lines):
            if line.strip().startswith('-') and norm_pronoun in line.lower():
                for j in range(i - 1, -1, -1):
                    author_line = lines[j].strip()
                    if author_line and not author_line.startswith('-'):
                        author_part = author_line.split(',', 1)
                        if len(author_part) == 2:
                            return author_part[1].strip()
                        else:
                            return author_line
    return None

def is_subject_simple(word, sentence, morph):
    normalized_word = word.lower().replace('ё', 'е')
    parsed = morph.parse(word)[0]
    if parsed.tag.POS not in ['NOUN', 'NPRO']:
        return False
    if 'nomn' not in str(parsed.tag.case):
        return False
    sentence_lower = sentence.lower().replace('ё', 'е')
    word_position = sentence_lower.find(normalized_word)
    if word_position < len(sentence) / 3:
        return True
    return False

