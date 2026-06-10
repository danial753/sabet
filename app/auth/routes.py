from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from app.models import db, User, WorkSession
from datetime import datetime, timezone, timedelta

auth_bp = Blueprint('auth', __name__)
IRAN_TZ = timezone(timedelta(hours=3, minutes=30))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        # هدایت بر اساس نقش
        if current_user.is_admin:
            return redirect(url_for('admin.view_user_reports'))
        if current_user.is_approver:
            return redirect(url_for('reports.approver_dashboard'))
        if current_user.is_shift_planner:
            return redirect(url_for('reports.shift_planner_dashboard'))
        if current_user.is_quality_inspector:
            return redirect(url_for('reports.quality_inspector_dashboard'))
        if current_user.is_warehouse:
            return redirect(url_for('reports.warehouse_dashboard'))
        return redirect(url_for('reports.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            # بستن جلسه کاری باز قبلی (در صورت وجود)
            open_session = WorkSession.query.filter_by(user_id=user.id, logout_time=None).first()
            if open_session:
                open_session.logout_time = datetime.now(IRAN_TZ)
                db.session.commit()
            # ایجاد جلسه کاری جدید
            new_session = WorkSession(user_id=user.id, login_time=datetime.now(IRAN_TZ))
            db.session.add(new_session)
            db.session.commit()

            # هدایت بر اساس نقش
            if user.is_admin:
                return redirect(url_for('admin.view_user_reports'))
            if user.is_approver:
                return redirect(url_for('reports.approver_dashboard'))
            if user.is_shift_planner:
                return redirect(url_for('reports.shift_planner_dashboard'))
            if user.is_quality_inspector:
                return redirect(url_for('reports.quality_inspector_dashboard'))
            if user.is_warehouse:
                return redirect(url_for('reports.warehouse_dashboard'))
            return redirect(url_for('reports.dashboard'))
        else:
            flash('نام کاربری یا رمز عبور اشتباه است.', 'danger')
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    # بستن جلسه کاری
    open_session = WorkSession.query.filter_by(user_id=current_user.id, logout_time=None).first()
    if open_session:
        open_session.logout_time = datetime.now(IRAN_TZ)
        db.session.commit()
    logout_user()
    return redirect(url_for('auth.login'))