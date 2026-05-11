from flask import Blueprint, render_template
from sqlalchemy.orm import subqueryload, joinedload
from models import Player, Country

teams_bp = Blueprint('teams', __name__)


@teams_bp.route('/teams')
def teams():
    players = Player.query.options(
        subqueryload(Player.countries)
    ).all()
    all_countries = Country.query.options(
        joinedload(Country.player)
    ).order_by(Country.group_name, Country.tier).all()
    return render_template('teams.html', players=players, all_countries=all_countries)
