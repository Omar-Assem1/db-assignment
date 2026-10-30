import re

from erd_loader import parse_erd
from renderer import _label
from transformer import transform


def test_label_has_no_empty_font_tags():
    tables = transform(*parse_erd({
        "entities": [{"name": "A", "attributes": [
            {"name": "ID", "isPrimaryKey": True}, {"name": "Plain"}]}],
    }))
    label = _label(tables[0])
    # an empty <FONT ...></FONT> element breaks Graphviz
    assert not re.search(r"<FONT[^>]*></FONT>", label)
    assert "<U>ID</U>" in label      # PK underlined
    assert "&nbsp;" in label         # non-key column gets a placeholder cell