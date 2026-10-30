import pytest

from errors import QueryError
from lexer import tokenize


def kinds(text):
    return [(t.kind, t.value) for t in tokenize(text)][:-1]   # drop EOF


def test_simple_select():
    assert kinds("SELECT(Salary >= 5000, Employee)") == [
        ("KEYWORD", "SELECT"), ("LPAREN", "("), ("IDENT", "Salary"), ("OP", ">="),
        ("NUMBER", 5000), ("COMMA", ","), ("IDENT", "Employee"), ("RPAREN", ")"),
    ]


def test_keywords_are_case_insensitive_but_identifiers_keep_case():
    assert kinds("select(Name, employee)")[0] == ("KEYWORD", "SELECT")
    assert ("IDENT", "employee") in kinds("select(Name, employee)")


def test_strings_numbers_and_ne_alias():
    assert kinds("Name <> 'Al\\'i'") == [("IDENT", "Name"), ("OP", "!="), ("STRING", "Al'i")]
    assert kinds("x = -3.5") == [("IDENT", "x"), ("OP", "="), ("NUMBER", -3.5)]


def test_math_symbols_are_keyword_aliases():
    assert kinds("σ π ⋈ ∪ ∩ − γ ρ") == [("KEYWORD", k) for k in (
        "SELECT", "PROJECT", "JOIN", "UNION", "INTERSECT", "DIFFERENCE", "AGGREGATE", "RENAME")]


def test_aggregate_punctuation():
    assert [k for k, _ in kinds("AGGREGATE(DeptID; COUNT(*) AS n, E)")] == [
        "KEYWORD", "LPAREN", "IDENT", "SEMI", "IDENT", "LPAREN", "STAR", "RPAREN",
        "KEYWORD", "IDENT", "COMMA", "IDENT", "RPAREN"]


def test_unexpected_character_reports_position():
    with pytest.raises(QueryError) as e:
        tokenize("SELECT(a # 1, T)")
    assert e.value.pos == 9