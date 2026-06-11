import time
from datetime import datetime, date as _date
from flask import Blueprint, render_template
from sqlalchemy.orm import subqueryload, joinedload
from models import Player, Country, Match
from points import player_standings, country_stats, STAGE_LABELS, ROUND_ORDER

_PLAYER_COLORS = ['emerald', 'blue', 'violet', 'amber', 'rose', 'cyan']
_COLOR_HEX = {
    'emerald': '#10b981', 'blue': '#3b82f6', 'violet': '#8b5cf6',
    'amber':   '#f59e0b', 'rose': '#f43f5e', 'cyan':   '#06b6d4',
}

main_bp = Blueprint('main', __name__)

_cache = {'standings': None, 'at': 0.0}
_CACHE_TTL = 30

KNOCKOUT_STAGES = ['LAST_32', 'LAST_16', 'QUARTER_FINALS', 'SEMI_FINALS', 'THIRD_PLACE', 'FINAL']


def _build_standings():
    now = time.monotonic()
    if _cache['standings'] is not None and (now - _cache['at']) < _CACHE_TTL:
        return _cache['standings']
    standings = player_standings(include_live=True)
    for row in standings:
        cstats = {}
        for c in row['player'].countries:
            cs = country_stats(c)
            all_m = c.home_matches + c.away_matches
            has_played   = any(m.status == 'FINISHED' for m in all_m)
            has_upcoming = any(m.status in ('SCHEDULED', 'TIMED') for m in all_m)
            cs['eliminated'] = has_played and not has_upcoming
            cstats[c.id] = cs
        row['country_stats'] = cstats
    _cache['standings'] = standings
    _cache['at'] = now
    return standings


def _todays_and_live():
    today = _date.today()
    matches = Match.query.options(
        joinedload(Match.home_country).joinedload(Country.player),
        joinedload(Match.away_country).joinedload(Country.player),
    ).filter(Match.status.in_(['IN_PLAY', 'PAUSED', 'SCHEDULED', 'TIMED'])
    ).order_by(Match.kickoff.asc()).all()
    live  = [m for m in matches if m.status in ('IN_PLAY', 'PAUSED')]
    today_ = [m for m in matches if m.status in ('SCHEDULED', 'TIMED')
               and m.kickoff and m.kickoff.date() == today]
    return live, today_


def invalidate_standings_cache():
    _cache['standings'] = None


@main_bp.route('/')
def league():
    live, today = _todays_and_live()
    return render_template('league.html', standings=_build_standings(),
                           live_matches=live, today_matches=today)


@main_bp.route('/league/standings')
def league_standings():
    live, today = _todays_and_live()
    return render_template('_standings_partial.html', standings=_build_standings(),
                           live_matches=live, today_matches=today)


@main_bp.route('/history')
def history():
    from models import StandingsSnapshot
    from sqlalchemy import func

    players = Player.query.all()
    snapshots = StandingsSnapshot.query.order_by(
        StandingsSnapshot.taken_at.asc()).all()

    if not players or not snapshots:
        return render_template('history.html', labels=[], datasets=[])

    seen = {}
    for s in snapshots:
        key = s.taken_at.strftime('%d %b %H:%M')
        if key not in seen:
            seen[key] = s.taken_at
    labels = list(seen.keys())

    datasets = []
    for p in players:
        cn = _PLAYER_COLORS[p.id % len(_PLAYER_COLORS)]
        snap_map = {s.taken_at.strftime('%d %b %H:%M'): s.points
                    for s in snapshots if s.player_id == p.id}
        datasets.append({
            'name':  p.name,
            'color': _COLOR_HEX.get(cn, '#6b7280'),
            'data':  [snap_map.get(lbl) for lbl in labels],
        })

    return render_template('history.html', labels=labels, datasets=datasets)


@main_bp.route('/rules')
def rules():
    return render_template('rules.html')


