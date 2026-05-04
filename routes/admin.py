from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, flash, Response, current_app
from models import db, Player, Country
from draw import run_draw
from api_client import fetch_and_sync

admin_bp = Blueprint('admin', __name__)


def _require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        password = current_app.config.get('ADMIN_PASSWORD', '')
        if not password:
            return Response(
                'Set ADMIN_PASSWORD to enable the admin panel.',
                401,
                {'WWW-Authenticate': 'Basic realm="Admin"'},
            )
        auth = request.authorization
        if not auth or \
           auth.username != current_app.config.get('ADMIN_USER', 'admin') or \
           auth.password != password:
            return Response(
                'Incorrect credentials.',
                401,
                {'WWW-Authenticate': 'Basic realm="Admin"'},
            )
        return f(*args, **kwargs)
    return decorated


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
    flash('Draw has been reset.', 'success')
    return redirect(url_for('admin.admin'))
