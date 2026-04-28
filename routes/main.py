from flask import Blueprint, render_template
from points import player_standings, country_stats

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def league():
    standings = player_standings()
    for row in standings:
        row['country_stats'] = {
            c.id: country_stats(c) for c in row['player'].countries
        }
    return render_template('league.html', standings=standings)
