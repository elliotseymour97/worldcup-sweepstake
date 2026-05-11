from functools import wraps
from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, session, current_app)
from models import db, Player, Country
from draw import run_draw
from api_client import fetch_and_sync
from routes.main import invalidate_standings_cache

admin_bp = Blueprint('admin', __name__)


def _require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin.login'))
        return f(*args, **kwargs)
    return decorated


@admin_bp.route('/admin/login', methods=['GET', 'POST'])
def login():
    if session.get('admin_logged_in'):
        return redirect(url_for('admin.admin'))
    error = None
    if request.method == 'POST':
        password = current_app.config.get('ADMIN_PASSWORD', '')
        if request.form.get('password') == password:
            session['admin_logged_in'] = True
            return redirect(url_for('admin.admin'))
        error = 'Incorrect password.'
    return render_template('admin_login.html', error=error)


@admin_bp.route('/admin/logout', methods=['POST'])
def logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin.login'))


@admin_bp.route('/admin')
@_require_auth
def admin():
    players = Player.query.all()
    draw_done = Player.query.count() == 6
    return render_template('admin.html', players=players, draw_done=draw_done)


@admin_bp.route('/admin/draw', methods=['POST'])
@_require_auth
def do_draw():
    names = [request.form.get(f'player{i}', '') for i in range(1, 7)]
    try:
        run_draw(names)
        invalidate_standings_cache()
        flash('Draw complete! Countries have been assigned.', 'success')
    except ValueError as e:
        flash(str(e), 'error')
    return redirect(url_for('admin.admin'))


@admin_bp.route('/admin/refresh', methods=['POST'])
@_require_auth
def refresh_data():
    ok, msg = fetch_and_sync()
    flash(msg, 'success' if ok else 'error')
    return redirect(url_for('admin.admin'))


@admin_bp.route('/admin/reset', methods=['POST'])
@_require_auth
def reset_draw():
    Country.query.update({'player_id': None})
    Player.query.delete()
    db.session.commit()
    invalidate_standings_cache()
    flash('Draw has been reset.', 'success')
    return redirect(url_for('admin.admin'))
