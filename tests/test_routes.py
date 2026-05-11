import pytest
from draw import run_draw


class TestPublicRoutes:

    def test_league_page(self, client):
        assert client.get('/').status_code == 200

    def test_scores_page(self, client):
        assert client.get('/scores').status_code == 200

    def test_teams_page(self, client):
        assert client.get('/teams').status_code == 200

    def test_rules_page(self, client):
        assert client.get('/rules').status_code == 200

    def test_unknown_route_returns_404(self, client):
        assert client.get('/does-not-exist').status_code == 404


class TestAdminAuth:

    def test_admin_redirects_to_login_when_unauthenticated(self, client):
        resp = client.get('/admin')
        assert resp.status_code == 302
        assert '/admin/login' in resp.headers['Location']

    def test_login_page_loads(self, client):
        assert client.get('/admin/login').status_code == 200

    def test_wrong_password_shows_error(self, client):
        resp = client.post('/admin/login', data={'password': 'wrong'})
        assert resp.status_code == 200
        assert b'Incorrect' in resp.data

    def test_correct_password_redirects_to_admin(self, client):
        resp = client.post('/admin/login', data={'password': 'testpass'})
        assert resp.status_code == 302
        assert '/admin' in resp.headers['Location']

    def test_admin_accessible_after_login(self, client):
        client.post('/admin/login', data={'password': 'testpass'})
        assert client.get('/admin').status_code == 200

    def test_logout_clears_session(self, client):
        client.post('/admin/login', data={'password': 'testpass'})
        client.post('/admin/logout')
        resp = client.get('/admin')
        assert resp.status_code == 302

    def test_already_logged_in_skips_login_page(self, client):
        client.post('/admin/login', data={'password': 'testpass'})
        resp = client.get('/admin/login')
        assert resp.status_code == 302  # redirects to /admin


class TestAdminActions:

    def _login(self, client):
        client.post('/admin/login', data={'password': 'testpass'})

    def test_draw_requires_six_names(self, client):
        self._login(client)
        resp = client.post('/admin/draw',
                           data={f'player{i}': f'P{i}' for i in range(1, 5)},
                           follow_redirects=True)
        assert b'required' in resp.data.lower() or b'6' in resp.data

    def test_valid_draw_shows_success(self, client):
        self._login(client)
        data = {f'player{i}': name for i, name in
                enumerate(['Jake', 'George', 'Ben', 'Lewis', 'Tim', 'Elliot'], 1)}
        resp = client.post('/admin/draw', data=data, follow_redirects=True)
        assert resp.status_code == 200

    def test_reset_clears_draw(self, client, db):
        self._login(client)
        data = {f'player{i}': name for i, name in
                enumerate(['Jake', 'George', 'Ben', 'Lewis', 'Tim', 'Elliot'], 1)}
        client.post('/admin/draw', data=data)
        resp = client.post('/admin/reset', follow_redirects=True)
        assert resp.status_code == 200
        from models import Player
        assert Player.query.count() == 0


class TestModels:

    def test_match_goals_property_empty(self, make_country, make_match):
        home = make_country()
        away = make_country()
        match = make_match(home, away, 1, 0)
        assert match.goals == []

    def test_match_goals_property_parses_json(self, db, make_country, make_match):
        import json
        home = make_country()
        away = make_country()
        match = make_match(home, away, 1, 0)
        match.goals_json = json.dumps([
            {'minute': '15', 'scorer': 'Neymar', 'is_home': True, 'type': 'REGULAR'},
            {'minute': '67', 'scorer': 'Vinicius', 'is_home': True, 'type': 'REGULAR'},
        ])
        db.session.flush()
        assert len(match.goals) == 2
        assert match.goals[0]['scorer'] == 'Neymar'

    def test_match_red_cards_filters_bookings(self, db, make_country, make_match):
        import json
        home = make_country()
        away = make_country()
        match = make_match(home, away, 1, 0)
        match.bookings_json = json.dumps([
            {'minute': 34, 'player': 'Messi', 'is_home': False, 'card': 'YELLOW_CARD'},
            {'minute': 78, 'player': 'Ramos', 'is_home': True,  'card': 'RED_CARD'},
        ])
        db.session.flush()
        assert len(match.red_cards) == 1
        assert match.red_cards[0]['player'] == 'Ramos'

    def test_country_multipliers(self, make_country):
        assert make_country(tier=1).multiplier == 1.0
        assert make_country(tier=2).multiplier == 1.25
        assert make_country(tier=3).multiplier == 1.5
        assert make_country(tier=4).multiplier == 1.75
