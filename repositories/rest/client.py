import logging

import dacite
import requests

from models import Client
from repositories import ClientRepository


class RestClientRepository(ClientRepository):
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url
        self.logger = logging.getLogger(self.__class__.__name__)

    def get(self, client_id: str) -> Client | None:
        resp = requests.get(f'{self.base_url}/api/v1/clients/{client_id}', timeout=2)

        if resp.status_code == requests.codes.ok:
            return dacite.from_dict(data_class=Client, data=resp.json())

        if resp.status_code == requests.codes.not_found:
            return None

        resp.raise_for_status()

        raise requests.HTTPError('Unexpected response from server', response=resp)
