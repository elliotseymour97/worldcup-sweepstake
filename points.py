from datetime import datetime
from sqlalchemy.orm import subqueryload
from models import Player, Match, Country

STAGE_BONUS = {
    'GROUP_STAGE':    0,
    'LAST_32':        1,
    'LAST_16':        2,
    'QUARTER_FINALS': 3,
    'SEMI_FINALS':    4,
    'THIRD_PLACE':    5,
    'FINAL':          5,
}

ROUND_ORDER = {
    'GROUP_STAGE':    0,
    'LAST_32':        1,
    'LAST_16':        2,
    'QUARTER_FINALS': 3,
    'SEMI_FINALS':    4,
    'THIRD_PLACE':    5,
    'FINAL':          6,
}

STAGE_LABELS = {
    'GROUP_STAGE':    'Group Stage',
    'LAST_32':        'Round of 32',
    'LAST_16':        'Round of 16',
    'QUARTER_FINALS': 'Quarter-Final',
    'SEMI_FINALS':    'Semi-Final',
    'THIRD_PLACE':    'Third Place',
    'FINAL':          'Final',
}

FURTHEST_LABELS = ['Groups', 'R32', 'R16', 'QF', 'SF', '3rd/Final', 'Final']

_LIVE_STATUSES = ('IN_PLAY', 'PAUSED')


def match_points_for_country(match, country, include_live=False):
    is_live = match.status in _LIVE_STATUSES
    if match.status != 'FINISHED' and not (include_live and is_live):
        return 0.0

    is_home = (match.home_team_id == country.id)
    scored   = match.home_score if is_home else match.away_score
    conceded = match.away_score if is_home else match.home_score

    if scored is None or conceded is None:
        return 0.0

    if scored > conceded:
        base = 3
    elif scored == conceded and match.stage == 'GROUP_STAGE':
        base = 1
    else:
        base = 0

    if base == 0:
        return 0.0

    return round(base * country.multiplier + STAGE_BONUS.get(match.stage, 0), 2)


def country_stats(country, include_live=False):
    gf = ga = 0
    confirmed_pts = provisional_pts = 0.0
    furthest = 0
    played = wins = draws = losses = 0
    has_live = False

    all_matches = country.home_matches + country.away_matches
    for match in all_matches:
        is_live = match.status in _LIVE_STATUSES
        is_done = match.status == 'FINISHED'

        if not is_done and not (include_live and is_live):
            continue

        is_home = (match.home_team_id == country.id)
        scored   = match.home_score if is_home else match.away_score
        conceded = match.away_score if is_home else match.home_score

        if scored is None or conceded is None:
            continue

        gf += scored
        ga += conceded

        match_pts = match_points_for_country(match, country, include_live=include_live)
        round_val = ROUND_ORDER.get(match.stage, 0)
        if round_val > furthest:
            furthest = round_val

        if is_done:
            confirmed_pts += match_pts
            played += 1
            if scored > conceded:
                wins += 1
            elif scored == conceded and match.stage == 'GROUP_STAGE':
                draws += 1
            else:
                losses += 1
        else:
            provisional_pts += match_pts
            has_live = True

    result = {
        'points':  confirmed_pts + provisional_pts,
        'gf':      gf,
        'ga':      ga,
        'furthest': furthest,
        'played':  played,
        'wins':    wins,
        'draws':   draws,
        'losses':  losses,
    }
    if include_live:
        result['live_pts'] = provisional_pts
        result['has_live'] = has_live
    return result


def _player_form(player):
    results = []
    for country in player.countries:
        for match in country.home_matches + country.away_matches:
            if match.status != 'FINISHED':
                continue
            is_home = match.home_team_id == country.id
            scored = match.home_score if is_home else match.away_score
            conceded = match.away_score if is_home else match.home_score
            if scored is None or conceded is None:
                continue
            if scored > conceded:
                result = 'W'
            elif scored == conceded and match.stage == 'GROUP_STAGE':
                result = 'D'
            else:
                result = 'L'
            results.append((match.kickoff or datetime.min, result))
    results.sort(key=lambda x: x[0], reverse=True)
    return [r for _, r in results[:5]]


def player_standings(include_live=False):
    players = Player.query.options(
        subqueryload(Player.countries).subqueryload(Country.home_matches),
        subqueryload(Player.countries).subqueryload(Country.away_matches),
    ).all()
    rows = []

    for player in players:
        pts = live_pts = 0.0
        gf = ga = furthest = 0
        played = wins = draws = losses = 0
        has_live = False

        for country in player.countries:
            stats = country_stats(country, include_live=include_live)
            pts    += stats['points']
            gf     += stats['gf']
            ga     += stats['ga']
            played += stats['played']
            wins   += stats['wins']
            draws  += stats['draws']
            losses += stats['losses']
            if stats['furthest'] > furthest:
                furthest = stats['furthest']
            if include_live:
                live_pts += stats.get('live_pts', 0.0)
                if stats.get('has_live'):
                    has_live = True

        row = {
            'player':   player,
            'points':   round(pts, 2),
            'played':   played,
            'wins':     wins,
            'draws':    draws,
            'losses':   losses,
            'gf':       gf,
            'ga':       ga,
            'gd':       gf - ga,
            'furthest': furthest,
            'form':     _player_form(player),
        }
        if include_live:
            row['live_pts'] = round(live_pts, 2)
            row['has_live'] = has_live
        rows.append(row)

    rows.sort(key=lambda x: (-x['points'], -x['gd'], -x['furthest'], x['player'].name))
    for i, row in enumerate(rows):
        row['rank'] = i + 1

    return rows
