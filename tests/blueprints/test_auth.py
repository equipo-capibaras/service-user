import json
from typing import Any, cast
from unittest.mock import Mock

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from faker import Faker
from passlib.hash import pbkdf2_sha256
from unittest_parametrize import ParametrizedTestCase, parametrize
from werkzeug.test import TestResponse

from app import create_app
from models import User
from repositories import UserRepository


class TestAuth(ParametrizedTestCase):
    def setUp(self) -> None:
        self.faker = Faker()
        self.app = create_app()
        self.jwt_issuer = self.faker.uri()
        jwt_private_key = Ed25519PrivateKey.generate()
        self.jwt_public_key = jwt_private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        self.app.container.config.jwt.issuer.override(self.jwt_issuer)
        self.app.container.config.jwt.private_key.override(
            jwt_private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )

        self.client = self.app.test_client()

    def tearDown(self) -> None:
        self.app.container.unwire()

    def call_api(self, body: dict[str, Any] | str) -> TestResponse:
        return self.client.post(
            '/api/v1/auth/user',
            data=body if isinstance(body, str) else json.dumps(body),
            content_type='application/json',
        )

    def test_auth_invalid_json(self) -> None:
        user_repo_mock = Mock(UserRepository)
        with self.app.container.user_repo.override(user_repo_mock):
            resp = self.call_api('invalid json')

        self.assertEqual(resp.status_code, 400)
        resp_data = json.loads(resp.get_data())

        self.assertEqual(resp_data['code'], 400)
        self.assertEqual(resp_data['message'], 'The request body could not be parsed as valid JSON.')

    @parametrize(
        'field',
        [
            ('username',),
            ('password',),
        ],
    )
    def test_auth_missing_field(self, field: str) -> None:
        login_data = {
            'username': self.faker.email(),
            'password': self.faker.password(),
        }

        del login_data[field]

        user_repo_mock = Mock(UserRepository)
        with self.app.container.user_repo.override(user_repo_mock):
            resp = self.call_api(login_data)

        self.assertEqual(resp.status_code, 400)
        resp_data = json.loads(resp.get_data())

        self.assertEqual(resp_data['code'], 400)
        self.assertEqual(resp_data['message'], f'Invalid value for {field}: Missing data for required field.')

    def test_login_invalid_credentials(self) -> None:
        login_data = {
            'username': self.faker.email(),
            'password': self.faker.password(),
        }

        user_repo_mock = Mock(UserRepository)
        cast(Mock, user_repo_mock.find_by_email).return_value = None
        with self.app.container.user_repo.override(user_repo_mock):
            resp = self.call_api(login_data)

        cast(Mock, user_repo_mock.find_by_email).assert_called_once_with(login_data['username'])

        self.assertEqual(resp.status_code, 401)
        resp_data = json.loads(resp.get_data())

        self.assertEqual(resp_data['code'], 401)
        self.assertEqual(resp_data['message'], 'Invalid username or password.')

    def test_login_valid_credentials(self) -> None:
        password = self.faker.password()

        user = User(
            id=cast(str, self.faker.uuid4()),
            client_id=cast(str, self.faker.uuid4()),
            name=self.faker.name(),
            email=self.faker.email(),
            password=pbkdf2_sha256.hash(password),
        )

        login_data = {
            'username': user.email,
            'password': password,
        }

        user_repo_mock = Mock(UserRepository)

        cast(Mock, user_repo_mock.find_by_email).return_value = user
        with self.app.container.user_repo.override(user_repo_mock):
            resp = self.call_api(login_data)

        cast(Mock, user_repo_mock.find_by_email).assert_called_once_with(login_data['username'])

        self.assertEqual(resp.status_code, 200)
        resp_data = json.loads(resp.get_data())

        self.assertIn('token', resp_data)
        decoded_token = jwt.decode(resp_data['token'], self.jwt_public_key, algorithms=['EdDSA'], audience='user')
        self.assertEqual(decoded_token['iss'], self.jwt_issuer)
        self.assertEqual(decoded_token['sub'], user.id)
        self.assertEqual(decoded_token['cid'], user.client_id)
        self.assertEqual(decoded_token['role'], 'user')
        self.assertEqual(decoded_token['aud'], 'user')
        self.assertEqual(decoded_token['email'], user.email)
