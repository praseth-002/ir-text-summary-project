"""Inverted index built from scratch.

Structure (what the ranking module needs for TF-IDF / BM25):
    postings : term -> {doc_id: term_frequency}
    doc_len  : doc_id -> number of indexed tokens
    N, avgdl : collection size, average doc length
    df(term) = len(postings[term])
"""
import json
from .preprocess import preprocess


class InvertedIndex:
    def __init__(self, remove_stopwords=True, use_stemming=True):
        self.remove_stopwords = remove_stopwords
        self.use_stemming = use_stemming
        self.postings = {}
        self.doc_len = {}
        self.docs_meta = {}     # doc_id -> {title, section, url} for displaying results / citations

    # ---- building
    def analyze(self, text):
        return preprocess(text, self.remove_stopwords, self.use_stemming)

    def add_document(self, doc_id, text, meta=None):
        tokens = self.analyze(text)
        self.doc_len[doc_id] = len(tokens)
        if meta:
            self.docs_meta[doc_id] = meta
        tf = {}
        for t in tokens:
            tf[t] = tf.get(t, 0) + 1
        for term, f in tf.items():
            self.postings.setdefault(term, {})[doc_id] = f

    @classmethod
    def from_corpus(cls, corpus, **kw):
        """corpus: {chunk_id: {url, title, section, text}} as produced by data_collection/scrape.py"""
        idx = cls(**kw)
        for doc_id, d in corpus.items():
            idx.add_document(doc_id, d["text"],
                            meta={"title": d["title"], "section": d["section"], "url": d["url"]})
        return idx

    # ---- statistics
    @property
    def N(self):
        return len(self.doc_len)

    @property
    def avgdl(self):
        return sum(self.doc_len.values()) / self.N if self.N else 0.0

    def df(self, term):
        return len(self.postings.get(term, ()))

    def tf(self, term, doc_id):
        return self.postings.get(term, {}).get(doc_id, 0)

    def get_postings(self, term):
        return self.postings.get(term, {})

    def all_docs(self):
        return set(self.doc_len)

    # ---- persistence
    def save(self, path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"remove_stopwords": self.remove_stopwords,
                       "use_stemming": self.use_stemming,
                       "postings": self.postings, "doc_len": self.doc_len,
                       "docs_meta": self.docs_meta}, f, ensure_ascii=False)

    @classmethod
    def load(cls, path):
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        idx = cls(d["remove_stopwords"], d["use_stemming"])
        idx.postings, idx.doc_len, idx.docs_meta = d["postings"], d["doc_len"], d["docs_meta"]
        return idx
