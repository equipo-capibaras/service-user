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

from .util import (
    UUID4Validator,
    class_route,
    error_response,
    is_valid_uuid4,
    json_response,
    requires_token,
    validation_error_response,
)

blp = Blueprint('Users', __name__)

USER_NOT_FOUND = 'User not found'


def user_to_dict(user: User) -> dict[str, Any]:
    return {
        'id': user.id,
        'clientId': user.client_id,
        'name': user.name,
        'email': user.email,
    }


# Find by email validation class
@dataclass
class FindByEmailBody:
    email: str = field(metadata={'validate': [marshmallow.validate.Email(), marshmallow.validate.Length(min=1, max=60)]})


@class_route(blp, '/api/v1/users/me')
class UserInfo(MethodView):
    init_every_request = False

    @requires_token
    def get(self, token: dict[str, Any], user_repo: UserRepository = Provide[Container.user_repo]) -> Response:
        user = user_repo.get(user_id=token['sub'], client_id=token['cid'])

        if user is None:
            return error_response(USER_NOT_FOUND, 404)

        return json_response(user_to_dict(user), 200)


# Internal only
@class_route(blp, '/api/v1/users/<client_id>/<user_id>')
class RetrieveUser(MethodView):
    init_every_request = False

    def get(self, client_id: str, user_id: str, user_repo: UserRepository = Provide[Container.user_repo]) -> Response:
        if not is_valid_uuid4(client_id):
            return error_response('Invalid client ID.', 400)

        if not is_valid_uuid4(user_id):
            return error_response('Invalid user ID.', 400)

        user = user_repo.get(user_id=user_id, client_id=client_id)

        if user is None:
            return error_response(USER_NOT_FOUND, 404)

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
            return error_response('A user with the email already exists.', 409)

        return json_response(user_to_dict(user), 201)


# Internal only
@class_route(blp, '/api/v1/users/detail')
class FindUser(MethodView):
    init_every_request = False

    def post(self, user_repo: UserRepository = Provide[Container.user_repo]) -> Response:
        # Parse request body
        find_schema = marshmallow_dataclass.class_schema(FindByEmailBody)()
        req_json = request.get_json(silent=True)
        if req_json is None:
            return error_response('The request body could not be parsed as valid JSON.', 400)

        try:
            data: FindByEmailBody = find_schema.load(req_json)
        except ValidationError as err:
            return validation_error_response(err)

        # Find user by email
        user = user_repo.find_by_email(data.email)

        if user is None:
            return error_response(USER_NOT_FOUND, 404)

        return json_response(user_to_dict(user), 200)
