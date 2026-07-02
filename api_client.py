from __future__ import annotations

import json
import re
import threading
import requests
from datetime import datetime, timedelta
from typing import Optional
from flask import current_app
from models import db, Country, Match

_last_fetch: Optional[datetime] = None
_last_error: Optional[str]      = None
_sync_lock  = threading.Lock()

STAGE_MAP = {
    'GROUP_STAGE':    'GROUP_STAGE',
    'LAST_32':        'LAST_32',
    'LAST_16':        'LAST_16',
    'QUARTER_FINALS': 'QUARTER_FINALS',
    'SEMI_FINALS':    'SEMI_FINALS',
    'THIRD_PLACE':    'THIRD_PLACE',
    'FINAL':          'FINAL',
}


def _normalise(s: str) -> str:
    if not s:
        return ''
    s = s.strip().lower()
    s = s.replace('-', ' ')
    s = s.replace('&', 'and')
    s = re.sub(r'\s+and\s+', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


def _find_country(api_name: str) -> Optional[Country]:
    if not api_name:
        return None
    needle = _normalise(api_name)
    all_countries = Country.query.all()
    for c in all_countries:
        if _normalise(c.api_name) == needle:
            return c
    for c in all_countries:
        if _normalise(c.name) == needle:
            return c
    return None


def get_last_fetch() -> Optional[datetime]:
    return _last_fetch


def get_last_error() -> Optional[str]:
    return _last_error


def fetch_and_sync() -> tuple[bool, str]:
    """Public entry point used by the admin manual refresh. Respects a 15-s throttle."""
    now = datetime.utcnow()
    if _last_fetch and (now - _last_fetch) < timedelta(seconds=15):
        secs = int((now - _last_fetch).total_seconds())
        return True, f'Data is fresh (last synced {secs}s ago).'
    return _do_sync()


def _do_sync() -> tuple[bool, str]:
    """Call the football-data API and write results to the DB.
    Protected by a lock so only one sync runs at a time."""
    global _last_fetch, _last_error

    if not _sync_lock.acquire(blocking=False):
        return True, 'Sync already in progress.'

    try:
        api_key = current_app.config.get('FOOTBALL_DATA_API_KEY', '')
        if not api_key:
            _last_error = 'No API key configured.'
            return False, _last_error

        competition = current_app.config.get('COMPETITION_CODE', 'WC')
        url = f'https://api.football-data.org/v4/competitions/{competition}/matches'

        try:
            resp = requests.get(url, headers={'X-Auth-Token': api_key}, timeout=10)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            _last_error = f'API request failed: {e}'
            return False, _last_error

        matches = data.get('matches', [])
        finished_now = _sync_matches(matches)

        try:
            _maybe_snapshot(force=finished_now)
        except Exception:
            pass

        try:
            from routes.main import invalidate_standings_cache
            invalidate_standings_cache()
        except Exception:
            pass

        _last_fetch = datetime.utcnow()
        _last_error = None
        return True, f'Synced {len(matches)} matches.'

    except Exception as e:
        _last_error = f'Sync error: {e}'
        return False, _last_error
    finally:
        _sync_lock.release()


def _maybe_snapshot(force: bool = False) -> None:
    """Record a standings snapshot for the history chart. To keep that chart
    readable, only do this when a match has just finished (`force=True`) or
    it's been at least a day since the last point — not on every live-score
    tick, which would plot a new point after every goal (or penalty)."""
    from models import StandingsSnapshot, db
    from points import player_standings
    from sqlalchemy import func

    standings = player_standings()
    if not standings:
        return

    current = {row['player'].id: round(row['points'], 4) for row in standings}

    last_time = db.session.query(func.max(StandingsSnapshot.taken_at)).scalar()
    if last_time:
        last = {s.player_id: round(s.points, 4)
                for s in StandingsSnapshot.query.filter_by(taken_at=last_time).all()}
        if last == current:
            return
        if not force and (datetime.utcnow() - last_time) < timedelta(days=1):
            return

    now = datetime.utcnow()
    for row in standings:
        db.session.add(StandingsSnapshot(
            taken_at=now,
            player_id=row['player'].id,
            points=row['points'],
            rank=row['rank'],
        ))
    db.session.commit()


def cleanup_standings_history() -> str:
    """Retroactively collapse standings-snapshot history down to one point per
    day (keeping each day's last snapshot, plus the very first one ever),
    undoing the old behaviour of snapshotting on every live-score tick."""
    from models import StandingsSnapshot, db

    snapshots = StandingsSnapshot.query.order_by(StandingsSnapshot.taken_at.asc()).all()
    if not snapshots:
        return 'No history to clean up.'

    times = sorted({s.taken_at for s in snapshots})
    if len(times) <= 1:
        return 'Nothing to clean up — only one snapshot exists.'

    last_per_day = {}
    for t in times:
        last_per_day[t.date()] = t
    keep = {times[0]} | set(last_per_day.values())

    removed = StandingsSnapshot.query.filter(
        ~StandingsSnapshot.taken_at.in_(keep)).delete(synchronize_session=False)
    db.session.commit()
    return f'Removed {removed} snapshot rows, kept {len(keep)} history points.'


def _sync_matches(api_matches: list) -> bool:
    """Sync matches from the API into the DB. Returns True if any match
    transitioned to FINISHED during this sync (used to force a standings
    snapshot for the history chart)."""
    any_finished = False
    for m in api_matches:
        api_id    = m.get('id')
        home_name = m.get('homeTeam', {}).get('name') or ''
        away_name = m.get('awayTeam', {}).get('name') or ''
        stage     = STAGE_MAP.get(m.get('stage', ''), m.get('stage', ''))
        status    = m.get('status', 'SCHEDULED')

        ft         = m.get('score', {}).get('fullTime', {})
        home_score = ft.get('home')
        away_score = ft.get('away')

        kickoff_str = m.get('utcDate')
        kickoff = None
        if kickoff_str:
            try:
                kickoff = datetime.fromisoformat(kickoff_str.replace('Z', '+00:00'))
            except ValueError:
                pass

        group_raw    = m.get('group') or ''
        group_letter = group_raw.replace('GROUP_', '') if group_raw.startswith('GROUP_') else None

        home_country = _find_country(home_name)
        away_country = _find_country(away_name)

        match = Match.query.filter_by(api_id=api_id).first()
        if not match:
            match = Match(api_id=api_id)
            db.session.add(match)

        home_api_id = m.get('homeTeam', {}).get('id')

        goals = []
        for g in (m.get('goals') or []):
            minute   = g.get('minute', 0)
            inj      = g.get('injuryTime')
            disp_min = f"{minute}+{inj}" if inj else str(minute)
            scorer   = (g.get('scorer') or {}).get('name') or '?'
            team_id  = (g.get('team') or {}).get('id')
            goals.append({'minute': disp_min, 'scorer': scorer,
                          'is_home': team_id == home_api_id, 'type': g.get('type', 'REGULAR')})

        bookings = []
        for b in (m.get('bookings') or []):
            team_id = (b.get('team') or {}).get('id')
            bookings.append({'minute': b.get('minute', 0),
                             'player': (b.get('player') or {}).get('name') or '?',
                             'is_home': team_id == home_api_id, 'card': b.get('card', '')})

        # Prevent status regressions caused by API glitches:
        #   active/finished → SCHEDULED/TIMED  (API sends wrong status mid-match)
        #   FINISHED → any live status          (API briefly re-opens a finished match)
        _active = {'IN_PLAY', 'PAUSED', 'EXTRA_TIME', 'PENALTY_SHOOTOUT', 'FINISHED', 'SUSPENDED', 'POSTPONED'}
        _live   = {'IN_PLAY', 'PAUSED', 'EXTRA_TIME', 'PENALTY_SHOOTOUT'}
        is_regression = (
            (match.status in _active and status in ('SCHEDULED', 'TIMED')) or
            (match.status == 'FINISHED' and status in _live)
        )
        new_status = match.status if is_regression else status
        if match.status != 'FINISHED' and new_status == 'FINISHED':
            any_finished = True

        match.home_team_name = home_name
        match.away_team_name = away_name
        match.home_team_id   = home_country.id if home_country else None
        match.away_team_id   = away_country.id if away_country else None
        match.stage          = stage
        match.group_name     = group_letter
        match.status         = new_status
        match.kickoff        = kickoff
        match.last_updated   = datetime.utcnow()

        # On a regression the existing live data is correct — skip all updates
        if not is_regression:
            if home_score is not None:
                match.home_score = home_score
            if away_score is not None:
                match.away_score = away_score
            api_minute = m.get('minute')
            if api_minute is not None:
                match.minute = api_minute
            match.goals_json    = json.dumps(goals) if goals else None
            match.bookings_json = json.dumps(bookings) if bookings else None

    db.session.commit()
    return any_finished
