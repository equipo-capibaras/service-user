import uuid
from dataclasses import dataclass, field
from typing import Any

import marshmallow.validate
import marshmallow_dataclass
from dependency_injector.wiring import Provide
from flask import Blueprint, Response, request
from flask.views import MethodView
from marshmallow import ValidationError
from passlib.hash import pbkdf2_sha256

from containers import Container
from models import User
from repositories import ClientRepository, UserRepository
from repositories.errors import DuplicateEmailError

from .util import UUID4Validator, class_route, error_response, json_response, requires_token, validation_error_response

blp = Blueprint('Users', __name__)


def user_to_dict(user: User) -> dict[str, Any]:
    return {
        'id': user.id,
        'clientId': user.client_id,
        'name': user.name,
        'email': user.email,
    }


@class_route(blp, '/api/v1/users/me')
class UserInfo(MethodView):
    init_every_request = False

    @requires_token
    def get(self, token: dict[str, Any], user_repo: UserRepository = Provide[Container.user_repo]) -> Response:
        user = user_repo.get(user_id=token['sub'], client_id=token['cid'])

        if user is None:
            return error_response('User not found', 404)

        return json_response(user_to_dict(user), 200)


@dataclass
class RegisterBody:
    clientId: str = field(metadata={'validate': UUID4Validator()})  # noqa: N815
    name: str = field(metadata={'validate': marshmallow.validate.Length(min=1, max=60)})
    email: str = field(metadata={'validate': [marshmallow.validate.Email(), marshmallow.validate.Length(min=1, max=60)]})
    password: str = field(metadata={'validate': marshmallow.validate.Length(min=8)})


@class_route(blp, '/api/v1/users')
class UserRegister(MethodView):
    init_every_request = False

    def post(
        self,
        user_repo: UserRepository = Provide[Container.user_repo],
        client_repo: ClientRepository = Provide[Container.client_repo],
    ) -> Response:
        auth_schema = marshmallow_dataclass.class_schema(RegisterBody)()
        req_json = request.get_json(silent=True)
        if req_json is None:
            return error_response('The request body could not be parsed as valid JSON.', 400)

        try:
            data: RegisterBody = auth_schema.load(req_json)
        except ValidationError as err:
            return validation_error_response(err)

        if client_repo.get(data.clientId) is None:
            return error_response('Invalid value for clientId: Client does not exist.', 400)

        user = User(
            id=str(uuid.uuid4()),
            client_id=data.clientId,
            name=data.name,
            email=data.email,
            password=pbkdf2_sha256.hash(data.password),
        )

        try:
            user_repo.create(user)
        except DuplicateEmailError:
            return error_response('A user with the email already exists.', 400)

        return json_response(user_to_dict(user), 201)
