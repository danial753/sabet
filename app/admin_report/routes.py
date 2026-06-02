# app/admin_report/routes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file
from flask_login import login_required, current_user
from app.models import db, User, ProductionReport, StoppageReport
from datetime import datetime, timezone, timedelta
from io import BytesIO
import openpyxl
from openpyxl.styles import Font, PatternFill

admin_report_bp = Blueprint('admin_report', __name__)

IRAN_TZ = timezone(timedelta(hours=3, minutes=30))

# ------------------------------------------------------------
#   فرم درخواست گزارش جامع
# ------------------------------------------------------------
@admin_report_bp.route('/general-report', methods=['GET'])
@login_required
def general_report_form():
    if not current_user.is_admin:
        flash('دسترسی غیرمجاز', 'danger')
        return redirect(url_for('reports.dashboard'))
    return render_template('admin/general_report.html')

# ------------------------------------------------------------
#   دانلود فایل اکسل گزارش جامع (با برگه‌های جدا و ستون‌های یکسان)
# ------------------------------------------------------------
@admin_report_bp.route('/general-report/download', methods=['POST'])
@login_required
def general_report_download():
    if not current_user.is_admin:
        flash('دسترسی غیرمجاز', 'danger')
        return redirect(url_for('reports.dashboard'))

    user_code = request.form.get('user_code', '').strip()
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')

    # کوئری‌های پایه
    prod_query = ProductionReport.query
    stop_query = StoppageReport.query

    if user_code:
        user = User.query.filter_by(code=user_code).first()
        if not user:
            flash('کاربری با این کد یافت نشد.', 'danger')
            return redirect(url_for('admin_report.general_report_form'))
        prod_query = prod_query.filter_by(user_id=user.id)
        stop_query = stop_query.filter_by(user_id=user.id)

    # فیلتر تاریخ
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            prod_query = prod_query.filter(ProductionReport.date >= start_dt)
            stop_query = stop_query.filter(StoppageReport.date >= start_dt)
        except ValueError:
            flash('فرمت تاریخ شروع نامعتبر است.', 'danger')
            return redirect(url_for('admin_report.general_report_form'))
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            end_dt = end_dt.replace(hour=23, minute=59, second=59)
            prod_query = prod_query.filter(ProductionReport.date <= end_dt)
            stop_query = stop_query.filter(StoppageReport.date <= end_dt)
        except ValueError:
            flash('فرمت تاریخ پایان نامعتبر است.', 'danger')
            return redirect(url_for('admin_report.general_report_form'))

    # دریافت داده‌ها
    cnc_reports = prod_query.filter_by(type='CNC').order_by(ProductionReport.date.asc()).all()
    manall_reports = prod_query.filter_by(type='ManAll').order_by(ProductionReport.date.asc()).all()
    stoppage_reports = stop_query.order_by(StoppageReport.date.asc()).all()

    # ساخت فایل اکسل
    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    # استایل‌ها
    header_font = Font(bold=True, color='FFFFFF')
    header_fill = PatternFill(start_color='343a40', end_color='343a40', fill_type='solid')

    # ستون‌های ثابت (مطابق درخواست)
    HEADERS = [
        'کد پرسنلی اپراتور',     # 1
        'نام اپراتور',           # 2
        'نوع شیفت',              # 3
        'تاریخ شیفت',            # 4
        'نام قطعه تولیدی',       # 5
        'سایز قطعه',             # 6
        'کد فعالیت',             # 7
        'عنوان مرحله',           # 8
        'کد دستگاه',             # 9
        'جمع کل زمان تولید (ثانیه)', # 10
        'تعداد واقعی تولید',     # 11
        'زمان صرف شده',          # 12
        'زمان توقف (دقیقه)',     # 13
        'کد توقف',               # 14
        'علت توقف'               # 15
    ]

    def add_header(ws):
        for col, header in enumerate(HEADERS, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill

    def auto_width(ws):
        for col in ws.columns:
            max_length = 0
            col_letter = col[0].column_letter
            for cell in col:
                if cell.value:
                    max_length = max(max_length, len(str(cell.value)))
            ws.column_dimensions[col_letter].width = min(max_length + 5, 40)

    def write_row(ws, row, data_dict):
        ws.cell(row=row, column=1, value=data_dict.get('operator_code', '-'))
        ws.cell(row=row, column=2, value=data_dict.get('operator_name', '-'))
        ws.cell(row=row, column=3, value=data_dict.get('shift', '-'))
        ws.cell(row=row, column=4, value=data_dict.get('shift_date', '-'))
        ws.cell(row=row, column=5, value=data_dict.get('product_name', '-'))
        ws.cell(row=row, column=6, value=data_dict.get('part_size', '-'))
        ws.cell(row=row, column=7, value=data_dict.get('activity_code', '-'))
        ws.cell(row=row, column=8, value=data_dict.get('stage_title', '-'))
        ws.cell(row=row, column=9, value=data_dict.get('machine_code', '-'))
        ws.cell(row=row, column=10, value=data_dict.get('total_production_time_sec', 0))
        ws.cell(row=row, column=11, value=data_dict.get('actual_quantity', 0))
        ws.cell(row=row, column=12, value=data_dict.get('time_spent', 0))
        ws.cell(row=row, column=13, value=data_dict.get('stop_duration_min', 0))
        ws.cell(row=row, column=14, value=data_dict.get('stop_code', '-'))
        ws.cell(row=row, column=15, value=data_dict.get('stop_reason', '-'))

    # ---------- برگه CNC ----------
    ws_cnc = wb.create_sheet('CNC')
    ws_cnc.sheet_view.rightToLeft = True
    add_header(ws_cnc)
    row = 2
    for r in cnc_reports:
        user = r.user
        data = {
            'operator_code': user.code if user else '-',
            'operator_name': user.full_name if user else '-',
            'shift': r.shift_fa or '-',
            'shift_date': r.date.strftime('%Y-%m-%d %H:%M'),
            'product_name': r.product_name or '-',
            'part_size': r.part_size or '-',
            'activity_code': r.operation_stage_code or '-',
            'stage_title': r.manual_title or '-',
            'machine_code': r.machine_code or '-',
            'total_production_time_sec': r.duration_seconds or 0,
            'actual_quantity': r.approved_quantity if (r.is_approved and r.approved_quantity is not None) else (r.quantity or 0),
            'time_spent': r.duration_seconds or 0,
            'stop_duration_min': 0,
            'stop_code': '-',
            'stop_reason': '-'
        }
        write_row(ws_cnc, row, data)
        row += 1
    auto_width(ws_cnc)

    # ---------- برگه Manual ----------
    ws_man = wb.create_sheet('Manual')
    ws_man.sheet_view.rightToLeft = True
    add_header(ws_man)
    row = 2
    for r in manall_reports:
        user = r.user
        data = {
            'operator_code': user.code if user else '-',
            'operator_name': user.full_name if user else '-',
            'shift': r.shift_fa or '-',
            'shift_date': r.date.strftime('%Y-%m-%d %H:%M'),
            'product_name': r.product_name or '-',
            'part_size': '-',              # Manual سایز قطعه ندارد
            'activity_code': r.operation_stage_code or '-',
            'stage_title': r.manual_title or '-',
            'machine_code': r.machine_code or '-',
            'total_production_time_sec': r.duration_seconds or 0,
            'actual_quantity': r.approved_quantity if (r.is_approved and r.approved_quantity is not None) else (r.quantity or 0),
            'time_spent': r.duration_seconds or 0,
            'stop_duration_min': 0,
            'stop_code': '-',
            'stop_reason': '-'
        }
        write_row(ws_man, row, data)
        row += 1
    auto_width(ws_man)

    # ---------- برگه توقف ----------
    ws_stop = wb.create_sheet('توقف')
    ws_stop.sheet_view.rightToLeft = True
    add_header(ws_stop)
    row = 2
    for r in stoppage_reports:
        user = User.query.get(r.user_id) if r.user_id else None
        duration_min = round((r.duration_seconds or 0) / 60, 2)
        data = {
            'operator_code': user.code if user else '-',
            'operator_name': user.full_name if user else '-',
            'shift': '-',                # توقف شیفت ندارد
            'shift_date': r.date.strftime('%Y-%m-%d %H:%M'),
            'product_name': '-',
            'part_size': '-',
            'activity_code': '-',
            'stage_title': '-',
            'machine_code': r.machine_code or '-',
            'total_production_time_sec': 0,
            'actual_quantity': 0,
            'time_spent': 0,
            'stop_duration_min': duration_min,
            'stop_code': r.stop_code or '-',
            'stop_reason': r.reason or '-'
        }
        write_row(ws_stop, row, data)
        row += 1
    auto_width(ws_stop)

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    filename = f"general_report_{datetime.now(IRAN_TZ).strftime('%Y%m%d_%H%M%S')}.xlsx"
    return send_file(output,
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                     as_attachment=True,
                     download_name=filename)