from dependency_injector import providers
from dependency_injector.containers import DeclarativeContainer, WiringConfiguration


class Container(DeclarativeContainer):
    wiring_config = WiringConfiguration(packages=['blueprints'])
    config = providers.Configuration()
