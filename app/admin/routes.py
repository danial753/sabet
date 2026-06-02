# app/admin/routes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file
from flask_login import login_required, current_user
from app.models import db, User, ProductionReport, StoppageReport, Factory, SystemLog, ConfigSetting
from werkzeug.security import generate_password_hash
from sqlalchemy import or_
from datetime import datetime, timezone, timedelta
from io import BytesIO
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill
from app.log_utils import log_action

admin_bp = Blueprint('admin', __name__)
IRAN_TZ = timezone(timedelta(hours=3, minutes=30))

# ------------------------------------------------------------
#   لیست کاربران (با جستجو، فیلتر، مرتب‌سازی و حذف دسته‌جمعی)
# ------------------------------------------------------------
@admin_bp.route('/users')
@login_required
def user_list():
    if not current_user.is_admin:
        flash('دسترسی غیرمجاز', 'danger')
        return redirect(url_for('reports.dashboard'))

    q = request.args.get('q', '').strip()
    role = request.args.get('role', '')
    sort = request.args.get('sort', 'id')
    order = request.args.get('order', 'asc')

    query = User.query

    if q:
        search = f"%{q}%"
        query = query.filter(or_(
            User.first_name.ilike(search),
            User.last_name.ilike(search),
            User.code.ilike(search),
            User.username.ilike(search)
        ))

    if role == 'admin':
        query = query.filter_by(is_admin=True)
    elif role == 'approver':
        query = query.filter_by(is_approver=True)
    elif role == 'operator':
        query = query.filter_by(is_admin=False, is_approver=False)

    if sort in ['id', 'first_name', 'last_name', 'code', 'username']:
        col = getattr(User, sort)
        if order == 'desc':
            query = query.order_by(col.desc())
        else:
            query = query.order_by(col.asc())
    else:
        query = query.order_by(User.id.asc())

    users = query.all()
    return render_template('admin/user_list.html', users=users, q=q, role=role, sort=sort, order=order)

# ------------------------------------------------------------
#   ایجاد کاربر جدید
# ------------------------------------------------------------
@admin_bp.route('/users/create', methods=['GET', 'POST'])
@login_required
def user_create():
    if not current_user.is_admin:
        flash('دسترسی غیرمجاز', 'danger')
        return redirect(url_for('reports.dashboard'))

    factories = Factory.query.all()

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        code = request.form.get('code')
        factory_id = request.form.get('factory_id', type=int)
        is_approver = request.form.get('is_approver') == 'on'

        if not all([username, password, first_name, last_name, code, factory_id]):
            flash('همه فیلدها الزامی هستند.', 'danger')
            return render_template('admin/user_create.html', factories=factories)

        if User.query.filter_by(username=username).first():
            flash('این نام کاربری قبلاً ثبت شده است.', 'danger')
            return render_template('admin/user_create.html', factories=factories)

        if User.query.filter_by(code=code).first():
            flash('این کد قبلاً ثبت شده است.', 'danger')
            return render_template('admin/user_create.html', factories=factories)

        new_user = User(
            username=username,
            password=generate_password_hash(password),
            first_name=first_name,
            last_name=last_name,
            code=code,
            is_admin=False,
            is_approver=is_approver,
            factory_id=factory_id
        )
        db.session.add(new_user)
        db.session.commit()
        log_action(current_user, 'ایجاد کاربر', f'کاربر {username} با کد {code} در کارخانه {new_user.factory.name} ایجاد شد')
        flash('کاربر جدید با موفقیت ایجاد شد.', 'success')
        return redirect(url_for('admin.user_list'))

    return render_template('admin/user_create.html', factories=factories)

