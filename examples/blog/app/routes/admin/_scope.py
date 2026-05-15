"""Admin-tree scope: DB session + bearer-token verification.

Both providers are defined in `app.deps`; importing them here makes
them part of this `_scope.py`'s module namespace, which is how the file
router discovers them.
"""

from __future__ import annotations

from app.deps import current_admin, db_session  # noqa: F401  # discovered by name
