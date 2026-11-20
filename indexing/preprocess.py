"""Text preprocessing: tokenize -> (optional) stop-word removal -> (optional) Porter stemming.
"""
import re

# Common words ignored when indexing/querying; the last line is extra words frequent in this corpus.
STOPWORDS = frozenset("""
a about above after again against all am an and any are as at be because been before being
below between both but by can could did do does doing down during each few for from further
had has have having he her here hers him his how i if in into is it its itself just me more
most my no nor not now of off on once only or other our out over own same she should so some
such than that the their them then there these they this those through to too under until up
very was we were what when where which while who whom why will with would you your yours
also one us may get like
""".split())

_TOKEN_RE = re.compile(r"[a-z0-9]+(?:'[a-z]+)?")


def tokenize(text):
    """Lowercase and split into alphanumeric tokens (non-ASCII script such as Khmer is dropped).

    Pure-digit tokens are dropped: bare numbers (prices, list numbers) are noise for retrieval.
    """
    toks = [t.replace("'", "") for t in _TOKEN_RE.findall(text.lower())]
    return [t for t in toks if not t.isdigit()]


# ---------------------------------------------------------------- Porter stemmer
_V = "aeiou"


def _cons(w, i):
    c = w[i]
    if c in _V:
        return False
    if c == "y":
        return i == 0 or not _cons(w, i - 1)
    return True


def _m(stem_):
    """Measure: number of VC sequences in the stem."""
    n, prev_v = 0, False
    for i in range(len(stem_)):
        v = not _cons(stem_, i)
        if prev_v and not v:
            n += 1
        prev_v = v
    return n


def _has_v(stem_):
    return any(not _cons(stem_, i) for i in range(len(stem_)))


def _dc(w):
    return len(w) >= 2 and w[-1] == w[-2] and _cons(w, len(w) - 1)


def _cvc(w):
    return (len(w) >= 3 and _cons(w, len(w) - 3) and not _cons(w, len(w) - 2)
            and _cons(w, len(w) - 1) and w[-1] not in "wxy")


def _rep(w, rules, min_m):
    for suf, new in rules:
        if w.endswith(suf):
            s = w[: -len(suf)]
            return s + new if _m(s) > min_m else w
    return w


_S2 = [("ational", "ate"), ("tional", "tion"), ("enci", "ence"), ("anci", "ance"),
       ("izer", "ize"), ("abli", "able"), ("alli", "al"), ("entli", "ent"), ("eli", "e"),
       ("ousli", "ous"), ("ization", "ize"), ("ation", "ate"), ("ator", "ate"),
       ("alism", "al"), ("iveness", "ive"), ("fulness", "ful"), ("ousness", "ous"),
       ("aliti", "al"), ("iviti", "ive"), ("biliti", "ble")]
_S3 = [("icate", "ic"), ("ative", ""), ("alize", "al"), ("iciti", "ic"),
       ("ical", "ic"), ("ful", ""), ("ness", "")]
_S4 = ["al", "ance", "ence", "er", "ic", "able", "ible", "ant", "ement", "ment", "ent",
       "ion", "ou", "ism", "ate", "iti", "ous", "ive", "ize"]


def stem(w):
    """Porter stemmer."""
    if len(w) <= 2:
        return w
    # step 1a
    if w.endswith("sses") or w.endswith("ies"):
        w = w[:-2]
    elif w.endswith("s") and not w.endswith("ss"):
        w = w[:-1]
    # step 1b
    if w.endswith("eed"):
        if _m(w[:-3]) > 0:
            w = w[:-1]
    else:
        for suf in ("ed", "ing"):
            if w.endswith(suf) and _has_v(w[: -len(suf)]):
                w = w[: -len(suf)]
                if w.endswith(("at", "bl", "iz")):
                    w += "e"
                elif _dc(w) and w[-1] not in "lsz":
                    w = w[:-1]
                elif _m(w) == 1 and _cvc(w):
                    w += "e"
                break
    # step 1c
    if w.endswith("y") and _has_v(w[:-1]):
        w = w[:-1] + "i"
    # steps 2, 3
    w = _rep(w, _S2, 0)
    w = _rep(w, _S3, 0)
    # step 4
    for suf in _S4:
        if w.endswith(suf):
            s = w[: -len(suf)]
            if _m(s) > 1 and (suf != "ion" or s.endswith(("s", "t"))):
                w = s
            break
    # step 5
    if w.endswith("e"):
        s = w[:-1]
        if _m(s) > 1 or (_m(s) == 1 and not _cvc(s)):
            w = s
    if _m(w) > 1 and _dc(w) and w.endswith("l"):
        w = w[:-1]
    return w

_cache = {}

def cached_stem(w):
    if w not in _cache:
        _cache[w] = stem(w)
    return _cache[w]

def preprocess(text, remove_stopwords=True, use_stemming=True):
    """Full pipeline used for BOTH documents and queries (they must match)."""
    toks = tokenize(text)
    if remove_stopwords:
        toks = [t for t in toks if t not in STOPWORDS]
    if use_stemming:
        toks = [cached_stem(t) for t in toks]
    return toks