# ------------------------------------------------------------
#   ویرایش کاربر
# ------------------------------------------------------------
@admin_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
def user_edit(user_id):
    if not current_user.is_admin:
        flash('دسترسی غیرمجاز', 'danger')
        return redirect(url_for('reports.dashboard'))

    user = User.query.get(user_id)
    if not user:
        flash('کاربر مورد نظر یافت نشد.', 'danger')
        return redirect(url_for('admin.user_list'))

    factories = Factory.query.all()

    if request.method == 'POST':
        username = request.form.get('username')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        code = request.form.get('code')
        factory_id = request.form.get('factory_id', type=int)
        password = request.form.get('password')
        is_approver = request.form.get('is_approver') == 'on'

        if not all([username, first_name, last_name, code, factory_id]):
            flash('همه فیلدها به جز رمز عبور الزامی هستند.', 'danger')
            return render_template('admin/user_edit.html', user=user, factories=factories)

        if User.query.filter(User.username == username, User.id != user.id).first():
            flash('این نام کاربری قبلاً توسط کاربر دیگری ثبت شده است.', 'danger')
            return render_template('admin/user_edit.html', user=user, factories=factories)
        if User.query.filter(User.code == code, User.id != user.id).first():
            flash('این کد قبلاً توسط کاربر دیگری ثبت شده است.', 'danger')
            return render_template('admin/user_edit.html', user=user, factories=factories)

        user.username = username
        user.first_name = first_name
        user.last_name = last_name
        user.code = code
        user.factory_id = factory_id
        user.is_approver = is_approver
        if password:
            user.password = generate_password_hash(password)
        db.session.commit()
        log_action(current_user, 'ویرایش کاربر', f'کاربر {username} با کد {code} ویرایش شد')
        flash('اطلاعات کاربر با موفقیت به‌روزرسانی شد.', 'success')
        return redirect(url_for('admin.user_list'))

    return render_template('admin/user_edit.html', user=user, factories=factories)

# ------------------------------------------------------------
#   حذف کاربر (تکی)
# ------------------------------------------------------------
@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
def user_delete(user_id):
    if not current_user.is_admin:
        flash('دسترسی غیرمجاز', 'danger')
        return redirect(url_for('reports.dashboard'))

    user = User.query.get(user_id)
    if not user:
        flash('کاربر مورد نظر یافت نشد.', 'danger')
        return redirect(url_for('admin.user_list'))

    if user.id == current_user.id:
        flash('نمی‌توانید حساب کاربری خود را حذف کنید.', 'danger')
        return redirect(url_for('admin.user_list'))

    username = user.username
    ProductionReport.query.filter_by(user_id=user.id).delete()
    StoppageReport.query.filter_by(user_id=user.id).delete()
    db.session.delete(user)
    db.session.commit()
    log_action(current_user, 'حذف کاربر', f'کاربر {username} حذف شد')
    flash('کاربر با موفقیت حذف شد.', 'success')
    return redirect(url_for('admin.user_list'))

# ------------------------------------------------------------
#   حذف دسته‌جمعی کاربران
# ------------------------------------------------------------
@admin_bp.route('/users/delete-multiple', methods=['POST'])
@login_required
def user_delete_multiple():
    if not current_user.is_admin:
        flash('دسترسی غیرمجاز', 'danger')
        return redirect(url_for('reports.dashboard'))

    user_ids = request.form.getlist('user_ids')
    if not user_ids:
        flash('هیچ کاربری انتخاب نشده است.', 'warning')
        return redirect(url_for('admin.user_list'))

    try:
        ids = [int(uid) for uid in user_ids]
    except ValueError:
        flash('شناسه‌های نامعتبر', 'danger')
        return redirect(url_for('admin.user_list'))

    users_to_delete = User.query.filter(User.id.in_(ids), User.id != current_user.id).all()
    names = [u.username for u in users_to_delete]
    for user in users_to_delete:
        ProductionReport.query.filter_by(user_id=user.id).delete()
        StoppageReport.query.filter_by(user_id=user.id).delete()
        db.session.delete(user)

    db.session.commit()
    log_action(current_user, 'حذف دسته‌جمعی کاربران', f'{len(users_to_delete)} کاربر حذف شدند: {", ".join(names)}')
    flash(f'{len(users_to_delete)} کاربر با موفقیت حذف شد.', 'success')
    return redirect(url_for('admin.user_list'))

