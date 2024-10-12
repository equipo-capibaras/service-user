from typing import cast

import responses
from faker import Faker
from requests import HTTPError
from unittest_parametrize import ParametrizedTestCase, parametrize

from models import Client
from repositories.rest import RestClientRepository


class TestClient(ParametrizedTestCase):
    def setUp(self) -> None:
        self.faker = Faker()
        self.base_url = self.faker.url().rstrip('/')
        self.repo = RestClientRepository(self.base_url)

    def test_get_existing(self) -> None:
        client = Client(
            id=cast(str, self.faker.uuid4()),
            name=self.faker.company(),
        )
        client_id = cast(str, self.faker.uuid4())

        with responses.RequestsMock() as rsps:
            rsps.get(
                f'{self.base_url}/api/v1/clients/{client_id}',
                json={
                    'id': client.id,
                    'name': client.name,
                },
            )

            client_repo = self.repo.get(client_id)

        self.assertEqual(client_repo, client)

    def test_get_not_found(self) -> None:
        client_id = cast(str, self.faker.uuid4())

        with responses.RequestsMock() as rsps:
            rsps.get(f'{self.base_url}/api/v1/clients/{client_id}', status=404)

            client_repo = self.repo.get(client_id)

        self.assertIsNone(client_repo)

    @parametrize(
        'status',
        [
            (500,),
            (201,),
        ],
    )
    def test_get_error(self, status: int) -> None:
        client_id = cast(str, self.faker.uuid4())

        with responses.RequestsMock() as rsps:
            rsps.get(f'{self.base_url}/api/v1/clients/{client_id}', status=status)

            with self.assertRaises(HTTPError):
                self.repo.get(client_id)
