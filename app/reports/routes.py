# app/reports/routes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.models import db, ProductionReport, StoppageReport
from app.data_loader import get_cnc_lists, get_manall_lists, get_stoppage_lists
from app import cache
from datetime import datetime, timezone, timedelta

reports_bp = Blueprint('reports', __name__)
IRAN_TZ = timezone(timedelta(hours=3, minutes=30))

def can_operate():
    """کاربر عادی (اپراتور) که می‌تواند گزارش ثبت کند."""
    return current_user.is_authenticated and current_user.is_operator

def get_factory_name():
    """نام کارخانه کاربر فعلی برای بارگذاری لیست‌های صحیح."""
    if current_user.factory:
        return current_user.factory.name
    return 'default'

# ------------------------------------------------------------
#           CNC start & stop API endpoints
# ------------------------------------------------------------
@reports_bp.route('/cnc/start', methods=['POST'])
@login_required
def cnc_start():
    if not can_operate():
        return jsonify({'error': 'شما مجاز به ثبت تولید نیستید.'}), 403
    data = request.get_json()
    if not data:
        return jsonify({'error': 'داده‌ای ارسال نشده'}), 400

    product_name = data.get('product_name')
    quantity = data.get('quantity')
    shift = data.get('shift')
    part_size = data.get('part_size')
    machine_code = data.get('machine_code')
    operation_stage_code = data.get('operation_stage_code')
    expected_hours = data.get('expected_hours', 0)
    expected_minutes = data.get('expected_minutes', 0)
    expected_seconds = data.get('expected_seconds', 0)

    if not all([product_name, quantity, shift, part_size, machine_code, operation_stage_code]):
        return jsonify({'error': 'همه فیلدها الزامی هستند'}), 400

    try:
        qty = int(quantity)
        total_expected = int(expected_hours) * 3600 + int(expected_minutes) * 60 + int(expected_seconds)
    except ValueError:
        return jsonify({'error': 'مقادیر عددی نامعتبر'}), 400

    active = ProductionReport.query.filter_by(user_id=current_user.id, type='CNC', end_time=None).first()
    if active:
        return jsonify({'error': 'شما یک کار CNC فعال دارید. لطفاً ابتدا آن را متوقف کنید.', 'active_report_id': active.id}), 400

    now = datetime.now(IRAN_TZ)
    report = ProductionReport(
        user_id=current_user.id, type='CNC',
        product_name=product_name, quantity=qty, shift=shift,
        part_size=part_size, machine_code=machine_code,
        operation_stage_code=operation_stage_code,
        start_time=now,
        expected_duration_seconds=total_expected
    )
    db.session.add(report)
    db.session.commit()
    return jsonify({'report_id': report.id, 'start_time': now.strftime('%Y-%m-%d %H:%M:%S')}), 201

@reports_bp.route('/cnc/stop/<int:report_id>', methods=['POST'])
@login_required
def cnc_stop(report_id):
    report = ProductionReport.query.get(report_id)
    if not report or report.user_id != current_user.id:
        return jsonify({'error': 'گزارش یافت نشد'}), 404
    if report.end_time:
        return jsonify({'error': 'قبلاً متوقف شده'}), 400
    report.end_time = datetime.now(IRAN_TZ)
    db.session.commit()
    return jsonify({
        'end_time': report.end_time.strftime('%Y-%m-%d %H:%M:%S'),
        'duration': report.duration,
        'expected_duration': report.expected_duration_formatted,
        'warning': report.duration_warning
    }), 200

