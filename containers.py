from dependency_injector import providers
from dependency_injector.containers import DeclarativeContainer, WiringConfiguration

from repositories.firestore import FirestoreUserRepository


class Container(DeclarativeContainer):
    wiring_config = WiringConfiguration(packages=['blueprints'])
    config = providers.Configuration()

    user_repo = providers.ThreadSafeSingleton(FirestoreUserRepository, database=config.firestore.database)
