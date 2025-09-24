from .helpers import is_subject_simple

def rank_candidates(candidates, pronoun_position, text, morph):
    freq = {}
    for cand in candidates:
        word_norm = cand['normalized']
        freq[word_norm] = freq.get(word_norm, 0) + 1
    distances = []
    for c in candidates:
        start = c.get('start', -1)
        if start >= 0:
            dist = abs(pronoun_position - start)
        else:
            dist = float('inf')
        distances.append(dist)
    min_distance = min(distances) if distances else None
    scored_candidates = []
    for c, dist in zip(candidates, distances):
        score = 0
        if is_subject_simple(c['word'], text, morph):
            score += 2
        score += freq.get(c['normalized'], 0)
        if min_distance is not None and dist == min_distance:
            score += 2
        scored_candidates.append((score, c))
    scored_candidates.sort(key=lambda x: x[0], reverse=True)
    return [c for score, c in scored_candidates]

