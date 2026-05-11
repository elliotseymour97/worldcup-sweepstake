import threading
from datetime import date
from flask import Blueprint, render_template, current_app
from sqlalchemy.orm import joinedload
from models import Match, Country
from api_client import fetch_and_sync
from points import STAGE_LABELS

scores_bp = Blueprint('scores', __name__)


def _trigger_sync():
    app = current_app._get_current_object()
    def _run():
        with app.app_context():
            fetch_and_sync()
    threading.Thread(target=_run, daemon=True).start()


def _grouped_matches():
    _trigger_sync()
    all_matches = Match.query.options(
        joinedload(Match.home_country).joinedload(Country.player),
        joinedload(Match.away_country).joinedload(Country.player),
    ).order_by(Match.kickoff.asc()).all()
    today = date.today()

    live     = [m for m in all_matches if m.status in ('IN_PLAY', 'PAUSED')]
    upcoming = [m for m in all_matches if m.status in ('SCHEDULED', 'TIMED')
                and m.kickoff and m.kickoff.date() >= today]
    results  = [m for m in reversed(all_matches) if m.status == 'FINISHED']

    return live, upcoming, results


@scores_bp.route('/scores')
def scores():
    live, upcoming, results = _grouped_matches()
    return render_template('scores.html',
                           live=live, upcoming=upcoming, results=results,
                           stage_labels=STAGE_LABELS)


@scores_bp.route('/scores/live')
def scores_live():
    live, upcoming, results = _grouped_matches()
    return render_template('_matches_partial.html',
                           live=live, upcoming=upcoming, results=results,
                           stage_labels=STAGE_LABELS)
