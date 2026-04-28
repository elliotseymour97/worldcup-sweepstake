from datetime import date, timezone
from flask import Blueprint, render_template
from models import Match
from api_client import fetch_and_sync
from points import STAGE_LABELS

scores_bp = Blueprint('scores', __name__)


def _grouped_matches():
    fetch_and_sync()
    all_matches = Match.query.order_by(Match.kickoff.asc()).all()
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