# ------------------------------------------------------------
#           ManAll start & stop API endpoints
# ------------------------------------------------------------
@reports_bp.route('/manall/start', methods=['POST'])
@login_required
def manall_start():
    if not can_operate():
        return jsonify({'error': 'شما مجاز به ثبت تولید نیستید.'}), 403
    data = request.get_json()
    if not data:
        return jsonify({'error': 'داده‌ای ارسال نشده'}), 400

    product_name = data.get('product_name')
    quantity = data.get('quantity')
    shift = data.get('shift')
    machine_code = data.get('machine_code')
    operation_stage_code = data.get('operation_stage_code')
    manual_title = data.get('manual_title', '')
    expected_hours = data.get('expected_hours', 0)
    expected_minutes = data.get('expected_minutes', 0)
    expected_seconds = data.get('expected_seconds', 0)

    if not all([product_name, quantity, shift, machine_code, operation_stage_code]):
        return jsonify({'error': 'همه فیلدهای اجباری را پر کنید'}), 400

    try:
        qty = int(quantity)
        total_expected = int(expected_hours) * 3600 + int(expected_minutes) * 60 + int(expected_seconds)
    except ValueError:
        return jsonify({'error': 'مقادیر عددی نامعتبر'}), 400

    active = ProductionReport.query.filter_by(user_id=current_user.id, type='ManAll', end_time=None).first()
    if active:
        return jsonify({'error': 'شما یک کار ManAll فعال دارید. لطفاً ابتدا آن را متوقف کنید.', 'active_report_id': active.id}), 400

    now = datetime.now(IRAN_TZ)
    report = ProductionReport(
        user_id=current_user.id, type='ManAll',
        product_name=product_name, quantity=qty, shift=shift,
        part_size='',
        machine_code=machine_code,
        operation_stage_code=operation_stage_code,
        manual_title=manual_title,
        start_time=now,
        expected_duration_seconds=total_expected
    )
    db.session.add(report)
    db.session.commit()
    return jsonify({'report_id': report.id, 'start_time': now.strftime('%Y-%m-%d %H:%M:%S')}), 201

@reports_bp.route('/manall/stop/<int:report_id>', methods=['POST'])
@login_required
def manall_stop(report_id):
    report = ProductionReport.query.get(report_id)
    if not report or report.user_id != current_user.id:
        return jsonify({'error': 'گزارش یافت نشد'}), 404
    if report.end_time:
        return jsonify({'error': 'قبلاً متوقف شده'}), 400
    report.end_time = datetime.now(IRAN_TZ)
    db.session.commit()
    return jsonify({
        'end_time': report.end_time.strftime('%Y-%m-%d %H:%M:%S'),
        'duration': report.duration,
        'expected_duration': report.expected_duration_formatted,
        'warning': report.duration_warning
    }), 200

# ------------------------------------------------------------
#           Stoppage start & stop API endpoints
# ------------------------------------------------------------
@reports_bp.route('/stoppage/start', methods=['POST'])
@login_required
def stoppage_start():
    if not can_operate():
        return jsonify({'error': 'شما مجاز به ثبت توقف نیستید.'}), 403
    data = request.get_json()
    if not data:
        return jsonify({'error': 'داده‌ای ارسال نشده'}), 400

    machine_code = data.get('machine_code')
    stop_code = data.get('stop_code')
    reason = data.get('reason', '')
    expected_hours = data.get('expected_hours', 0)
    expected_minutes = data.get('expected_minutes', 0)
    expected_seconds = data.get('expected_seconds', 0)

    if not machine_code or not stop_code:
        return jsonify({'error': 'کد دستگاه و کد توقف الزامی هستند'}), 400

    try:
        total_expected = int(expected_hours) * 3600 + int(expected_minutes) * 60 + int(expected_seconds)
    except ValueError:
        total_expected = 0

    active = StoppageReport.query.filter_by(user_id=current_user.id, end_time=None).first()
    if active:
        return jsonify({'error': 'شما یک توقف فعال دارید. لطفاً ابتدا آن را متوقف کنید.', 'active_id': active.id}), 400

    now = datetime.now(IRAN_TZ)
    report = StoppageReport(
        user_id=current_user.id,
        machine_code=machine_code,
        stop_code=stop_code,
        reason=reason,
        start_time=now,
        expected_duration_seconds=total_expected
    )
    db.session.add(report)
    db.session.commit()
    return jsonify({'report_id': report.id, 'start_time': now.strftime('%Y-%m-%d %H:%M:%S')}), 201

@reports_bp.route('/stoppage/stop/<int:report_id>', methods=['POST'])
@login_required
def stoppage_stop(report_id):
    report = StoppageReport.query.get(report_id)
    if not report or report.user_id != current_user.id:
        return jsonify({'error': 'گزارش یافت نشد'}), 404
    if report.end_time:
        return jsonify({'error': 'این توقف قبلاً پایان یافته است'}), 400

    report.end_time = datetime.now(IRAN_TZ)
    db.session.commit()
    return jsonify({
        'end_time': report.end_time.strftime('%Y-%m-%d %H:%M:%S'),
        'duration': report.duration,
        'expected_duration': report.expected_duration_formatted,
        'warning': report.duration_warning
    }), 200

