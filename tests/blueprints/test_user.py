import base64
import json
from typing import cast
from unittest.mock import Mock

from faker import Faker
from passlib.hash import pbkdf2_sha256
from unittest_parametrize import ParametrizedTestCase, parametrize
from werkzeug.test import TestResponse

from app import create_app
from models import User
from repositories import UserRepository


class TestUser(ParametrizedTestCase):
    INFO_API_URL = '/api/v1/users/me'

    def setUp(self) -> None:
        self.faker = Faker()
        self.app = create_app()
        self.client = self.app.test_client()

    def gen_token(self) -> dict[str, str]:
        return {
            'sub': cast(str, self.faker.uuid4()),
            'cid': cast(str, self.faker.uuid4()),
            'aud': 'user',
        }

    def call_info_api(self, token: dict[str, str] | None) -> TestResponse:
        if token is None:
            return self.client.get(self.INFO_API_URL)

        token_encoded = base64.urlsafe_b64encode(json.dumps(token).encode()).decode()
        return self.client.get(self.INFO_API_URL, headers={'X-Apigateway-Api-Userinfo': token_encoded})

    def test_info_no_token(self) -> None:
        resp = self.call_info_api(None)

        self.assertEqual(resp.status_code, 401)
        resp_data = json.loads(resp.get_data())

        self.assertEqual(resp_data, {'code': 401, 'message': 'Token is missing'})

    @parametrize(
        'missing_field',
        [
            ('sub',),
            ('cid',),
            ('aud',),
        ],
    )
    def test_info_token_missing_fields(self, missing_field: str) -> None:
        token = self.gen_token()
        del token[missing_field]
        resp = self.call_info_api(token)

        self.assertEqual(resp.status_code, 401)
        resp_data = json.loads(resp.get_data())

        self.assertEqual(resp_data, {'code': 401, 'message': f'{missing_field} is missing in token'})

    def test_info_user_not_found(self) -> None:
        token = self.gen_token()

        user_repo_mock = Mock(UserRepository)

        cast(Mock, user_repo_mock.get).return_value = None
        with self.app.container.user_repo.override(user_repo_mock):
            resp = self.call_info_api(token)

        self.assertEqual(resp.status_code, 404)
        resp_data = json.loads(resp.get_data())

        self.assertEqual(resp_data, {'code': 404, 'message': 'User not found'})

    def test_info_user_found(self) -> None:
        token = self.gen_token()

        user = User(
            id=token['sub'],
            client_id=token['cid'],
            name=self.faker.name(),
            email=self.faker.email(),
            password=pbkdf2_sha256.hash(self.faker.password()),
        )

        user_repo_mock = Mock(UserRepository)

        cast(Mock, user_repo_mock.get).return_value = user
        with self.app.container.user_repo.override(user_repo_mock):
            resp = self.call_info_api(token)

        self.assertEqual(resp.status_code, 200)
        resp_data = json.loads(resp.get_data())

        self.assertEqual(resp_data['id'], user.id)
        self.assertEqual(resp_data['clientId'], user.client_id)
        self.assertEqual(resp_data['name'], user.name)
        self.assertEqual(resp_data['email'], user.email)
