from typing import Any

from dependency_injector.wiring import Provide
from flask import Blueprint, Response
from flask.views import MethodView

from containers import Container
from repositories import UserRepository

from .util import class_route, error_response, json_response, requires_token

blp = Blueprint('Users', __name__)


@class_route(blp, '/api/v1/users/me')
class UserInfo(MethodView):
    init_every_request = False

    @requires_token
    def get(self, token: dict[str, Any], user_repo: UserRepository = Provide[Container.user_repo]) -> Response:
        user = user_repo.get(user_id=token['sub'], client_id=token['cid'])

        if user is None:
            return error_response('User not found', 404)

        user_data = {
            'id': user.id,
            'clientId': user.client_id,
            'name': user.name,
            'email': user.email,
        }

        return json_response(user_data, 200)
