from __future__ import annotations

from ast_nodes import (Aggregate, AggSpec, And, Column, Comparison, Difference, InList,
                       InSubquery, Intersect, Join, Literal, Not, Or, Project, Rename,
                       Select, TableRef, Union_)
from errors import QueryError
from lexer import Token, tokenize

AGG_FUNCS = {"COUNT", "SUM", "AVG", "MIN", "MAX"}


class Parser:
    def __init__(self, text: str):
        self.text = text
        self.toks = tokenize(text)
        self.i = 0

    # ---- helpers ----
    def peek(self, k: int = 0) -> Token:
        return self.toks[min(self.i + k, len(self.toks) - 1)]

    def next(self) -> Token:
        t = self.toks[self.i]
        if t.kind != "EOF":
            self.i += 1
        return t

    def error(self, msg: str, tok: Token | None = None):
        raise QueryError(msg, self.text, (tok or self.peek()).pos)

    def expect(self, kind: str) -> Token:
        t = self.peek()
        if t.kind != kind:
            self.error(f"Expected {kind}, found {t.kind}{'' if t.value is None else ' ' + repr(t.value)}")
        return self.next()

    # ---- entry ----
    def parse(self):
        q = self.query()
        if self.peek().kind == "SEMI":
            self.next()
        if self.peek().kind != "EOF":
            self.error("Unexpected input after end of query")
        return q

    # ---- queries ----
    def query(self):
        t = self.peek()
        if t.kind == "IDENT":
            self.next()
            return TableRef(t.value)
        if t.kind == "LPAREN":
            self.next()
            q = self.query()
            self.expect("RPAREN")
            return q
        if t.kind == "KEYWORD":
            handler = {
                "SELECT": self._select, "PROJECT": self._project, "JOIN": self._join,
                "UNION": lambda: self._binary(Union_), "INTERSECT": lambda: self._binary(Intersect),
                "DIFFERENCE": lambda: self._binary(Difference),
                "AGGREGATE": self._aggregate, "RENAME": self._rename,
            }.get(t.value)
            if handler:
                self.next()
                self.expect("LPAREN")
                node = handler()
                self.expect("RPAREN")
                return node
        self.error("Expected a table name or an operator (SELECT, PROJECT, JOIN, ...)")

    def _select(self):
        cond = self.condition()
        self.expect("COMMA")
        return Select(cond, self.query())

    def _project(self):
        cols = []
        while self.peek().kind == "IDENT" and self.peek(1).kind == "COMMA":
            cols.append(self.next().value)
            self.next()
        if not cols:
            self.error("PROJECT needs at least one column before the relation")
        return Project(cols, self.query())

    def _join(self):
        left = self.query()
        self.expect("COMMA")
        right = self.query()
        cond = None
        if self.peek().kind == "COMMA":
            self.next()
            cond = self.condition()
        return Join(left, right, cond)

    def _binary(self, cls):
        left = self.query()
        self.expect("COMMA")
        return cls(left, self.query())

    def _aggregate(self):
        group = []
        if self.peek().kind != "SEMI":
            while True:
                group.append(self.expect("IDENT").value)
                if self.peek().kind != "COMMA":
                    break
                self.next()
        self.expect("SEMI")
        specs = []
        while (self.peek().kind == "IDENT" and self.peek(1).kind == "LPAREN"
               and self.peek().value.upper() in AGG_FUNCS):
            specs.append(self._agg_spec())
            self.expect("COMMA")
        if not specs:
            self.error("AGGREGATE needs at least one function such as COUNT(*) or SUM(col)")
        return Aggregate(group, specs, self.query())

    def _agg_spec(self) -> AggSpec:
        func = self.next().value.upper()
        self.expect("LPAREN")
        if self.peek().kind == "STAR":
            self.next()
            col = None
        else:
            col = self.expect("IDENT").value
        self.expect("RPAREN")
        alias = None
        if self.peek().is_keyword("AS"):
            self.next()
            alias = self.expect("IDENT").value
        return AggSpec(func, col, alias)

    def _rename(self):
        pairs = []
        while self.peek().kind == "IDENT" and self.peek(1).is_keyword("AS"):
            old = self.next().value
            self.next()
            pairs.append((old, self.expect("IDENT").value))
            self.expect("COMMA")
        if not pairs:
            self.error("RENAME needs 'old AS new' pairs before the relation")
        return Rename(pairs, self.query())

    # ---- conditions ----
    def condition(self):
        left = self._and()
        while self.peek().is_keyword("OR"):
            self.next()
            left = Or(left, self._and())
        return left

    def _and(self):
        left = self._not()
        while self.peek().is_keyword("AND"):
            self.next()
            left = And(left, self._not())
        return left

    def _not(self):
        if self.peek().is_keyword("NOT"):
            self.next()
            return Not(self._not())
        return self._primary()

    def _primary(self):
        if self.peek().kind == "LPAREN":
            self.next()
            c = self.condition()
            self.expect("RPAREN")
            return c
        left = self._operand()
        if self.peek().kind == "OP":
            op = self.next().value
            return Comparison(left, op, self._operand())
        negated = False
        if self.peek().is_keyword("NOT"):
            self.next()
            negated = True
        if not self.peek().is_keyword("IN"):
            self.error("Expected a comparison operator or IN")
        self.next()
        self.expect("LPAREN")
        if self._starts_literal():
            values = [self._operand(literal_only=True).value]
            while self.peek().kind == "COMMA":
                self.next()
                values.append(self._operand(literal_only=True).value)
            node = InList(left, values, negated)
        else:
            node = InSubquery(left, self.query(), negated)
        self.expect("RPAREN")
        return node

    def _starts_literal(self) -> bool:
        t = self.peek()
        return t.kind in ("NUMBER", "STRING") or t.is_keyword("TRUE", "FALSE", "NULL")

    def _operand(self, literal_only: bool = False):
        t = self.peek()
        if t.kind == "IDENT" and not literal_only:
            self.next()
            return Column(t.value)
        if t.kind in ("NUMBER", "STRING"):
            self.next()
            return Literal(t.value)
        if t.is_keyword("TRUE", "FALSE", "NULL"):
            self.next()
            return Literal({"TRUE": True, "FALSE": False, "NULL": None}[t.value])
        self.error("Expected a column name or a literal value")


def parse(text: str):
    return Parser(text).parse()