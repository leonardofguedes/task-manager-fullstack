import pytest

from app.domain.ids import persisted_id


def test_persisted_id_returns_the_id() -> None:
    assert persisted_id(7) == 7


def test_persisted_id_rejects_unsaved_entity() -> None:
    # A real check, not an `assert`: it must also hold under `python -O`.
    with pytest.raises(RuntimeError, match="not persisted"):
        persisted_id(None)
