from dependency_injector.wiring import Provide, inject
from flask import Blueprint, Response, request
from flask.views import MethodView

import demo
from containers import Container
from repositories import UserRepository

from .util import class_route, json_response

blp = Blueprint('Reset database', __name__)


@class_route(blp, '/api/v1/reset/user')
class ResetDB(MethodView):
    init_every_request = False

    @inject
    def post(
        self,
        user_repo: UserRepository = Provide[Container.user_repo],
    ) -> Response:
        user_repo.delete_all()

        if request.args.get('demo', 'false') == 'true':
            for user in demo.users:
                user_repo.create(user)

        return json_response({'status': 'Ok'}, 200)
