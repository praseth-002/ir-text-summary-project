"""Run from project root:  python -m indexing.test_indexing"""
from .preprocess import stem
from .inverted_index import InvertedIndex
from .boolean_retrieval import boolean_search

# Porter stemmer sanity checks (classic examples)
for w, s in {"caresses": "caress", "ponies": "poni", "running": "run", "hopping": "hop",
             "relational": "relat", "traveling": "travel", "agreed": "agre"}.items():
    assert stem(w) == s, (w, stem(w), s)

corpus = {
    "d1": {"text": "Take a bus from Phnom Penh to Siem Reap.", "title": "t", "section": "s", "url": "u"},
    "d2": {"text": "Taxi from Phnom Penh to Kampot costs more.", "title": "t", "section": "s", "url": "u"},
    "d3": {"text": "Angkor Wat temples near Siem Reap.", "title": "t", "section": "s", "url": "u"},
}
idx = InvertedIndex.from_corpus(corpus)
assert boolean_search(idx, "bus AND siem") == ["d1"]
assert boolean_search(idx, "phnom OR angkor") == ["d1", "d2", "d3"]
assert boolean_search(idx, "phnom NOT taxi") == ["d1"]
assert boolean_search(idx, "(bus OR taxi) AND penh") == ["d1", "d2"]
assert boolean_search(idx, "siem reap") == ["d1", "d3"]          # implicit AND
assert boolean_search(idx, "temples") == ["d3"]                  # stemming: temple
assert idx.df("siem") == 2 and idx.tf("siem", "d1") == 1
print("all indexing tests passed")