# ------------------------------------------------------------
#   مشاهده گزارش‌های یک کاربر (برای ادمین)
# ------------------------------------------------------------
@admin_bp.route('/view-reports', methods=['GET', 'POST'])
@login_required
def view_user_reports():
    if not current_user.is_admin:
        flash('دسترسی غیرمجاز', 'danger')
        return redirect(url_for('reports.dashboard'))

    user = None
    cnc_reports = []
    manall_reports = []
    stoppage_reports = []
    start_date = end_date = None

    if request.method == 'POST':
        code = request.form.get('user_code')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')

        if code:
            user = User.query.filter_by(code=code).first()
            if not user:
                flash('کاربری با این کد یافت نشد.', 'danger')
            else:
                prod_base = ProductionReport.query.filter_by(user_id=user.id)
                stop_base = StoppageReport.query.filter_by(user_id=user.id)

                if start_date:
                    try:
                        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                        prod_base = prod_base.filter(ProductionReport.date >= start_dt)
                        stop_base = stop_base.filter(StoppageReport.date >= start_dt)
                    except ValueError:
                        flash('فرمت تاریخ شروع نامعتبر است.', 'danger')
                if end_date:
                    try:
                        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
                        end_dt = end_dt.replace(hour=23, minute=59, second=59)
                        prod_base = prod_base.filter(ProductionReport.date <= end_dt)
                        stop_base = stop_base.filter(StoppageReport.date <= end_dt)
                    except ValueError:
                        flash('فرمت تاریخ پایان نامعتبر است.', 'danger')

                cnc_reports = prod_base.filter_by(type='CNC').order_by(ProductionReport.date.desc()).all()
                manall_reports = prod_base.filter_by(type='ManAll').order_by(ProductionReport.date.desc()).all()
                stoppage_reports = stop_base.order_by(StoppageReport.date.desc()).all()
        else:
            flash('لطفاً کد کاربر را وارد کنید.', 'warning')

    return render_template('admin/view_user_reports.html',
                           user=user,
                           cnc_reports=cnc_reports,
                           manall_reports=manall_reports,
                           stoppage_reports=stoppage_reports,
                           start_date=start_date,
                           end_date=end_date)

