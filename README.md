# Database Systems Assignment

Two tools built in Python:

| Part | Folder | What it does |
|---|---|---|
| 1 | `part1_erd_to_relational/` | Converts an ERD (JSON) into a visual relational schema diagram |
| 2 | `part2_query_executor/` | Parses and executes relational algebra queries on JSON tables (no pandas) |

## Project structure

```
db-assignment/
├── part1_erd_to_relational/
│   ├── main.py            # CLI
│   ├── erd_loader.py      # reads and validates the ERD JSON
│   ├── models.py          # Entity, Relationship, Table, Column, ForeignKey
│   ├── transformer.py     # ER-to-relational rules
│   ├── mpl_renderer.py    # matplotlib drawing (default)
│   ├── renderer.py        # Graphviz drawing (optional)
│   └── samples/           # example ERD files
├── part2_query_executor/
│   ├── main.py            # CLI
│   ├── lexer.py           # tokenizer
│   ├── parser.py          # recursive-descent parser -> AST
│   ├── ast_nodes.py       # AST node classes
│   ├── executor.py        # evaluates the AST
│   ├── operators.py       # Relation class and the relational operators
│   ├── printer.py         # ASCII table output
│   ├── errors.py          # QueryError with a position marker
│   ├── data/sample.json   # example dataset
│   └── queries/examples.txt
├── tests/                 # pytest tests for both parts
├── requirements.txt
└── README.md
```

## Setup

Python 3.10 or newer (developed on 3.14).

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

The Graphviz engine in Part 1 also needs the Graphviz program installed (`dot` on your PATH). The default matplotlib engine does not.

---

## Part 1: ERD to Relational Model

### Usage

```bash
cd part1_erd_to_relational

python main.py samples/employee_dept.json                  # print schema + PNG and SVG
python main.py samples/many_to_many.json -o output         # choose the output folder
python main.py samples/weak_entity.json -n my_schema       # choose the file name
python main.py samples/employee_dept.json --no-render      # text schema only
python main.py samples/employee_dept.json --engine graphviz
```

| Option | Meaning |
|---|---|
| `-o`, `--out-dir` | output directory (default `output`) |
| `-n`, `--name` | output file name without extension (default: input file name) |
| `--no-render` | only print the schema as text |
| `--engine` | `matplotlib` (default) or `graphviz` |

The tool prints the relational schema as text and saves `<name>.png` and `<name>.svg` in the output folder.

### Input format

```json
{
  "entities": [
    {
      "name": "Employee",
      "attributes": [
        { "name": "SSN", "isPrimaryKey": true },
        { "name": "Name", "composite": ["FirstName", "LastName"] },
        { "name": "Phone", "isMultiValued": true }
      ]
    },
    {
      "name": "Dependent",
      "isWeak": true,
      "owner": "Employee",
      "attributes": [ { "name": "DepName", "isPartialKey": true } ]
    }
  ],
  "relationships": [
    {
      "name": "Works_In",
      "entity1": "Employee",
      "entity2": "Department",
      "cardinality": "N:1",
      "participation": ["partial", "total"],
      "attributes": [ { "name": "Since" } ]
    }
  ]
}
```

| Field | Notes |
|---|---|
| `isPrimaryKey` | key attribute (a strong entity must have one) |
| `isPartialKey` | discriminator of a weak entity |
| `isMultiValued` | attribute that gets its own table |
| `composite` | list of sub-attributes that are flattened into columns |
| `isWeak` and `owner` | weak entity and the name of its owner entity |
| `cardinality` | `1:1`, `1:N`, `N:1`, `M:N` (aliases such as `N:M` and `M:M` are accepted) |
| `participation` | optional, two values (`total` or `partial`) for entity1 and entity2; default is partial for both |
| relationship `attributes` | optional descriptive attributes of the relationship |

Invalid files (unknown entity, missing key, bad cardinality, duplicate names) stop with a clear `Error:` message.

### Transformation rules

| ER construct | Relational result |
|---|---|
| Strong entity | Table whose PK is the key attribute(s) |
| Composite attribute | Replaced by one column per component |
| Multi-valued attribute | New table `Entity_Attribute` with PK = owner key + the value, and an FK to the owner |
| Weak entity | Table with the owner's PK as FK, plus the partial key; PK = owner key + partial key |
| Identifying relationship | No table; it is already represented by the weak entity's PK |
| 1:N | FK of the "1" side is added to the "N" side table |
| N:1 | FK of the "1" side is added to the "N" side table (mirror case) |
| 1:1 | FK placed on the side with total participation (default: entity1) |
| M:N | New table named after the relationship; PK = both FKs |
| Relationship attributes | Added to the FK table (1:1, 1:N) or to the new table (M:N) |
| Column name clash (e.g. recursive relationship) | The column is prefixed with the relationship name, e.g. `Supervises_SSN` |

### Diagram notation

- Each table is a box with a blue header containing the table name.
- Primary key columns are underlined and highlighted in yellow.
- Each column is tagged `PK`, `FK` or `PK, FK` on its right side.
- Arrows run from each foreign key column to the referenced primary key column.

### Example text output

```
Employee_Phone
  SSN  [PK,FK] -> Employee.SSN
  Phone  [PK]
```

