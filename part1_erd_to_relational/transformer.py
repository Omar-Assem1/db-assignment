from __future__ import annotations

from models import Column, Entity, ForeignKey, Relationship, Table


class ERTransformer:
    def __init__(self, entities: list[Entity], relationships: list[Relationship]):
        self.entities = {e.name: e for e in entities}
        self.relationships = relationships
        self.tables: dict[str, Table] = {}

    def transform(self) -> list[Table]:
        ordered = self._ordered_entities()
        for e in ordered:
            self._entity_to_table(e)
        for e in ordered:
            self._multivalued_tables(e)
        for r in self.relationships:
            self._relationship(r)
        return list(self.tables.values())

    def _ordered_entities(self) -> list[Entity]:
        done: set[str] = set()
        out: list[Entity] = []

        def visit(e: Entity, stack: tuple = ()):
            if e.name in done:
                return
            if e.name in stack:
                raise ValueError(f"Circular weak-entity ownership involving '{e.name}'")
            if e.is_weak:
                visit(self.entities[e.owner], stack + (e.name,))
            done.add(e.name)
            out.append(e)

        for e in self.entities.values():
            visit(e)
        return out

    def _entity_to_table(self, e: Entity) -> None:
        t = Table(e.name)
        for a in e.attributes:
            if a.is_multi_valued:
                continue
            is_pk = a.is_primary_key or a.is_partial_key
            for n in a.flat_names():
                t.add_column(Column(n, is_pk=is_pk))
        if e.is_weak:
            self._add_fk(t, self.tables[e.owner], is_pk=True, prefix=e.owner, index=0)
        self._register(t)

    def _multivalued_tables(self, e: Entity) -> None:
        base = self.tables[e.name]
        for a in e.attributes:
            if not a.is_multi_valued:
                continue
            mv = Table(f"{e.name}_{a.name}")
            for n in a.flat_names():
                mv.add_column(Column(n, is_pk=True))
            self._add_fk(mv, base, is_pk=True, prefix=e.name, index=0)
            self._register(mv)

    def _relationship(self, r: Relationship) -> None:
        ea, eb = self.entities[r.entity1], self.entities[r.entity2]
        if (ea.is_weak and ea.owner == eb.name) or (eb.is_weak and eb.owner == ea.name):
            return  # identifying relationship, already represented by the weak entity's PK
        a, b = self.tables[r.entity1], self.tables[r.entity2]

        if r.cardinality == "M:N":
            self._many_to_many(r, a, b)
        elif r.cardinality == "1:N":
            self._fk_side(r, holder=b, ref=a)
        elif r.cardinality == "N:1":
            self._fk_side(r, holder=a, ref=b)
        else:  # 1:1 -> FK on the total-participation side
            if r.participation2 == "total" and r.participation1 != "total":
                self._fk_side(r, holder=b, ref=a)
            else:
                self._fk_side(r, holder=a, ref=b)

    def _fk_side(self, r: Relationship, holder: Table, ref: Table) -> None:
        self._add_fk(holder, ref, is_pk=False, prefix=r.name)
        self._add_rel_attributes(holder, r)

    def _many_to_many(self, r: Relationship, a: Table, b: Table) -> None:
        t = Table(r.name)
        self._add_fk(t, a, is_pk=True, prefix=r.name)
        self._add_fk(t, b, is_pk=True, prefix=r.name)
        self._add_rel_attributes(t, r)
        self._register(t)

    def _register(self, t: Table) -> None:
        if t.name in self.tables:
            raise ValueError(f"Table name clash: '{t.name}' already exists")
        self.tables[t.name] = t

    @staticmethod
    def _free_name(table: Table, base: str, prefix: str) -> str:
        if not table.has_column(base):
            return base
        candidate, n = f"{prefix}_{base}", 2
        while table.has_column(candidate):
            candidate, n = f"{prefix}_{base}{n}", n + 1
        return candidate

    def _add_fk(self, table: Table, target: Table, *, is_pk: bool, prefix: str,
                index: int | None = None) -> list[str]:
        cols, refs = [], []
        for i, pk in enumerate(target.pk_names()):
            name = self._free_name(table, pk, prefix)
            table.add_column(Column(name, is_pk=is_pk, is_fk=True),
                             None if index is None else index + i)
            cols.append(name)
            refs.append(pk)
        table.foreign_keys.append(ForeignKey(cols, target.name, refs))
        return cols

    def _add_rel_attributes(self, table: Table, r: Relationship) -> None:
        for a in r.attributes:
            if a.is_multi_valued:
                raise ValueError(
                    f"Multi-valued attribute '{a.name}' on relationship '{r.name}' is not supported")
            for n in a.flat_names():
                table.add_column(Column(self._free_name(table, n, r.name)))


def transform(entities: list[Entity], relationships: list[Relationship]) -> list[Table]:
    return ERTransformer(entities, relationships).transform()