import os
from dataclasses import asdict
from typing import cast
from unittest import skipUnless

import requests
from faker import Faker
from google.cloud.firestore import Client as FirestoreClient  # type: ignore[import-untyped]
from google.cloud.firestore_v1 import DocumentReference
from passlib.hash import pbkdf2_sha256
from unittest_parametrize import ParametrizedTestCase, parametrize

from models import User
from repositories.errors import DuplicateEmailError
from repositories.firestore import FirestoreUserRepository

FIRESTORE_DATABASE = '(default)'


@skipUnless('FIRESTORE_EMULATOR_HOST' in os.environ, 'Firestore emulator not available')
class TestUser(ParametrizedTestCase):
    def setUp(self) -> None:
        self.faker = Faker()

        # Reset Firestore emulator before each test
        requests.delete(
            f'http://{os.environ["FIRESTORE_EMULATOR_HOST"]}/emulator/v1/projects/google-cloud-firestore-emulator/databases/{FIRESTORE_DATABASE}/documents',
            timeout=5,
        )

        self.repo = FirestoreUserRepository(FIRESTORE_DATABASE)
        self.client = FirestoreClient(database=FIRESTORE_DATABASE)

        self.emails = [self.faker.unique.email() for _ in range(4)]

    @parametrize(
        ('email_idx_map', 'find_idx', 'expected'),
        [
            ({0: 0, 1: 1, 2: 2}, 0, 0),  # User found
            ({0: 0, 1: 1, 2: 2}, 3, None),  # User not found
            ({0: 0, 1: 0, 2: 2}, 0, None),  # Multiple users found
        ],
    )
    def test_find_by_email(self, email_idx_map: dict[int, int], find_idx: int, expected: int | None) -> None:
        client_id = cast(str, self.faker.uuid4())
        self.client.collection('clients').document(client_id).set({})

        users: list[User] = []
        for idx, _ in enumerate(range(3)):
            user = User(
                id=cast(str, self.faker.uuid4()),
                client_id=client_id,
                name=self.faker.name(),
                email=self.emails[email_idx_map[idx]],
                password=pbkdf2_sha256.hash(self.faker.password()),
            )
            users.append(user)
            user_dict = asdict(user)
            del user_dict['id']
            del user_dict['client_id']
            self.client.collection('clients').document(client_id).collection('users').document(user.id).set(user_dict)

        duplicate_emails = len(set(email_idx_map.values())) != len(email_idx_map)

        if duplicate_emails:
            with self.assertLogs() as cm:
                user_db = self.repo.find_by_email(self.emails[find_idx])
        else:
            with self.assertNoLogs():
                user_db = self.repo.find_by_email(self.emails[find_idx])

        if expected is not None:
            self.assertIsNotNone(user_db)
            self.assertEqual(user_db, users[expected])
        else:
            self.assertIsNone(user_db)

            if duplicate_emails:
                self.assertEqual(cm.records[0].message, f'Multiple users found with email {self.emails[find_idx]}')
                self.assertEqual(cm.records[0].levelname, 'ERROR')

    def test_get_found(self) -> None:
        client_id = cast(str, self.faker.uuid4())
        self.client.collection('clients').document(client_id).set({})

        user = User(
            id=cast(str, self.faker.uuid4()),
            client_id=client_id,
            name=self.faker.name(),
            email=self.faker.unique.email(),
            password=pbkdf2_sha256.hash(self.faker.password()),
        )
        user_dict = asdict(user)
        del user_dict['id']
        del user_dict['client_id']
        self.client.collection('clients').document(client_id).collection('users').document(user.id).set(user_dict)

        user_db = self.repo.get(user.id, client_id)

        self.assertEqual(user_db, user)

    def test_get_not_found(self) -> None:
        client_id = cast(str, self.faker.uuid4())
        user_id = cast(str, self.faker.uuid4())
        user = self.repo.get(user_id, client_id)

        self.assertIsNone(user)

    def test_create(self) -> None:
        client_id = cast(str, self.faker.uuid4())
        self.client.collection('clients').document(client_id).set({})

        user = User(
            id=cast(str, self.faker.uuid4()),
            client_id=client_id,
            name=self.faker.name(),
            email=self.faker.unique.email(),
            password=pbkdf2_sha256.hash(self.faker.password()),
        )

        self.repo.create(user)

        user_ref = cast(
            DocumentReference,
            self.client.collection('clients').document(client_id).collection('users').document(user.id),
        )
        doc = user_ref.get()

        self.assertTrue(doc.exists)

        user_dict = asdict(user)
        del user_dict['id']
        del user_dict['client_id']
        self.assertEqual(doc.to_dict(), user_dict)

    def test_create_duplicate(self) -> None:
        client_id = cast(str, self.faker.uuid4())
        self.client.collection('clients').document(client_id).set({})

        user1 = User(
            id=cast(str, self.faker.uuid4()),
            client_id=client_id,
            name=self.faker.name(),
            email=self.faker.unique.email(),
            password=pbkdf2_sha256.hash(self.faker.password()),
        )
        user_dict = asdict(user1)
        del user_dict['id']
        del user_dict['client_id']
        self.client.collection('clients').document(client_id).collection('users').document(user1.id).set(user_dict)

        user2 = User(
            id=cast(str, self.faker.uuid4()),
            client_id=client_id,
            name=self.faker.name(),
            email=user1.email,
            password=pbkdf2_sha256.hash(self.faker.password()),
        )

        with self.assertRaises(DuplicateEmailError) as context:
            self.repo.create(user2)

        self.assertEqual(str(context.exception), f"A user with the email '{user2.email}' already exists.")

        user_ref = cast(
            DocumentReference,
            self.client.collection('clients').document(client_id).collection('users').document(user2.id),
        )
        doc = user_ref.get()
        self.assertFalse(doc.exists)

    def test_delete_all(self) -> None:
        users: list[User] = []

        # Add 3 clients with 3 users each to Firestore
        for _ in range(3):
            client_id = cast(str, self.faker.uuid4())
            self.client.collection('clients').document(client_id).set({})

            for _ in range(3):
                user = User(
                    id=cast(str, self.faker.uuid4()),
                    client_id=client_id,
                    name=self.faker.name(),
                    email=self.faker.unique.email(),
                    password=pbkdf2_sha256.hash(self.faker.password()),
                )
                users.append(user)
                user_dict = asdict(user)
                del user_dict['id']
                del user_dict['client_id']
                self.client.collection('clients').document(client_id).collection('users').document(user.id).set(user_dict)

        self.repo.delete_all()

        for user in users:
            user_ref = cast(
                DocumentReference,
                self.client.collection('clients').document(user.client_id).collection('users').document(user.id),
            )

            doc = user_ref.get()

            self.assertFalse(doc.exists)
