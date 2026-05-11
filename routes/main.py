from flask import Blueprint, render_template
from points import player_standings, country_stats

main_bp = Blueprint('main', __name__)


def _build_standings():
    standings = player_standings()
    for row in standings:
        row['country_stats'] = {
            c.id: country_stats(c) for c in row['player'].countries
        }
    return standings


@main_bp.route('/')
def league():
    return render_template('league.html', standings=_build_standings())


@main_bp.route('/league/standings')
def league_standings():
    return render_template('_standings_partial.html', standings=_build_standings())


@main_bp.route('/rules')
def rules():
    return render_template('rules.html')
