"""Boolean retrieval over the inverted index.

Query syntax:  AND, OR, NOT (case-insensitive), parentheses.
Adjacent terms with no operator mean AND.   e.g.  bus AND (phnom penh OR siem reap) NOT taxi
Precedence: NOT > AND > OR.
"""
import re
from .inverted_index import InvertedIndex

_TOK = re.compile(r"\(|\)|[^\s()]+")
_OPS = {"AND", "OR", "NOT"}


class _Parser:
    def __init__(self, tokens, index):
        self.t, self.i, self.idx = tokens, 0, index

    def peek(self):
        return self.t[self.i] if self.i < len(self.t) else None

    def next(self):
        tok = self.peek()
        self.i += 1
        return tok

    def or_expr(self):
        res = self.and_expr()
        while self.peek() and self.peek().upper() == "OR":
            self.next()
            res = res | self.and_expr()
        return res

    def and_expr(self):
        res = self.not_expr()
        while self.peek() and self.peek() != ")" and self.peek().upper() != "OR":
            if self.peek().upper() == "AND":
                self.next()
            res = res & self.not_expr()          # implicit AND when no operator
        return res

    def not_expr(self):
        if self.peek() and self.peek().upper() == "NOT":
            self.next()
            return self.idx.all_docs() - self.not_expr()
        return self.atom()

    def atom(self):
        tok = self.next()
        if tok is None:
            raise ValueError("Unexpected end of query")
        if tok == "(":
            res = self.or_expr()
            if self.next() != ")":
                raise ValueError("Missing closing parenthesis")
            return res
        if tok == ")" or tok.upper() in _OPS:
            raise ValueError(f"Unexpected '{tok}'")
        # a word is analysed like document text; it may yield 0 terms (stop word) or 1+
        terms = self.idx.analyze(tok)
        if not terms:
            return self.idx.all_docs()           # stop word: neutral for AND
        res = set(self.idx.get_postings(terms[0]))
        for t in terms[1:]:
            res &= set(self.idx.get_postings(t))
        return res


def boolean_search(index: InvertedIndex, query: str):
    """Return the sorted list of doc_ids that satisfy the Boolean query."""
    tokens = _TOK.findall(query)
    if not tokens:
        return []
    p = _Parser(tokens, index)
    res = p.or_expr()
    if p.peek() is not None:
        raise ValueError(f"Unexpected '{p.peek()}'")
    return sorted(res)
