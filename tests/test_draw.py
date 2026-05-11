import pytest
from draw import run_draw
from models import Player, Country


def _run(names):
    return run_draw(names)


class TestDraw:

    def test_requires_exactly_six_names(self):
        with pytest.raises(ValueError, match='6'):
            run_draw(['Alice', 'Bob', 'Charlie'])

    def test_empty_names_excluded(self):
        with pytest.raises(ValueError, match='6'):
            run_draw(['Alice', 'Bob', '', '', '', ''])

    def test_creates_six_players(self, db):
        run_draw(['Alice', 'Bob', 'Charlie', 'Dave', 'Eve', 'Frank'])
        assert Player.query.count() == 6

    def test_each_player_gets_eight_countries(self, db):
        players = run_draw(['Alice', 'Bob', 'Charlie', 'Dave', 'Eve', 'Frank'])
        for player in players:
            assert len(player.countries) == 8

    def test_each_player_gets_two_per_tier(self, db):
        players = run_draw(['Alice', 'Bob', 'Charlie', 'Dave', 'Eve', 'Frank'])
        for player in players:
            for tier in range(1, 5):
                tier_countries = [c for c in player.countries if c.tier == tier]
                assert len(tier_countries) == 2, (
                    f'{player.name} has {len(tier_countries)} tier-{tier} countries, expected 2'
                )

    def test_all_countries_assigned(self, db):
        run_draw(['Alice', 'Bob', 'Charlie', 'Dave', 'Eve', 'Frank'])
        unassigned = Country.query.filter_by(player_id=None).count()
        assert unassigned == 0

    def test_rerun_replaces_previous_draw(self, db):
        run_draw(['Alice', 'Bob', 'Charlie', 'Dave', 'Eve', 'Frank'])
        run_draw(['P1', 'P2', 'P3', 'P4', 'P5', 'P6'])
        assert Player.query.count() == 6
        assert Player.query.filter_by(name='Alice').first() is None

    def test_strips_whitespace_from_names(self, db):
        players = run_draw(['  Alice  ', 'Bob', 'Charlie', 'Dave', 'Eve', 'Frank'])
        names = [p.name for p in players]
        assert 'Alice' in names
