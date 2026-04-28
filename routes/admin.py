from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db, Player, Country
from draw import run_draw
from api_client import fetch_and_sync

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/admin')
def admin():
    players = Player.query.all()
    draw_done = Player.query.count() == 6
    return render_template('admin.html', players=players, draw_done=draw_done)


@admin_bp.route('/admin/draw', methods=['POST'])
def do_draw():
    names = [request.form.get(f'player{i}', '') for i in range(1, 7)]
    try:
        run_draw(names)
        flash('Draw complete! Countries have been assigned.', 'success')
    except ValueError as e:
        flash(str(e), 'error')
    return redirect(url_for('admin.admin'))


@admin_bp.route('/admin/refresh', methods=['POST'])
def refresh_data():
    ok, msg = fetch_and_sync()
    flash(msg, 'success' if ok else 'error')
    return redirect(url_for('admin.admin'))


@admin_bp.route('/admin/reset', methods=['POST'])
def reset_draw():
    Country.query.update({'player_id': None})
    Player.query.delete()
    db.session.commit()
    flash('Draw has been reset.', 'success')
    return redirect(url_for('admin.admin'))
