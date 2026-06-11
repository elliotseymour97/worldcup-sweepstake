from collections import defaultdict
from datetime import date
from flask import Blueprint, render_template
from sqlalchemy.orm import joinedload
from models import Match, Country
from api_client import fetch_and_sync, get_last_fetch
from points import STAGE_LABELS

scores_bp = Blueprint('scores', __name__)


def _grouped_matches():
    # Sync inline so the response always reflects the latest data.
    # fetch_and_sync() throttles to one API call per 60 s, so most hits
    # return immediately from the in-memory cache.
    try:
        fetch_and_sync()
    except Exception:
        pass
    all_matches = Match.query.options(
        joinedload(Match.home_country).joinedload(Country.player),
        joinedload(Match.away_country).joinedload(Country.player),
    ).order_by(Match.kickoff.asc()).all()
    today = date.today()

    live          = [m for m in all_matches if m.status in ('IN_PLAY', 'PAUSED', 'EXTRA_TIME', 'PENALTY_SHOOTOUT')]
    today_matches = [m for m in all_matches if m.status in ('SCHEDULED', 'TIMED')
                     and m.kickoff and m.kickoff.date() == today]
    future        = [m for m in all_matches if m.status in ('SCHEDULED', 'TIMED')
                     and m.kickoff and m.kickoff.date() > today]
    results       = [m for m in reversed(all_matches) if m.status == 'FINISHED']

    upcoming_by_date = defaultdict(list)
    for m in future:
        upcoming_by_date[m.kickoff.date()].append(m)
    upcoming_by_date = dict(sorted(upcoming_by_date.items()))

    return live, today_matches, upcoming_by_date, results


def _last_synced_str():
    lf = get_last_fetch()
    return lf.strftime('%H:%M') if lf else None


@scores_bp.route('/scores')
def scores():
    live, today_matches, upcoming_by_date, results = _grouped_matches()
    return render_template('scores.html',
                           live=live, today_matches=today_matches,
                           upcoming_by_date=upcoming_by_date, results=results,
                           stage_labels=STAGE_LABELS,
                           last_synced=_last_synced_str())


@scores_bp.route('/scores/live')
def scores_live():
    live, today_matches, upcoming_by_date, results = _grouped_matches()
    return render_template('_matches_partial.html',
                           live=live, today_matches=today_matches,
                           upcoming_by_date=upcoming_by_date, results=results,
                           stage_labels=STAGE_LABELS,
                           last_synced=_last_synced_str())
