class CeleryNotificationDispatcher:
    """NotificationDispatcher adapter: enqueues the job on Redis for the Celery worker."""

    def task_assigned(self, task_id: int, assignee_id: int) -> None:
        # Imported lazily so the API process only builds the Celery app when it first enqueues.
        from app.infrastructure.worker.jobs import send_assignment_notification

        send_assignment_notification.delay(task_id, assignee_id)
