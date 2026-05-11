import pytest
from points import match_points_for_country, country_stats, player_standings, STAGE_BONUS


class TestMatchPoints:

    def test_scheduled_match_scores_zero(self, make_country, make_match):
        home = make_country(tier=1)
        away = make_country(tier=2)
        match = make_match(home, away, 0, 0, status='SCHEDULED')
        assert match_points_for_country(match, home) == 0.0

    def test_win_group_stage_tier1(self, make_country, make_match):
        home = make_country(tier=1)
        away = make_country(tier=2)
        match = make_match(home, away, 2, 0)
        assert match_points_for_country(match, home) == 3.0  # 3 × 1.0 + 0

    def test_win_group_stage_tier4(self, make_country, make_match):
        home = make_country(tier=4)
        away = make_country(tier=1)
        match = make_match(home, away, 1, 0)
        assert match_points_for_country(match, home) == 5.25  # 3 × 1.75 + 0

    def test_win_group_stage_tier2(self, make_country, make_match):
        home = make_country(tier=2)
        away = make_country(tier=1)
        match = make_match(home, away, 3, 1)
        assert match_points_for_country(match, home) == 3.75  # 3 × 1.25 + 0

    def test_win_group_stage_tier3(self, make_country, make_match):
        home = make_country(tier=3)
        away = make_country(tier=1)
        match = make_match(home, away, 1, 0)
        assert match_points_for_country(match, home) == 4.5  # 3 × 1.5 + 0

    def test_away_win_scores_correctly(self, make_country, make_match):
        home = make_country(tier=1)
        away = make_country(tier=4)
        match = make_match(home, away, 0, 2)
        assert match_points_for_country(match, away) == 5.25  # 3 × 1.75 + 0

    def test_loss_scores_zero(self, make_country, make_match):
        home = make_country(tier=4)
        away = make_country(tier=1)
        match = make_match(home, away, 0, 1)
        assert match_points_for_country(match, home) == 0.0

    def test_draw_group_stage_scores(self, make_country, make_match):
        home = make_country(tier=2)
        away = make_country(tier=1)
        match = make_match(home, away, 1, 1)
        assert match_points_for_country(match, home) == 1.25  # 1 × 1.25 + 0

    def test_draw_knockout_scores_zero(self, make_country, make_match):
        home = make_country(tier=2)
        away = make_country(tier=1)
        match = make_match(home, away, 1, 1, stage='LAST_16')
        assert match_points_for_country(match, home) == 0.0

    def test_win_semifinal_stage_bonus(self, make_country, make_match):
        home = make_country(tier=1)
        away = make_country(tier=2)
        match = make_match(home, away, 1, 0, stage='SEMI_FINALS')
        assert match_points_for_country(match, home) == 7.0  # 3 × 1.0 + 4

    def test_win_final_stage_bonus(self, make_country, make_match):
        home = make_country(tier=3)
        away = make_country(tier=1)
        match = make_match(home, away, 1, 0, stage='FINAL')
        assert match_points_for_country(match, home) == 9.5  # 3 × 1.5 + 5

    def test_win_quarterfinal_stage_bonus(self, make_country, make_match):
        home = make_country(tier=4)
        away = make_country(tier=1)
        match = make_match(home, away, 1, 0, stage='QUARTER_FINALS')
        assert match_points_for_country(match, home) == 8.25  # 3 × 1.75 + 3

    @pytest.mark.parametrize('stage,bonus', STAGE_BONUS.items())
    def test_stage_bonuses(self, make_country, make_match, stage, bonus):
        home = make_country(tier=1)
        away = make_country(tier=2)
        match = make_match(home, away, 1, 0, stage=stage)
        expected = round(3 * 1.0 + bonus, 2)
        assert match_points_for_country(match, home) == expected


class TestCountryStats:

    def test_no_matches_all_zero(self, make_country):
        country = make_country(tier=1)
        stats = country_stats(country)
        assert stats == {'points': 0.0, 'gf': 0, 'ga': 0,
                         'furthest': 0, 'played': 0, 'wins': 0,
                         'draws': 0, 'losses': 0}

    def test_aggregates_multiple_matches(self, make_country, make_match):
        home = make_country(tier=1)
        away = make_country(tier=2)
        make_match(home, away, 2, 0)  # win
        make_match(home, away, 1, 1)  # draw
        make_match(home, away, 0, 1)  # loss
        stats = country_stats(home)
        assert stats['played'] == 3
        assert stats['wins'] == 1
        assert stats['draws'] == 1
        assert stats['losses'] == 1
        assert stats['gf'] == 3
        assert stats['ga'] == 2

    def test_furthest_round_tracked(self, make_country, make_match):
        home = make_country(tier=1)
        away = make_country(tier=2)
        make_match(home, away, 1, 0, stage='GROUP_STAGE')
        make_match(home, away, 1, 0, stage='SEMI_FINALS')
        stats = country_stats(home)
        assert stats['furthest'] == 4  # ROUND_ORDER['SEMI_FINALS'] == 4

    def test_pending_matches_excluded(self, make_country, make_match):
        home = make_country(tier=1)
        away = make_country(tier=2)
        make_match(home, away, None, None, status='SCHEDULED')
        stats = country_stats(home)
        assert stats['played'] == 0
        assert stats['points'] == 0.0


class TestPlayerStandings:

    def test_sorted_by_points_descending(self, db, make_player, make_country, make_match):
        p1 = make_player('Alice')
        p2 = make_player('Bob')
        c1 = make_country(tier=1)
        c2 = make_country(tier=4)
        c1.player_id = p1.id
        c2.player_id = p2.id
        db.session.flush()
        make_match(c1, c2, 1, 0)  # c1 (Alice, tier 1) wins → 3 pts
        make_match(c2, c1, 1, 0)  # c2 (Bob, tier 4) wins → 5.25 pts
        db.session.commit()
        rows = player_standings()
        assert rows[0]['player'].name == 'Bob'
        assert rows[1]['player'].name == 'Alice'

    def test_goal_difference_tiebreaker(self, db, make_player, make_country, make_match):
        p1 = make_player('Alice')
        p2 = make_player('Bob')
        c1 = make_country(tier=1)
        c2 = make_country(tier=1)
        c3 = make_country(tier=2)
        c1.player_id = p1.id
        c2.player_id = p2.id
        db.session.flush()
        make_match(c1, c3, 3, 0)  # Alice wins 3-0, GD=+3
        make_match(c2, c3, 1, 0)  # Bob wins 1-0, GD=+1
        db.session.commit()
        rows = player_standings()
        assert rows[0]['player'].name == 'Alice'

    def test_alphabetical_final_tiebreaker(self, db, make_player, make_country, make_match):
        p1 = make_player('Zara')
        p2 = make_player('Alice')
        c1 = make_country(tier=1)
        c2 = make_country(tier=1)
        c3 = make_country(tier=2)
        c1.player_id = p1.id
        c2.player_id = p2.id
        db.session.flush()
        make_match(c1, c3, 1, 0)  # both win 1-0, equal points and GD
        make_match(c2, c3, 1, 0)
        db.session.commit()
        rows = player_standings()
        assert rows[0]['player'].name == 'Alice'  # alphabetically first
        assert rows[1]['player'].name == 'Zara'
