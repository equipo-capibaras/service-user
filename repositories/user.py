from models import User


class UserRepository:
    def get(self, user_id: str, client_id: str) -> User | None:
        raise NotImplementedError  # pragma: no cover

    def find_by_email(self, email: str) -> User | None:
        raise NotImplementedError  # pragma: no cover

    def create(self, user: User) -> None:
        raise NotImplementedError  # pragma: no cover

    def delete_all(self) -> None:
        raise NotImplementedError  # pragma: no cover