# ------------------------------------------------------------
#   دانلود فایل اکسل از گزارش‌های کاربر
# ------------------------------------------------------------
@admin_bp.route('/download-reports-excel', methods=['POST'])
@login_required
def download_user_reports_excel():
    if not current_user.is_admin:
        flash('دسترسی غیرمجاز', 'danger')
        return redirect(url_for('reports.dashboard'))

    code = request.form.get('user_code')
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')

    user = User.query.filter_by(code=code).first() if code else None
    if not user:
        flash('کاربری با این کد یافت نشد.', 'danger')
        return redirect(url_for('admin.view_user_reports'))

    prod_base = ProductionReport.query.filter_by(user_id=user.id)
    stop_base = StoppageReport.query.filter_by(user_id=user.id)

    if start_date:
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            prod_base = prod_base.filter(ProductionReport.date >= start_dt)
            stop_base = stop_base.filter(StoppageReport.date >= start_dt)
        except ValueError:
            pass
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            end_dt = end_dt.replace(hour=23, minute=59, second=59)
            prod_base = prod_base.filter(ProductionReport.date <= end_dt)
            stop_base = stop_base.filter(StoppageReport.date <= end_dt)
        except ValueError:
            pass

    cnc_reports = prod_base.filter_by(type='CNC').order_by(ProductionReport.date.desc()).all()
    manall_reports = prod_base.filter_by(type='ManAll').order_by(ProductionReport.date.desc()).all()
    stoppage_reports = stop_base.order_by(StoppageReport.date.desc()).all()

    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    header_font = Font(bold=True, color='FFFFFF')
    header_fill = PatternFill(start_color='343a40', end_color='343a40', fill_type='solid')
    wrap_alignment = Alignment(wrap_text=True)

    def add_header(ws, headers):
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = wrap_alignment

    # برگه اطلاعات کاربر
    ws_info = wb.create_sheet('اطلاعات کاربر')
    info_data = [
        ('کد کاربری', user.code),
        ('نام', user.first_name),
        ('نام خانوادگی', user.last_name),
        ('نام کامل', user.full_name),
        ('نام کاربری', user.username),
        ('کارخانه', user.factory.name if user.factory else '-'),
        ('ادمین', 'بله' if user.is_admin else 'خیر'),
        ('تأییدکننده', 'بله' if user.is_approver else 'خیر'),
        ('تاریخ گزارش', datetime.now(IRAN_TZ).strftime('%Y-%m-%d %H:%M'))
    ]
    for i, (key, value) in enumerate(info_data, 1):
        ws_info.cell(row=i, column=1, value=key).font = Font(bold=True)
        ws_info.cell(row=i, column=2, value=value)
    ws_info.column_dimensions['A'].width = 20
    ws_info.column_dimensions['B'].width = 30

    # برگه CNC
    ws_cnc = wb.create_sheet('CNC')
    headers_cnc = ['تاریخ ثبت', 'شیفت', 'قطعه', 'سایز', 'کد دستگاه', 'مرحله کاری', 'تعداد', 'شروع', 'پایان', 'مدت واقعی', 'زمان مورد انتظار']
    add_header(ws_cnc, headers_cnc)
    for i, r in enumerate(cnc_reports, 2):
        ws_cnc.cell(row=i, column=1, value=r.date.strftime('%Y-%m-%d %H:%M'))
        ws_cnc.cell(row=i, column=2, value=r.shift_fa)
        ws_cnc.cell(row=i, column=3, value=r.product_name)
        ws_cnc.cell(row=i, column=4, value=r.part_size)
        ws_cnc.cell(row=i, column=5, value=r.machine_code)
        ws_cnc.cell(row=i, column=6, value=r.operation_stage_code)
        ws_cnc.cell(row=i, column=7, value=r.quantity)
        ws_cnc.cell(row=i, column=8, value=r.start_time.strftime('%Y-%m-%d %H:%M:%S') if r.start_time else '')
        ws_cnc.cell(row=i, column=9, value=r.end_time.strftime('%Y-%m-%d %H:%M:%S') if r.end_time else '')
        ws_cnc.cell(row=i, column=10, value=r.duration or '')
        ws_cnc.cell(row=i, column=11, value=r.expected_duration_formatted or '')

    # برگه Manual
    ws_man = wb.create_sheet('Manual')
    headers_man = ['تاریخ ثبت', 'شیفت', 'قطعه', 'کد دستگاه', 'مرحله کاری', 'عنوان کار', 'تعداد', 'شروع', 'پایان', 'مدت واقعی', 'زمان مورد انتظار']
    add_header(ws_man, headers_man)
    for i, r in enumerate(manall_reports, 2):
        ws_man.cell(row=i, column=1, value=r.date.strftime('%Y-%m-%d %H:%M'))
        ws_man.cell(row=i, column=2, value=r.shift_fa)
        ws_man.cell(row=i, column=3, value=r.product_name)
        ws_man.cell(row=i, column=4, value=r.machine_code)
        ws_man.cell(row=i, column=5, value=r.operation_stage_code)
        ws_man.cell(row=i, column=6, value=r.manual_title or '')
        ws_man.cell(row=i, column=7, value=r.quantity)
        ws_man.cell(row=i, column=8, value=r.start_time.strftime('%Y-%m-%d %H:%M:%S') if r.start_time else '')
        ws_man.cell(row=i, column=9, value=r.end_time.strftime('%Y-%m-%d %H:%M:%S') if r.end_time else '')
        ws_man.cell(row=i, column=10, value=r.duration or '')
        ws_man.cell(row=i, column=11, value=r.expected_duration_formatted or '')

    # برگه توقف
    ws_stop = wb.create_sheet('توقف')
    headers_stop = ['تاریخ ثبت', 'کد دستگاه', 'کد توقف', 'دلیل', 'شروع', 'پایان (راه‌اندازی)', 'مدت واقعی', 'زمان مورد انتظار', 'اختلاف']
    add_header(ws_stop, headers_stop)
    for i, r in enumerate(stoppage_reports, 2):
        ws_stop.cell(row=i, column=1, value=r.date.strftime('%Y-%m-%d %H:%M'))
        ws_stop.cell(row=i, column=2, value=r.machine_code)
        ws_stop.cell(row=i, column=3, value=r.stop_code)
        ws_stop.cell(row=i, column=4, value=r.reason or '')
        ws_stop.cell(row=i, column=5, value=r.start_time.strftime('%Y-%m-%d %H:%M:%S') if r.start_time else '')
        ws_stop.cell(row=i, column=6, value=r.end_time.strftime('%Y-%m-%d %H:%M:%S') if r.end_time else '')
        ws_stop.cell(row=i, column=7, value=r.duration or '')
        ws_stop.cell(row=i, column=8, value=r.expected_duration_formatted or '')
        ws_stop.cell(row=i, column=9, value=r.time_diff_formatted or '')

    for ws in [ws_info, ws_cnc, ws_man, ws_stop]:
        for col in ws.columns:
            max_length = 0
            col_letter = col[0].column_letter
            for cell in col:
                if cell.value:
                    max_length = max(max_length, len(str(cell.value)))
            ws.column_dimensions[col_letter].width = min(max_length + 5, 40)

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    filename = f"reports_{user.code}_{user.last_name}_{datetime.now(IRAN_TZ).strftime('%Y%m%d_%H%M%S')}.xlsx"
    log_action(current_user, 'دانلود گزارش کاربر', f'گزارش کاربر {user.code} دانلود شد')
    return send_file(output,
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                     as_attachment=True,
                     download_name=filename)

