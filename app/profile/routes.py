# app/profile/routes.py
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models import db, User
from werkzeug.security import check_password_hash, generate_password_hash

profile_bp = Blueprint('profile', __name__)

@profile_bp.route('/')
@login_required
def view():
    return render_template('profile/view.html', user=current_user)

@profile_bp.route('/edit', methods=['GET', 'POST'])
@login_required
def edit():
    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        code = request.form.get('code')

        if not all([first_name, last_name, code]):
            flash('همه فیلدها الزامی هستند.', 'danger')
            return render_template('profile/edit.html')

        if code != current_user.code and User.query.filter_by(code=code).first():
            flash('این کد قبلاً توسط کاربر دیگری ثبت شده است.', 'danger')
            return render_template('profile/edit.html')

        current_user.first_name = first_name
        current_user.last_name = last_name
        current_user.code = code
        db.session.commit()
        flash('پروفایل با موفقیت به‌روزرسانی شد.', 'success')
        return redirect(url_for('profile.view'))

    return render_template('profile/edit.html')

@profile_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        if not all([current_password, new_password, confirm_password]):
            flash('همه فیلدها الزامی هستند.', 'danger')
            return render_template('profile/change_password.html')

        if not check_password_hash(current_user.password, current_password):
            flash('رمز عبور فعلی اشتباه است.', 'danger')
            return render_template('profile/change_password.html')

        if new_password != confirm_password:
            flash('رمز عبور جدید با تکرار آن مطابقت ندارد.', 'danger')
            return render_template('profile/change_password.html')

        current_user.password = generate_password_hash(new_password)
        db.session.commit()
        flash('رمز عبور با موفقیت تغییر یافت.', 'success')
        return redirect(url_for('profile.view'))

    return render_template('profile/change_password.html')