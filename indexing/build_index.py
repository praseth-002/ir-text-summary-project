"""Build and save the index.   Run from the project root:  python -m indexing.build_index"""
import json, os, sys
from .inverted_index import InvertedIndex

CORPUS = "data/corpus.json"
OUT = "data/index.json"


def main():
    with open(CORPUS, encoding="utf-8") as f:
        corpus = json.load(f)
    idx = InvertedIndex.from_corpus(corpus)
    idx.save(OUT)
    print(f"Indexed {idx.N} chunks, {len(idx.postings)} unique terms, avgdl={idx.avgdl:.1f}")
    print(f"Saved to {OUT} ({os.path.getsize(OUT)/1024:.0f} KB)")
    top = sorted(idx.postings, key=idx.df, reverse=True)[:10]
    print("Top terms by df:", [(t, idx.df(t)) for t in top])


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
