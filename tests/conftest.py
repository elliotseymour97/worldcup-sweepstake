import pytest
from app import create_app
from models import db as _db, Player, Country, Match


@pytest.fixture(scope='session')
def app():
    application = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SECRET_KEY': 'test-secret',
        'ADMIN_PASSWORD': 'testpass',
        'FOOTBALL_DATA_API_KEY': '',
    })
    ctx = application.app_context()
    ctx.push()
    yield application
    ctx.pop()


@pytest.fixture(scope='session')
def db(app):
    return _db


@pytest.fixture(autouse=True)
def clean_db(db):
    yield
    Match.query.delete()
    Country.query.update({'player_id': None})
    Player.query.delete()
    db.session.commit()


@pytest.fixture
def client(app):
    with app.test_client() as c:
        yield c


@pytest.fixture
def make_country(db):
    _counter = [0]
    def _make(tier=1, name=None):
        _counter[0] += 1
        c = Country(
            name=name or f'TestCountry{_counter[0]}',
            code='TC',
            api_name=name or f'TestCountry{_counter[0]}',
            group_name='Z',
            tier=tier,
            fifa_ranking=99,
        )
        db.session.add(c)
        db.session.flush()
        return c
    return _make


@pytest.fixture
def make_match(db):
    def _make(home, away, home_score, away_score,
              stage='GROUP_STAGE', status='FINISHED'):
        m = Match(
            home_team_id=home.id,
            away_team_id=away.id,
            home_team_name=home.name,
            away_team_name=away.name,
            home_score=home_score,
            away_score=away_score,
            stage=stage,
            status=status,
        )
        db.session.add(m)
        db.session.flush()
        db.session.expire(home)
        db.session.expire(away)
        return m
    return _make


@pytest.fixture
def make_player(db):
    def _make(name):
        p = Player(name=name)
        db.session.add(p)
        db.session.flush()
        return p
    return _make