@main_bp.route('/player/<int:player_id>')
def player_detail(player_id):
    player = Player.query.options(
        subqueryload(Player.countries).subqueryload(Country.home_matches),
        subqueryload(Player.countries).subqueryload(Country.away_matches),
    ).filter_by(id=player_id).first_or_404()

    country_data = []
    total_points = 0.0
    for country in sorted(player.countries, key=lambda c: c.tier):
        stats = country_stats(country)
        stats['gd'] = stats['gf'] - stats['ga']
        country_data.append((country, stats))
        total_points += stats['points']

    # Last 10 finished matches across all countries
    recent = []
    for country in player.countries:
        for match in country.home_matches + country.away_matches:
            if match.status == 'FINISHED' and match.home_score is not None:
                recent.append((match, country))
    recent.sort(key=lambda x: x[0].kickoff or datetime.min, reverse=True)
    recent_matches = recent[:10]

    # Upcoming fixtures — deduplicated by match id
    today = _date.today()
    seen = set()
    upcoming = []
    for country in player.countries:
        for match in country.home_matches + country.away_matches:
            if (match.status in ('SCHEDULED', 'TIMED')
                    and match.kickoff
                    and match.kickoff.date() >= today
                    and match.id not in seen):
                seen.add(match.id)
                upcoming.append((match, country))
    upcoming.sort(key=lambda x: x[0].kickoff)
    upcoming_fixtures = upcoming[:8]

    standings = _build_standings()
    rank = next((r['rank'] for r in standings if r['player'].id == player_id), '–')

    return render_template('player.html',
                           player=player,
                           country_data=country_data,
                           total_points=round(total_points, 2),
                           rank=rank,
                           recent_matches=recent_matches,
                           upcoming_fixtures=upcoming_fixtures,
                           stage_labels=STAGE_LABELS)


@main_bp.route('/groups')
def groups():
    matches = Match.query.filter_by(stage='GROUP_STAGE').options(
        joinedload(Match.home_country).joinedload(Country.player),
        joinedload(Match.away_country).joinedload(Country.player),
    ).order_by(Match.kickoff.asc()).all()

    group_data = {}
    for m in matches:
        group = m.group_name or '?'
        if group not in group_data:
            group_data[group] = {}

        for is_home in (True, False):
            name    = m.home_team_name if is_home else m.away_team_name
            country = m.home_country   if is_home else m.away_country
            scored   = m.home_score if is_home else m.away_score
            conceded = m.away_score if is_home else m.home_score

            if name not in group_data[group]:
                group_data[group][name] = {
                    'country': country,
                    'name': name,
                    'P': 0, 'W': 0, 'D': 0, 'L': 0,
                    'GF': 0, 'GA': 0, 'Pts': 0,
                }

            if m.status == 'FINISHED' and scored is not None and conceded is not None:
                entry = group_data[group][name]
                entry['P'] += 1
                entry['GF'] += scored
                entry['GA'] += conceded
                if scored > conceded:
                    entry['W'] += 1
                    entry['Pts'] += 3
                elif scored == conceded:
                    entry['D'] += 1
                    entry['Pts'] += 1
                else:
                    entry['L'] += 1

    sorted_groups = {}
    for g in sorted(group_data.keys()):
        teams = list(group_data[g].values())
        for t in teams:
            t['GD'] = t['GF'] - t['GA']
        teams.sort(key=lambda x: (-x['Pts'], -x['GD'], -x['GF'], x['name']))
        sorted_groups[g] = teams

    return render_template('groups.html', groups=sorted_groups)


@main_bp.route('/bracket')
def bracket():
    matches_by_stage = {}
    for stage in KNOCKOUT_STAGES:
        stage_matches = Match.query.filter_by(stage=stage).options(
            joinedload(Match.home_country).joinedload(Country.player),
            joinedload(Match.away_country).joinedload(Country.player),
        ).order_by(Match.kickoff.asc()).all()
        if stage_matches:
            matches_by_stage[stage] = stage_matches

    return render_template('bracket.html',
                           matches_by_stage=matches_by_stage,
                           stage_labels=STAGE_LABELS,
                           knockout_stages=KNOCKOUT_STAGES)
