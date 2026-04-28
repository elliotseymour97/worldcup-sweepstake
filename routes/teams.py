from flask import Blueprint, render_template
from models import Player, Country

teams_bp = Blueprint('teams', __name__)


@teams_bp.route('/teams')
def teams():
    players = Player.query.all()
    all_countries = Country.query.order_by(Country.group_name, Country.tier).all()
    return render_template('teams.html', players=players, all_countries=all_countries)
