from typing import cast
from unittest.mock import Mock

from unittest_parametrize import ParametrizedTestCase, parametrize

import demo
from app import create_app
from repositories import UserRepository


class TestReset(ParametrizedTestCase):
    API_ENDPOINT = '/api/v1/reset/user'

    def setUp(self) -> None:
        self.app = create_app()
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        self.app.container.unwire()

    @parametrize(
        'arg,expected',
        [
            (None, False),
            ('true', True),
            ('false', False),
            ('foo', False),
        ],
    )
    def test_reset(self, arg: str | None, expected: bool) -> None:  # noqa: FBT001
        user_repo_mock = Mock(UserRepository)
        call_order = []

        cast(Mock, user_repo_mock.delete_all).side_effect = lambda: call_order.append('user:delete_all')
        cast(Mock, user_repo_mock.create).side_effect = lambda _x: call_order.append('user:create')

        with self.app.container.user_repo.override(user_repo_mock):
            resp = self.client.post(self.API_ENDPOINT + (f'?demo={arg}' if arg is not None else ''))

        cast(Mock, user_repo_mock.delete_all).assert_called_once()

        if not expected:
            self.assertEqual(call_order, ['user:delete_all'])
        else:
            self.assertEqual(call_order, ['user:delete_all'] + ['user:create'] * len(demo.users))

        self.assertEqual(resp.status_code, 200)