# ------------------------------------------------------------
#   گزارش پیشرفته (فیلترهای ترکیبی)
# ------------------------------------------------------------
@admin_bp.route('/advanced-report', methods=['GET', 'POST'])
@login_required
def advanced_report():
    if not current_user.is_admin:
        flash('دسترسی غیرمجاز', 'danger')
        return redirect(url_for('reports.dashboard'))

    # لیست‌های منحصربه‌فرد برای فیلترها
    machines = [r[0] for r in db.session.query(ProductionReport.machine_code).distinct()]
    products = [r[0] for r in db.session.query(ProductionReport.product_name).distinct()]
    reports = []

    if request.method == 'POST':
        machine = request.form.get('machine')
        product = request.form.get('product')
        shift = request.form.get('shift')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')

        query = ProductionReport.query
        if machine:
            query = query.filter_by(machine_code=machine)
        if product:
            query = query.filter_by(product_name=product)
        if shift:
            query = query.filter_by(shift=shift)
        if start_date:
            try:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                query = query.filter(ProductionReport.date >= start_dt)
            except ValueError:
                pass
        if end_date:
            try:
                end_dt = datetime.strptime(end_date, '%Y-%m-%d')
                end_dt = end_dt.replace(hour=23, minute=59, second=59)
                query = query.filter(ProductionReport.date <= end_dt)
            except ValueError:
                pass
        reports = query.order_by(ProductionReport.date.desc()).all()

    return render_template('admin/advanced_report.html',
                           machines=machines,
                           products=products,
                           reports=reports)

# ------------------------------------------------------------
#   لاگ سیستم
# ------------------------------------------------------------
@admin_bp.route('/system-logs')
@login_required
def system_logs():
    if not current_user.is_admin:
        flash('دسترسی غیرمجاز', 'danger')
        return redirect(url_for('reports.dashboard'))
    page = request.args.get('page', 1, type=int)
    logs = SystemLog.query.order_by(SystemLog.timestamp.desc()).paginate(page=page, per_page=50)
    return render_template('admin/system_logs.html', logs=logs)

# ------------------------------------------------------------
#   پیکربندی (تنظیمات)
# ------------------------------------------------------------
@admin_bp.route('/config', methods=['GET', 'POST'])
@login_required
def config():
    if not current_user.is_admin:
        flash('دسترسی غیرمجاز', 'danger')
        return redirect(url_for('reports.dashboard'))

    if request.method == 'POST':
        warning_threshold = request.form.get('warning_threshold')
        if warning_threshold:
            setting = ConfigSetting.query.filter_by(key='warning_threshold').first()
            if setting:
                setting.value = warning_threshold
            else:
                db.session.add(ConfigSetting(key='warning_threshold', value=warning_threshold))
            db.session.commit()
            log_action(current_user, 'تغییر تنظیمات', f'حد آستانه هشدار به {warning_threshold}% تغییر یافت')
            flash('تنظیمات ذخیره شد.', 'success')
        return redirect(url_for('admin.config'))

    setting = ConfigSetting.query.filter_by(key='warning_threshold').first()
    current_threshold = setting.value if setting else '5'
    return render_template('admin/config.html', current_threshold=current_threshold)