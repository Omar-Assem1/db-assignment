from __future__ import annotations

import re
from dataclasses import dataclass

from errors import QueryError

KEYWORDS = {
    "SELECT", "PROJECT", "JOIN", "UNION", "INTERSECT", "DIFFERENCE",
    "AGGREGATE", "RENAME", "AND", "OR", "NOT", "IN", "AS",
    "TRUE", "FALSE", "NULL",
}

# Mathematical symbols are aliases of the keywords above
SYMBOLS = {
    "σ": "SELECT", "π": "PROJECT", "⋈": "JOIN", "∪": "UNION",
    "∩": "INTERSECT", "−": "DIFFERENCE", "γ": "AGGREGATE", "ρ": "RENAME",
}

_TOKEN_RE = re.compile(r"""
    (?P<WS>\s+)
  | (?P<NUMBER>-?\d+\.\d+|-?\d+)
  | (?P<STRING>'(?:[^'\\]|\\.)*'|"(?:[^"\\]|\\.)*")
  | (?P<OP><=|>=|!=|<>|=|<|>)
  | (?P<SYM>[σπ⋈∪∩−γρ])
  | (?P<IDENT>[A-Za-z_][A-Za-z0-9_]*)
  | (?P<LPAREN>\()
  | (?P<RPAREN>\))
  | (?P<COMMA>,)
  | (?P<SEMI>;)
  | (?P<STAR>\*)
""", re.VERBOSE)


@dataclass(frozen=True)
class Token:
    kind: str      # NUMBER STRING OP KEYWORD IDENT LPAREN RPAREN COMMA SEMI STAR EOF
    value: object
    pos: int

    def is_keyword(self, *names: str) -> bool:
        return self.kind == "KEYWORD" and self.value in names


def tokenize(text: str) -> list[Token]:
    tokens: list[Token] = []
    i = 0
    while i < len(text):
        m = _TOKEN_RE.match(text, i)
        if not m:
            raise QueryError(f"Unexpected character {text[i]!r}", text, i)
        kind, raw = m.lastgroup, m.group()
        pos, i = m.start(), m.end()

        if kind == "WS":
            continue
        if kind == "NUMBER":
            tokens.append(Token("NUMBER", float(raw) if "." in raw else int(raw), pos))
        elif kind == "STRING":
            tokens.append(Token("STRING", re.sub(r"\\(.)", r"\1", raw[1:-1]), pos))
        elif kind == "OP":
            tokens.append(Token("OP", "!=" if raw == "<>" else raw, pos))
        elif kind == "SYM":
            tokens.append(Token("KEYWORD", SYMBOLS[raw], pos))
        elif kind == "IDENT":
            upper = raw.upper()
            if upper in KEYWORDS:
                tokens.append(Token("KEYWORD", upper, pos))
            else:
                tokens.append(Token("IDENT", raw, pos))
        else:
            tokens.append(Token(kind, raw, pos))

    tokens.append(Token("EOF", None, len(text)))
    return tokens