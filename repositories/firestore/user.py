import contextlib
import logging
from collections.abc import Generator
from dataclasses import asdict
from typing import Any, cast

import dacite
from google.api_core.exceptions import AlreadyExists
from google.cloud.firestore import Client as FirestoreClient  # type: ignore[import-untyped]
from google.cloud.firestore import transactional
from google.cloud.firestore_v1 import (
    CollectionReference,
    DocumentReference,
    DocumentSnapshot,
    Transaction,
)
from google.cloud.firestore_v1.base_query import FieldFilter
from google.cloud.firestore_v1.query_results import QueryResultsList

from models import User
from repositories import UserRepository
from repositories.errors import DuplicateEmailError


class FirestoreUserRepository(UserRepository):
    def __init__(self, database: str) -> None:
        self.db = FirestoreClient(database=database)
        self.logger = logging.getLogger(self.__class__.__name__)

    def doc_to_user(self, doc: DocumentSnapshot) -> User:
        return dacite.from_dict(
            data_class=User,
            data={
                **cast(dict[str, Any], doc.to_dict()),
                'id': doc.id,
                'client_id': cast(
                    DocumentReference, cast(CollectionReference, cast(DocumentReference, doc.reference).parent).parent
                ).id,
            },
        )

    def get(self, user_id: str, client_id: str) -> User | None:
        client_ref = self.db.collection('clients').document(client_id)
        user_ref = cast(CollectionReference, client_ref.collection('users')).document(user_id)
        doc = user_ref.get()

        if not doc.exists:
            return None

        return self.doc_to_user(doc)

    def _find_by_email(self, email: str, transaction: Transaction | None = None) -> DocumentSnapshot | None:
        docs: QueryResultsList[DocumentSnapshot] = (
            self.db.collection_group('users').where(filter=FieldFilter('email', '==', email)).get(transaction=transaction)  # type: ignore[no-untyped-call]
        )

        if len(docs) == 0:
            return None

        if len(docs) > 1:
            self.logger.error('Multiple users found with email %s', email)
            return None

        return docs[0]

    def find_by_email(self, email: str) -> User | None:
        doc = self._find_by_email(email)

        if doc is None:
            return None

        return self.doc_to_user(doc)

    def create(self, user: User) -> None:
        user_dict = asdict(user)
        del user_dict['id']
        del user_dict['client_id']

        client_ref = self.db.collection('clients').document(user.client_id)
        with contextlib.suppress(AlreadyExists):
            client_ref.create({})
        user_ref = cast(CollectionReference, client_ref.collection('users')).document(user.id)

        @transactional  # type: ignore[misc]
        def create_user_transaction(transaction: Transaction, user_dict: dict[str, Any]) -> None:
            if self._find_by_email(user_dict['email'], transaction) is not None:
                raise DuplicateEmailError(user_dict['email'])

            transaction.create(user_ref, user_dict)

        create_user_transaction(self.db.transaction(), user_dict)

    def delete_all(self) -> None:
        stream: Generator[DocumentSnapshot, None, None] = self.db.collection_group('users').stream()
        for e in stream:
            cast(DocumentReference, e.reference).delete()
