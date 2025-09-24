from .morph import morph, normalize_word, get_pos
from .resources import all_pronouns, collective_nouns, common_gender_nouns
from .helpers import find_coord_groups, find_addressed_entity, get_speaker_context
from .tokenization import get_sentences, get_words

def is_collective_noun(word):
    return normalize_word(word) in collective_nouns

def is_common_gender_noun(word):
    return normalize_word(word) in common_gender_nouns

def find_candidates(text, pronoun_position):
    text_lower = text.lower()
    sentences = get_sentences(text)
    current_sentence_idx = 0
    current_pos = 0
    for i, sentence in enumerate(sentences):
        sentence_length = len(sentence)
        if current_pos <= pronoun_position < current_pos + sentence_length:
            current_sentence_idx = i
            break
        current_pos += sentence_length
    start_sentence_idx = max(0, current_sentence_idx - 3)
    end_sentence_idx = current_sentence_idx
    relevant_sentences = sentences[start_sentence_idx:end_sentence_idx+1]
    if current_sentence_idx > 0:
        current_sentence_start = sum(len(s) for s in sentences[:current_sentence_idx])
        relevant_part = text_lower[current_sentence_start:pronoun_position]
        relevant_sentences[-1] = relevant_part
    else:
        relevant_sentences[0] = relevant_sentences[0][:pronoun_position]
    search_text = " ".join(relevant_sentences)
    words = get_words(search_text)
    word_positions = []
    current_pos = 0
    for word in words:
        start = search_text.find(word, current_pos)
        end = start + len(word)
        word_positions.append((word, start, end))
        current_pos = end
    candidates = []
    def add_candidate(word, start, end, pos, normalized, gender=None, number=None, is_group=False):
        candidates.append({
            'word': word,
            'start': start,
            'end': end,
            'pos': pos,
            'normalized': normalized,
            'gender': gender,
            'number': number,
            'is_group': is_group
        })
    for word, start, end in word_positions:
        parsed = morph.parse(word)[0]
        pos = parsed.tag.POS
        normalized_word = normalize_word(word)
        gender = parsed.tag.gender
        number = parsed.tag.number
        if pos == 'NOUN' or normalized_word in all_pronouns:
            vy_forms = {'вы', 'вас', 'вам', 'вами'}
            if normalized_word in vy_forms:
                add_candidate(word, start, end, pos, normalized_word, None, 'sing')
                add_candidate(word, start, end, pos, normalized_word, None, 'plur')
            elif is_common_gender_noun(word):
                add_candidate(word, start, end, pos, normalized_word, 'masc', number)
                add_candidate(word, start, end, pos, normalized_word, 'femn', number)
            elif is_collective_noun(word):
                add_candidate(word, start, end, pos, normalized_word, gender, 'sing')
                add_candidate(word, start, end, pos, normalized_word, gender, 'plur')
            else:
                add_candidate(word, start, end, pos, normalized_word, gender, number)
    full_search_text = " ".join(sentences[start_sentence_idx:end_sentence_idx+1])
    coord_groups = find_coord_groups(full_search_text)
    for group in coord_groups:
        if len(group) > 1:
            group_text = " и ".join(group)
            add_candidate(group_text, -1, -1, 'NOUN', group_text.lower(), None, 'plur', True)
    pronoun_word = None
    for word, start, end in word_positions:
        absolute_start = current_sentence_start + start if current_sentence_idx > 0 else start
        if absolute_start <= pronoun_position <= absolute_start + len(word):
            pronoun_word = word
            break
    if pronoun_word:
        for i in range(max(0, current_sentence_idx - 1), current_sentence_idx + 1):
            if i < len(sentences):
                sentence_to_check = sentences[i]
                addressed_entity = find_addressed_entity(pronoun_word, sentence_to_check)
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
                    add_candidate(addressed_entity, -1, -1, 'NOUN', addressed_entity.lower(), gender, number)
                    break
    if pronoun_word:
        speaker = get_speaker_context(pronoun_word, text)
        if speaker:
            parsed = morph.parse(speaker)[0]
            gender = parsed.tag.gender
            number = parsed.tag.number
            add_candidate(speaker, -1, -1, 'NOUN', speaker.lower(), gender, number)
    return candidates

