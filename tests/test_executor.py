import pytest

from errors import QueryError
from executor import Executor
from operators import Relation

EMP = Relation(["EmpID", "Name", "Salary", "DeptID"],
               [(1, "Ali", 6000, 10), (2, "Sara", 4500, 10), (3, "Omar", 7000, 20), (4, "Nour", 3000, None)])
DEPT = Relation(["DeptID", "DeptName"], [(10, "IT"), (20, "HR"), (30, "Finance")])
ex = Executor({"Employee": EMP, "Department": DEPT})


def run(q):
    r = ex.run_text(q)
    return r.columns, r.rows


def test_select_and_project():
    assert run("PROJECT(Name, SELECT(Salary >= 5000 AND DeptID = 10, Employee))") == (["Name"], [("Ali",)])


def test_natural_join_skips_null_keys():
    cols, rows = run("JOIN(Employee, Department)")
    assert cols == ["EmpID", "Name", "Salary", "DeptID", "DeptName"] and len(rows) == 3


def test_set_ops():
    assert run("DIFFERENCE(PROJECT(DeptID, Department), PROJECT(DeptID, Employee))")[1] == [(30,)]
    assert run("INTERSECT(PROJECT(DeptID, Department), PROJECT(DeptID, Employee))")[1] == [(10,), (20,)]


def test_aggregate():
    assert run("AGGREGATE(DeptID; COUNT(*) AS n, SUM(Salary), Employee)") == (
        ["DeptID", "n", "SUM(Salary)"], [(10, 2, 10500), (20, 1, 7000), (None, 1, 3000)])
    assert run("AGGREGATE(; COUNT(*), SELECT(Salary > 99999, Employee))")[1] == [(0,)]


def test_in_subquery_and_rename():
    assert run("PROJECT(Name, SELECT(DeptID NOT IN (PROJECT(DeptID, Department)), Employee))")[1] == [("Nour",)]
    assert run("RENAME(Name AS Who, PROJECT(Name, Employee))")[0] == ["Who"]


def test_errors():
    with pytest.raises(QueryError):
        ex.run_text("SELECT(Bogus = 1, Employee)")
    with pytest.raises(QueryError):
        ex.run_text("PROJECT(Name Employee)")