"""In-memory user store.

A single module-level dict so every route in `routes/users/` sees the
same state. A real app swaps this for SQLAlchemy/SQLModel/etc. and
provides a session via `_scope.py`.
"""

from __future__ import annotations

from itertools import count

from msgspec import Struct


class User(Struct):
    id: int
    name: str
    email: str


_users: dict[int, User] = {}
_ids = count(1)


def all_users() -> list[User]:
    return list(_users.values())


def get_user(user_id: int) -> User | None:
    return _users.get(user_id)


def create_user(name: str, email: str) -> User:
    user = User(id=next(_ids), name=name, email=email)
    _users[user.id] = user
    return user


def update_user(user_id: int, *, name: str | None, email: str | None) -> User | None:
    existing = _users.get(user_id)
    if existing is None:
        return None
    updated = User(
        id=existing.id,
        name=name if name is not None else existing.name,
        email=email if email is not None else existing.email,
    )
    _users[user_id] = updated
    return updated


def delete_user(user_id: int) -> bool:
    return _users.pop(user_id, None) is not None
