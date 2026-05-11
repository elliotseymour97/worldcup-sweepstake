import time
from flask import Blueprint, render_template
from points import player_standings, country_stats

main_bp = Blueprint('main', __name__)

_cache = {'standings': None, 'at': 0.0}
_CACHE_TTL = 30


def _build_standings():
    now = time.monotonic()
    if _cache['standings'] is not None and (now - _cache['at']) < _CACHE_TTL:
        return _cache['standings']
    standings = player_standings()
    for row in standings:
        row['country_stats'] = {c.id: country_stats(c) for c in row['player'].countries}
    _cache['standings'] = standings
    _cache['at'] = now
    return standings


def invalidate_standings_cache():
    _cache['standings'] = None


@main_bp.route('/')
def league():
    return render_template('league.html', standings=_build_standings())


@main_bp.route('/league/standings')
def league_standings():
    return render_template('_standings_partial.html', standings=_build_standings())


@main_bp.route('/rules')
def rules():
    return render_template('rules.html')
