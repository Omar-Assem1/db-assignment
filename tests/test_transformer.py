from erd_loader import parse_erd
from transformer import transform


def build(data):
    return {t.name: t for t in transform(*parse_erd(data))}


def cols(t):
    return [c.name for c in t.columns]


EMP_DEPT = {
    "entities": [
        {"name": "Employee", "attributes": [
            {"name": "SSN", "isPrimaryKey": True},
            {"name": "Name", "composite": ["FirstName", "LastName"]},
            {"name": "Phone", "isMultiValued": True}]},
        {"name": "Department", "attributes": [
            {"name": "DeptID", "isPrimaryKey": True},
            {"name": "Name"},
            {"name": "Location", "isMultiValued": True}]},
    ],
    "relationships": [
        {"entity1": "Employee", "entity2": "Department", "name": "Works_In", "cardinality": "N:1"}
    ],
}


def test_sheet_example():
    t = build(EMP_DEPT)
    assert set(t) == {"Employee", "Department", "Employee_Phone", "Department_Location"}
    assert cols(t["Employee"]) == ["SSN", "FirstName", "LastName", "DeptID"]  # composite flattened + FK
    fk = t["Employee"].foreign_keys[0]
    assert (fk.columns, fk.ref_table, fk.ref_columns) == (["DeptID"], "Department", ["DeptID"])
    assert t["Employee_Phone"].pk_names() == ["SSN", "Phone"]


def test_many_to_many_with_attribute():
    t = build({
        "entities": [
            {"name": "Student", "attributes": [{"name": "StudentID", "isPrimaryKey": True}]},
            {"name": "Course", "attributes": [{"name": "CourseID", "isPrimaryKey": True}]},
        ],
        "relationships": [{"name": "Enrolled", "entity1": "Student", "entity2": "Course",
                           "cardinality": "M:N", "attributes": [{"name": "Grade"}]}],
    })
    assert cols(t["Enrolled"]) == ["StudentID", "CourseID", "Grade"]
    assert t["Enrolled"].pk_names() == ["StudentID", "CourseID"]
    assert len(t["Enrolled"].foreign_keys) == 2


def test_weak_entity():
    t = build({
        "entities": [
            {"name": "Employee", "attributes": [{"name": "SSN", "isPrimaryKey": True}]},
            {"name": "Dependent", "isWeak": True, "owner": "Employee",
             "attributes": [{"name": "DepName", "isPartialKey": True}]},
        ],
        "relationships": [{"name": "Has", "entity1": "Employee", "entity2": "Dependent",
                           "cardinality": "1:N"}],
    })
    assert t["Dependent"].pk_names() == ["SSN", "DepName"]
    assert t["Dependent"].foreign_keys[0].ref_table == "Employee"
    assert "Has" not in t  # identifying relationship adds nothing


def test_one_to_one_fk_on_total_side():
    t = build({
        "entities": [
            {"name": "Employee", "attributes": [{"name": "SSN", "isPrimaryKey": True}]},
            {"name": "Department", "attributes": [{"name": "DeptID", "isPrimaryKey": True}]},
        ],
        "relationships": [{"name": "Manages", "entity1": "Employee", "entity2": "Department",
                           "cardinality": "1:1", "participation": ["partial", "total"]}],
    })
    assert t["Department"].foreign_keys[0].ref_table == "Employee"
    assert not t["Employee"].foreign_keys


def test_self_relationship_name_clash():
    t = build({
        "entities": [{"name": "Employee", "attributes": [{"name": "SSN", "isPrimaryKey": True}]}],
        "relationships": [{"name": "Supervises", "entity1": "Employee", "entity2": "Employee",
                           "cardinality": "1:N"}],
    })
    assert cols(t["Employee"]) == ["SSN", "Supervises_SSN"]