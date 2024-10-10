from models import User

# Universo Móvel
ID_UNIVERSO = 'acfa53b4-58f3-46e8-809b-19ef52b437ed'

users_universo = [
    User(
        id='46f94cd1-8494-4e96-b308-80d7705868be',
        client_id=ID_UNIVERSO,
        name='Rafael Almeida',
        email='r.almeida@example.org',
        password='$pbkdf2-sha256$29000$1lpLSWmtlTKm1JpTihFCaA$eS5gFesJgpzCJZsKlxmWwqlSEDwuXFLFTHwe41a0YAI',  # noqa: S106
    ),
    User(
        id='32c60b97-e136-4e27-9488-6f996e466909',
        client_id=ID_UNIVERSO,
        name='Beatriz Souza',
        email='beatriz.s@example.org',
        password='$pbkdf2-sha256$29000$.b93TumdE8KYs1ZK6f3fmw$UgzJRrCh3amQKccm9GXiTUo/zNaWk/b6gLzMoTheYzI',  # noqa: S106
    ),
    User(
        id='c1a1fb0f-e9d0-47ba-b731-539cf65e1db0',
        client_id=ID_UNIVERSO,
        name='Lucas Henrique Santos',
        email='lucas.hs@example.org',
        password='$pbkdf2-sha256$29000$MCbEWEvpPWdMCcHY.x9jzA$jNVk1HcpKEjNLcxWmctuNH/7f1F6L4J85XmE5DoLy3U',  # noqa: S106
    ),
]

# GlobalCom
ID_GLOBALCOM = '22128c04-0c2c-4633-8317-0fffd552f7a6'

users_globalcom = [
    User(
        id='08c3ce3a-cd26-4c38-a6b2-d4cce508489f',
        client_id=ID_GLOBALCOM,
        name='Santiago Fernández',
        email='santiago@example.net',
        password='$pbkdf2-sha256$29000$LEWIMYbQurcWojTG2HtPaQ$0t3OnIw8VTwU8FBQK8dql7SzP8uB5/YWRHeHqt29TmA',  # noqa: S106
    ),
    User(
        id='f88f7ac7-c15f-4ff2-8ae8-7375b7b2f8db',
        client_id=ID_GLOBALCOM,
        name='Valentina López',
        email='valentina@example.net',
        password='$pbkdf2-sha256$29000$e.99z7nXutfaew/h/D/nHA$9yT9d4Wig.OwcUWsGA6qwNo.zW4lCYoAwJ9Xq3g4ajQ',  # noqa: S106
    ),
    User(
        id='26508d6b-d2ef-45da-a8e6-de44b3166266',
        client_id=ID_GLOBALCOM,
        name='Mateo González',
        email='mateo@example.net',
        password='$pbkdf2-sha256$29000$3htjbM055xxjrDWm9J6TMg$8grxvR8F7d0XK8t./x4UyE203Tpr.DHHIKttQHvlpG0',  # noqa: S106
    ),
]

# Gigatel
ID_GIGATEL = '9a652818-342e-4771-84cf-39c20a29264d'

users_gigatel = [
    User(
        id='e7bcf651-c7d7-4dfa-9633-14598673faff',
        client_id=ID_GIGATEL,
        name='Juan Carlos Rodríguez',
        email='juan.rodriguez@example.com',
        password='$pbkdf2-sha256$29000$H8MYQ0ipFcJY653TGmNsTQ$alhrArnPC45bFk/A4MgUlJguVQaOEDD847ko.Za7Mpw',  # noqa: S106
    ),
    User(
        id='b713f559-cae5-4db3-992a-d3553fb25000',
        client_id=ID_GIGATEL,
        name='María Fernanda Gómez',
        email='maria.gomez@example.com',
        password='$pbkdf2-sha256$29000$iTEmxJizVkqp9V4rBQBgbA$VUy6t1.Kueb0Abk52OlmIoK.DjiferKUl0nkS1cbEn0',  # noqa: S106
    ),
    User(
        id='53dc1ea3-02a1-4766-bc7c-e30f9eb590f1',
        client_id=ID_GIGATEL,
        name='Andrés Felipe Martínez',
        email='andres.martinez@example.com',
        password='$pbkdf2-sha256$29000$REgppXQOIYTQem8NQehdaw$4.MzQ6Jd/9Fr6O5dpsgwPjolqsJg5AdrxUUlmz050MI',  # noqa: S106
    ),
]

users = users_universo + users_globalcom + users_gigatel
