from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class NotificationKind(StrEnum):
    ASSIGNED = "assigned"
    OVERDUE = "overdue"


@dataclass
class Notification:
    id: int | None
    user_id: int
    task_id: int
    kind: NotificationKind
    message: str
    created_at: datetime
