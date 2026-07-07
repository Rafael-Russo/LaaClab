"""Transitional re-export shim (removed in Task 8).

Keeps `from web.models import X` working while call sites migrate to the new
domain apps.
"""

from accounts.models import UserProfile  # noqa: F401
from alerts.models import Alert  # noqa: F401
from catalog.models import (  # noqa: F401
    Game,
    Genre,
    IngestCandidate,
    LibraryEntry,
    status_for,
)
from community.models import GameComment, Reply, Topic  # noqa: F401
