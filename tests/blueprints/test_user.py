import base64
import json
from typing import Any, cast
from unittest.mock import Mock

from faker import Faker
from passlib.hash import pbkdf2_sha256
from unittest_parametrize import ParametrizedTestCase, parametrize
from werkzeug.test import TestResponse

from app import create_app
from models import Client, User
from repositories import ClientRepository, UserRepository
from repositories.errors import DuplicateEmailError


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

    def call_register_api(self, body: dict[str, Any] | str) -> TestResponse:
        return self.client.post(
            '/api/v1/users',
            data=body if isinstance(body, str) else json.dumps(body),
            content_type='application/json',
        )

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

    def test_register_invalid_json(self) -> None:
        user_repo_mock = Mock(UserRepository)
        client_repo_mock = Mock(ClientRepository)
        with self.app.container.user_repo.override(user_repo_mock), self.app.container.client_repo.override(client_repo_mock):
            resp = self.call_register_api('invalid json')

        cast(Mock, user_repo_mock.get).assert_not_called()
        cast(Mock, user_repo_mock.create).assert_not_called()

        self.assertEqual(resp.status_code, 400)
        resp_data = json.loads(resp.get_data())

        self.assertEqual(resp_data['code'], 400)
        self.assertEqual(resp_data['message'], 'The request body could not be parsed as valid JSON.')

    @parametrize(
        'field',
        [
            ('clientId',),
            ('name',),
            ('email',),
            ('password',),
        ],
    )
    def test_register_missing_field(self, field: str) -> None:
        register_data = {
            'clientId': cast(str, self.faker.uuid4()),
            'name': self.faker.name(),
            'email': self.faker.email(),
            'password': self.faker.password(),
        }

        del register_data[field]

        user_repo_mock = Mock(UserRepository)
        client_repo_mock = Mock(ClientRepository)
        with self.app.container.user_repo.override(user_repo_mock), self.app.container.client_repo.override(client_repo_mock):
            resp = self.call_register_api(register_data)

        cast(Mock, user_repo_mock.get).assert_not_called()
        cast(Mock, user_repo_mock.create).assert_not_called()

        self.assertEqual(resp.status_code, 400)
        resp_data = json.loads(resp.get_data())

        self.assertEqual(resp_data['code'], 400)
        self.assertEqual(resp_data['message'], f'Invalid value for {field}: Missing data for required field.')

    @parametrize(
        ['field', 'error'],
        [
            ('clientId', 'Not a valid UUID.'),
            ('email', 'Not a valid email address.'),
        ],
    )
    def test_register_invalid_format(self, field: str, error: str) -> None:
        register_data = {
            'clientId': cast(str, self.faker.uuid4()),
            'name': self.faker.name(),
            'email': self.faker.email(),
            'password': self.faker.password(),
        }

        register_data[field] = self.faker.word()

        user_repo_mock = Mock(UserRepository)
        client_repo_mock = Mock(ClientRepository)
        with self.app.container.user_repo.override(user_repo_mock), self.app.container.client_repo.override(client_repo_mock):
            resp = self.call_register_api(register_data)

        cast(Mock, user_repo_mock.get).assert_not_called()
        cast(Mock, user_repo_mock.create).assert_not_called()

        self.assertEqual(resp.status_code, 400)
        resp_data = json.loads(resp.get_data())

        self.assertEqual(resp_data['code'], 400)
        self.assertEqual(resp_data['message'], f'Invalid value for {field}: {error}')

    def gen_register_data_with_bounds(self, field: str, length: int) -> dict[str, Any]:
        register_data = {
            'clientId': cast(str, self.faker.uuid4()),
            'name': self.faker.name(),
            'email': self.faker.email(),
            'password': self.faker.password(),
        }

        if field == 'email':
            register_data[field] = self.faker.email()
            register_data[field] += 'a' * (length - len(register_data[field]))
        else:
            register_data[field] = self.faker.pystr(min_chars=length, max_chars=length)

        return register_data

    @parametrize(
        ['field', 'length'],
        [
            ('name', 0),
            ('name', 61),
            ('email', 61),
            ('password', 7),
        ],
    )
    def test_register_bounds_fail(self, field: str, length: int) -> None:
        register_data = self.gen_register_data_with_bounds(field, length)

        user_repo_mock = Mock(UserRepository)
        client_repo_mock = Mock(ClientRepository)
        with self.app.container.user_repo.override(user_repo_mock), self.app.container.client_repo.override(client_repo_mock):
            resp = self.call_register_api(register_data)

        cast(Mock, user_repo_mock.get).assert_not_called()
        cast(Mock, user_repo_mock.create).assert_not_called()

        self.assertEqual(resp.status_code, 400)
        resp_data = json.loads(resp.get_data())

        self.assertEqual(resp_data['code'], 400)
        self.assertTrue(resp_data['message'].startswith(f'Invalid value for {field}:'))

    @parametrize(
        ['field', 'length'],
        [
            ('name', 1),
            ('name', 60),
            ('email', 60),
            ('password', 8),
        ],
    )
    def test_register_bounds_valid(self, field: str, length: int) -> None:
        register_data = self.gen_register_data_with_bounds(field, length)

        user_repo_mock = Mock(UserRepository)
        client_repo_mock = Mock(ClientRepository)
        cast(Mock, client_repo_mock.get).return_value = Client(id=register_data['clientId'], name=self.faker.company())
        with self.app.container.user_repo.override(user_repo_mock), self.app.container.client_repo.override(client_repo_mock):
            resp = self.call_register_api(register_data)

        cast(Mock, client_repo_mock.get).assert_called_once_with(register_data['clientId'])

        cast(Mock, user_repo_mock.create).assert_called_once()
        repo_user: User = cast(Mock, user_repo_mock.create).call_args[0][0]
        self.assertEqual(repo_user.client_id, register_data['clientId'])
        self.assertEqual(repo_user.name, register_data['name'])
        self.assertEqual(repo_user.email, register_data['email'])
        self.assertTrue(pbkdf2_sha256.verify(register_data['password'], repo_user.password))

        self.assertEqual(resp.status_code, 201)
        resp_data = json.loads(resp.get_data())

        self.assertEqual(resp_data['id'], repo_user.id)
        self.assertEqual(resp_data['clientId'], repo_user.client_id)
        self.assertEqual(resp_data['name'], repo_user.name)
        self.assertEqual(resp_data['email'], repo_user.email)

    def test_register_two_errors(self) -> None:
        register_data = {
            'clientId': cast(str, self.faker.uuid4()),
            'name': self.faker.name(),
            'email': self.faker.pystr(min_chars=61, max_chars=61),
            'password': self.faker.password(),
        }

        user_repo_mock = Mock(UserRepository)
        client_repo_mock = Mock(ClientRepository)
        cast(Mock, client_repo_mock.get).return_value = Client(id=register_data['clientId'], name=self.faker.company())
        with self.app.container.user_repo.override(user_repo_mock), self.app.container.client_repo.override(client_repo_mock):
            resp = self.call_register_api(register_data)

        cast(Mock, user_repo_mock.get).assert_not_called()
        cast(Mock, user_repo_mock.create).assert_not_called()

        self.assertEqual(resp.status_code, 400)
        resp_data = json.loads(resp.get_data())

        self.assertEqual(resp_data['code'], 400)
        self.assertEqual(
            resp_data['message'], 'Invalid value for email: Not a valid email address. Length must be between 1 and 60.'
        )

    def test_register_duplicate_email(self) -> None:
        register_data = {
            'clientId': cast(str, self.faker.uuid4()),
            'name': self.faker.name(),
            'email': self.faker.email(),
            'password': self.faker.password(),
        }

        user_repo_mock = Mock(UserRepository)
        cast(Mock, user_repo_mock.create).side_effect = DuplicateEmailError(register_data['email'])
        client_repo_mock = Mock(ClientRepository)
        cast(Mock, client_repo_mock.get).return_value = Client(id=register_data['clientId'], name=self.faker.company())
        with self.app.container.user_repo.override(user_repo_mock), self.app.container.client_repo.override(client_repo_mock):
            resp = self.call_register_api(register_data)

        cast(Mock, client_repo_mock.get).assert_called_once_with(register_data['clientId'])

        cast(Mock, user_repo_mock.create).assert_called_once()
        repo_user: User = cast(Mock, user_repo_mock.create).call_args[0][0]
        self.assertEqual(repo_user.email, register_data['email'])

        self.assertEqual(resp.status_code, 409)
        resp_data = json.loads(resp.get_data())

        self.assertEqual(resp_data['code'], 409)
        self.assertEqual(resp_data['message'], 'A user with the email already exists.')

    def test_register_invalid_client(self) -> None:
        register_data = {
            'clientId': cast(str, self.faker.uuid4()),
            'name': self.faker.name(),
            'email': self.faker.email(),
            'password': self.faker.password(),
        }

        user_repo_mock = Mock(UserRepository)
        client_repo_mock = Mock(ClientRepository)
        cast(Mock, client_repo_mock.get).return_value = None
        with self.app.container.user_repo.override(user_repo_mock), self.app.container.client_repo.override(client_repo_mock):
            resp = self.call_register_api(register_data)

        cast(Mock, client_repo_mock.get).assert_called_once_with(register_data['clientId'])

        cast(Mock, user_repo_mock.create).assert_not_called()

        self.assertEqual(resp.status_code, 400)
        resp_data = json.loads(resp.get_data())

        self.assertEqual(resp_data['code'], 400)
        self.assertEqual(resp_data['message'], 'Invalid value for clientId: Client does not exist.')
