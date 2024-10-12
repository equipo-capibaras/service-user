from dependency_injector import providers
from dependency_injector.containers import DeclarativeContainer, WiringConfiguration

from repositories.firestore import FirestoreUserRepository
from repositories.rest import RestClientRepository


class Container(DeclarativeContainer):
    wiring_config = WiringConfiguration(packages=['blueprints'])
    config = providers.Configuration()

    client_repo = providers.ThreadSafeSingleton(
        RestClientRepository,
        base_url=config.svc.client.url,
        token_provider=config.svc.client.token_provider,
    )
    user_repo = providers.ThreadSafeSingleton(
        FirestoreUserRepository,
        database=config.firestore.database,
    )