---

## Part 2: Relational Algebra Query Executor

### Usage

```bash
cd part2_query_executor

python main.py data/sample.json -f queries/examples.txt                  # run a query file
python main.py data/sample.json -f queries/examples.txt --show-tables    # print input tables first
python main.py data/sample.json -q "SELECT(Salary >= 5000, Employee)"    # single query
python main.py data/sample.json                                          # interactive mode
```

| Option | Meaning |
|---|---|
| `-q`, `--query` | query to run (can be repeated) |
| `-f`, `--file` | file with one query per line; `--` starts a comment |
| `--show-tables` | print all input tables before the queries |

In interactive mode, enter queries at the `ra>` prompt. An empty line or Ctrl-D quits.

### Dataset format

```json
{
  "Employee": {
    "columns": ["EmpID", "Name", "Salary", "DeptID"],
    "rows": [[1, "Ali", 6000, 10], [4, "Nour", 3000, null]]
  },
  "Department": {
    "columns": ["DeptID", "DeptName"],
    "rows": [[10, "IT"], [20, "HR"]]
  }
}
```

A table may also be a list of objects (`[{"DeptID": 10, "DeptName": "IT"}]`), and the whole dataset may be wrapped in a top-level `"tables"` key. JSON `null` is read as NULL.

### Query language

Keywords are case-insensitive. The mathematical symbols can be used instead of the keywords.

| Operation | Keyword | Symbol | Syntax |
|---|---|---|---|
| Selection | `SELECT` | σ | `SELECT(condition, R)` |
| Projection | `PROJECT` | π | `PROJECT(col1, col2, R)` |
| Join | `JOIN` | ⋈ | `JOIN(R, S)` (natural) or `JOIN(R, S, condition)` (theta) |
| Union | `UNION` | ∪ | `UNION(R, S)` |
| Intersection | `INTERSECT` | ∩ | `INTERSECT(R, S)` |
| Difference | `DIFFERENCE` | − | `DIFFERENCE(R, S)` |
| Aggregation | `AGGREGATE` | γ | `AGGREGATE(group_cols; FUNC(col) AS alias, R)` |
| Rename | `RENAME` | ρ | `RENAME(old AS new, R)` |

**Conditions:** comparisons `= != <> < > <= >=`, combined with `AND`, `OR`, `NOT` and parentheses. Operands are column names or literals (numbers, `'strings'`, `TRUE`, `FALSE`, `NULL`). Membership tests: `col IN (1, 2, 3)`, `col NOT IN (...)`, and `col IN (<query>)` for subqueries.

**Aggregate functions:** `COUNT(*)`, `COUNT(col)`, `SUM`, `AVG`, `MIN`, `MAX`. The grouping list may be empty: `AGGREGATE(; COUNT(*), R)`. Without `AS`, the output column is named like `AVG(Salary)`.

### Nested queries

Operators nest to any depth, and `IN` / `NOT IN` accept a subquery:

```
PROJECT(Name, DeptName, SELECT(Salary > 4000, JOIN(Employee, Department)))
SELECT(DeptID IN (PROJECT(DeptID, SELECT(DeptName = 'IT', Department))), Employee)
```

### Example session

```
> PROJECT(Name, DeptName, JOIN(Employee, Department))
+------+----------+
| Name | DeptName |
+------+----------+
| Ali  | IT       |
| Sara | IT       |
| Omar | HR       |
+------+----------+
(3 rows)

> AGGREGATE(DeptID; COUNT(*) AS n, AVG(Salary), Employee)
+--------+---+-------------+
| DeptID | n | AVG(Salary) |
+--------+---+-------------+
| 10     | 2 | 5250        |
| 20     | 1 | 7000        |
| NULL   | 1 | 3000        |
+--------+---+-------------+
(3 rows)
```

More examples are in `queries/examples.txt`.

### Error messages

Errors point at the exact position in the query:

```
> SELECT(Bogus = 1, Employee)
Query error: Unknown column 'Bogus' (available: EmpID, Name, Salary, DeptID)
```

### Semantics and limitations

- `PROJECT`, `JOIN` (natural), `UNION`, `INTERSECT` and `DIFFERENCE` remove duplicate rows (set semantics).
- A natural join never matches NULL keys, so rows with a NULL join column are dropped.
- Set operations require both relations to have the same column names; the column order may differ.
- A theta join needs distinct column names on both sides; use `RENAME` first if they clash.
- `NOT IN` keeps rows whose value is NULL (this is not the same as SQL's three-valued logic).
- Subqueries are uncorrelated and must return exactly one column.
- Qualified names such as `Employee.DeptID` are not supported.

---

## Tests

From the repository root:

```bash
python -m pytest -v
```

| File | Covers |
|---|---|
| `tests/test_lexer.py` | tokens, keyword aliases, error positions |
| `tests/test_executor.py` | all relational operators, subqueries, errors |
| `tests/test_transformer.py` | ER-to-relational rules |
| `tests/test_renderer.py` | Graphviz label generation |

## Author

Name: Omar Assem Ahmed &nbsp;|&nbsp; ID: 23010610 &nbsp;|&nbsp; Course: Database Systems