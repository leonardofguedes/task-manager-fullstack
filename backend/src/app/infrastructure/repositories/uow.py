from sqlalchemy.orm import Session


class SqlUnitOfWork:
    """UnitOfWork adapter: the use case decides when the transaction is committed."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def commit(self) -> None:
        self._session.commit()
