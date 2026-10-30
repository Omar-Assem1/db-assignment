from __future__ import annotations


class QueryError(Exception):

    def __init__(self, message: str, text: str | None = None, pos: int | None = None):
        self.message, self.text, self.pos = message, text, pos
        super().__init__(self._format())

    def _format(self) -> str:
        if self.text is None or self.pos is None:
            return self.message
        return f"{self.message}\n  {self.text}\n  {' ' * self.pos}^"