# ------------------------------------------------------------
#           API برای دریافت لیست‌های پیشنهادی (کش شده)
# ------------------------------------------------------------
@reports_bp.route('/api/cnc/options')
@login_required
@cache.cached(timeout=300)
def cnc_options():
    return jsonify(get_cnc_lists(get_factory_name()))

@reports_bp.route('/api/manall/options')
@login_required
@cache.cached(timeout=300)
def manall_options():
    return jsonify(get_manall_lists(get_factory_name()))

@reports_bp.route('/api/stoppage/options')
@login_required
@cache.cached(timeout=300)
def stoppage_options():
    return jsonify(get_stoppage_lists(get_factory_name()))

# ------------------------------------------------------------
#           Approver Dashboard و تأیید (فقط برای تأییدکنندگان)
# ------------------------------------------------------------
@reports_bp.route('/approver/dashboard')
@login_required
def approver_dashboard():
    if not current_user.is_approver:
        flash('دسترسی غیرمجاز', 'danger')
        return redirect(url_for('reports.dashboard'))
    reports = ProductionReport.query.filter_by(is_approved=False).order_by(ProductionReport.date.desc()).all()
    return render_template('approve_dashboard.html', reports=reports)

@reports_bp.route('/approver/approve/<int:report_id>', methods=['GET', 'POST'])
@login_required
def approve_report(report_id):
    if not current_user.is_approver:
        flash('دسترسی غیرمجاز', 'danger')
        return redirect(url_for('reports.dashboard'))

    report = ProductionReport.query.get(report_id)
    if not report:
        flash('گزارش یافت نشد.', 'danger')
        return redirect(url_for('reports.approver_dashboard'))

    if request.method == 'POST':
        approved_qty = request.form.get('approved_quantity')
        try:
            approved_qty = int(approved_qty)
        except (ValueError, TypeError):
            flash('مقدار تعداد معتبر نیست.', 'danger')
            return render_template('approve_report.html', report=report)

        report.approved_quantity = approved_qty
        report.is_approved = True
        report.approved_by_id = current_user.id
        report.approval_date = datetime.now(IRAN_TZ)
        db.session.commit()
        flash('گزارش با موفقیت تأیید شد.', 'success')
        return redirect(url_for('reports.approver_dashboard'))

    return render_template('approve_report.html', report=report)

# ------------------------------------------------------------
#                       صفحات اپراتور
# ------------------------------------------------------------
@reports_bp.route('/production', defaults={'prod_type': 'CNC'})
@reports_bp.route('/production/<string:prod_type>')
@login_required
def production(prod_type):
    if not can_operate():
        flash('شما مجاز به ثبت تولید نیستید.', 'warning')
        if current_user.is_approver:
            return redirect(url_for('reports.approver_dashboard'))
        return redirect(url_for('admin.view_user_reports'))
    if prod_type not in ['CNC', 'ManAll']:
        prod_type = 'CNC'
    reports = ProductionReport.query \
        .filter_by(type=prod_type, user_id=current_user.id) \
        .order_by(ProductionReport.date.desc()) \
        .all()
    return render_template('production.html', reports=reports, prod_type=prod_type)

@reports_bp.route('/stoppage')
@login_required
def stoppage():
    if not can_operate():
        flash('شما مجاز به ثبت توقف نیستید.', 'warning')
        if current_user.is_approver:
            return redirect(url_for('reports.approver_dashboard'))
        return redirect(url_for('admin.view_user_reports'))
    reports = StoppageReport.query \
        .filter_by(user_id=current_user.id) \
        .order_by(StoppageReport.date.desc()) \
        .all()
    return render_template('stoppage.html', reports=reports)

# ------------------------------------------------------------
#                       ریشه (داشبورد)
# ------------------------------------------------------------
@reports_bp.route('/')
@login_required
def dashboard():
    if current_user.is_admin:
        return redirect(url_for('admin.view_user_reports'))
    if current_user.is_approver:
        return redirect(url_for('reports.approver_dashboard'))
    return render_template('dashboard.html')