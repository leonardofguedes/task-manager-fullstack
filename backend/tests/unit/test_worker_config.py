from app.infrastructure.worker.jobs import scan_overdue_tasks, send_assignment_notification


def test_assignment_job_is_acked_early_so_it_is_never_redelivered() -> None:
    # Re-running it after a crash would duplicate the notification: at-most-once is the choice.
    assert send_assignment_notification.acks_late is False


def test_overdue_scan_is_acked_late_because_it_is_safe_to_rerun() -> None:
    assert scan_overdue_tasks.acks_late is True
