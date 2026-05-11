from models import Player, Match

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


def match_points_for_country(match, country):
    if match.status != 'FINISHED':
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


def country_stats(country):
    gf = ga = 0
    pts = 0.0
    furthest = 0
    played = wins = draws = losses = 0

    all_matches = country.home_matches + country.away_matches
    for match in all_matches:
        if match.status != 'FINISHED':
            continue
        is_home = (match.home_team_id == country.id)
        scored   = match.home_score if is_home else match.away_score
        conceded = match.away_score if is_home else match.home_score

        gf += scored   or 0
        ga += conceded or 0
        pts += match_points_for_country(match, country)

        round_val = ROUND_ORDER.get(match.stage, 0)
        if round_val > furthest:
            furthest = round_val

        played += 1
        if scored > conceded:
            wins += 1
        elif scored == conceded and match.stage == 'GROUP_STAGE':
            draws += 1
        else:
            losses += 1

    return {'points': pts, 'gf': gf, 'ga': ga, 'furthest': furthest,
            'played': played, 'wins': wins, 'draws': draws, 'losses': losses}


def player_standings():
    players = Player.query.all()
    rows = []

    for player in players:
        pts = 0.0
        gf = ga = furthest = 0
        played = wins = draws = losses = 0

        for country in player.countries:
            stats = country_stats(country)
            pts     += stats['points']
            gf      += stats['gf']
            ga      += stats['ga']
            played  += stats['played']
            wins    += stats['wins']
            draws   += stats['draws']
            losses  += stats['losses']
            if stats['furthest'] > furthest:
                furthest = stats['furthest']

        rows.append({
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
        })

    rows.sort(key=lambda x: (-x['points'], -x['gd'], -x['furthest']))
    for i, row in enumerate(rows):
        row['rank'] = i + 1

    return rows
