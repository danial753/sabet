# app/admin_report/routes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file
from flask_login import login_required, current_user
from app.models import db, User, ProductionReport, StoppageReport
from datetime import datetime, timezone, timedelta
from io import BytesIO
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from persiantools.jdatetime import JalaliDate
from datetime import datetime as dt_datetime

admin_report_bp = Blueprint('admin_report', __name__)
IRAN_TZ = timezone(timedelta(hours=3, minutes=30))

@admin_report_bp.route('/general-report', methods=['GET'])
@login_required
def general_report_form():
    if not current_user.is_admin:
        flash('دسترسی غیرمجاز', 'danger')
        return redirect(url_for('reports.dashboard'))
    return render_template('admin/general_report.html')

@admin_report_bp.route('/general-report/download', methods=['POST'])
@login_required
def general_report_download():
    if not current_user.is_admin:
        flash('دسترسی غیرمجاز', 'danger')
        return redirect(url_for('reports.dashboard'))

    user_code = request.form.get('user_code', '').strip()
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')

    prod_query = ProductionReport.query
    stop_query = StoppageReport.query

    if user_code:
        user = User.query.filter_by(code=user_code).first()
        if not user:
            flash('کاربری با این کد یافت نشد.', 'danger')
            return redirect(url_for('admin_report.general_report_form'))
        prod_query = prod_query.filter_by(user_id=user.id)
        stop_query = stop_query.filter_by(user_id=user.id)

    if start_date:
        try:
            start_dt = JalaliDate.strptime(start_date, '%Y-%m-%d').to_gregorian()
            start_dt = dt_datetime.combine(start_dt, dt_datetime.min.time())
            prod_query = prod_query.filter(ProductionReport.date >= start_dt)
            stop_query = stop_query.filter(StoppageReport.date >= start_dt)
        except ValueError:
            flash('فرمت تاریخ شروع نامعتبر است.', 'danger')
            return redirect(url_for('admin_report.general_report_form'))

    if end_date:
        try:
            end_dt = JalaliDate.strptime(end_date, '%Y-%m-%d').to_gregorian()
            end_dt = dt_datetime.combine(end_dt, dt_datetime.max.time())
            prod_query = prod_query.filter(ProductionReport.date <= end_dt)
            stop_query = stop_query.filter(StoppageReport.date <= end_dt)
        except ValueError:
            flash('فرمت تاریخ پایان نامعتبر است.', 'danger')
            return redirect(url_for('admin_report.general_report_form'))

    cnc_reports = prod_query.filter_by(type='CNC').order_by(ProductionReport.date.asc()).all()
    manall_reports = prod_query.filter_by(type='ManAll').order_by(ProductionReport.date.asc()).all()
    stoppage_reports = stop_query.order_by(StoppageReport.date.asc()).all()

    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    # استایل‌های حرفه‌ای
    header_font = Font(name='B Nazanin', bold=True, color='FFFFFF', size=11)
    header_fill = PatternFill(start_color='1a3a5c', end_color='1a3a5c', fill_type='solid')
    header_alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    cell_alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    thin_border = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin')
    )

    HEADERS = [
        'کد پرسنلی', 'نام اپراتور', 'نوع شیفت', 'تاریخ شیفت',
        'نام قطعه تولیدی', 'سایز قطعه', 'عنوان مرحله', 'کد دستگاه',
        'جمع کل زمان تولید (ثانیه)', 'تعداد واقعی تولید', 'تعداد در حال بررسی', 'تعداد انبار',
        'زمان صرف شده', 'زمان توقف (دقیقه)', 'کد توقف', 'علت توقف'
    ]

    def add_header(ws):
        for col, header in enumerate(HEADERS, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
            cell.border = thin_border
        ws.freeze_panes = 'A2'

    def auto_width(ws):
        for col in ws.columns:
            max_length = 0
            col_letter = col[0].column_letter
            for cell in col:
                if cell.value:
                    max_length = max(max_length, len(str(cell.value)))
            ws.column_dimensions[col_letter].width = min(max_length + 5, 40)

    def write_row(ws, row, data_dict):
        mapping = {
            'کد پرسنلی': 'operator_code', 'نام اپراتور': 'operator_name',
            'نوع شیفت': 'shift', 'تاریخ شیفت': 'shift_date',
            'نام قطعه تولیدی': 'product_name', 'سایز قطعه': 'part_size',
            'عنوان مرحله': 'stage_title', 'کد دستگاه': 'machine_code',
            'جمع کل زمان تولید (ثانیه)': 'total_production_time_sec',
            'تعداد واقعی تولید': 'actual_quantity',
            'تعداد در حال بررسی': 'inspection_quantity',
            'تعداد انبار': 'warehouse_quantity',
            'زمان صرف شده': 'time_spent', 'زمان توقف (دقیقه)': 'stop_duration_min',
            'کد توقف': 'stop_code', 'علت توقف': 'stop_reason'
        }
        for col, header in enumerate(HEADERS, 1):
            value = data_dict.get(mapping[header], '-')
            cell = ws.cell(row=row, column=col, value=value)
            cell.alignment = cell_alignment
            cell.border = thin_border
            cell.font = Font(name='B Nazanin', size=10)

    # ---------- CNC ----------
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
            'stage_title': r.manual_title or r.operation_stage_code or '-',
            'machine_code': r.machine_code or '-',
            'total_production_time_sec': r.duration_seconds or 0,
            'actual_quantity': r.approved_quantity if (r.is_approved and r.approved_quantity is not None) else (r.quantity or 0),
            'inspection_quantity': r.inspection_quantity if r.inspection_quantity is not None else '-',
            'warehouse_quantity': r.warehouse_quantity if r.warehouse_quantity is not None else '-',
            'time_spent': r.duration_seconds or 0,
            'stop_duration_min': 0, 'stop_code': '-', 'stop_reason': '-'
        }
        write_row(ws_cnc, row, data)
        row += 1
    auto_width(ws_cnc)

    # ---------- Manual ----------
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
            'part_size': '-',
            'stage_title': r.manual_title or r.operation_stage_code or '-',
            'machine_code': r.machine_code or '-',
            'total_production_time_sec': r.duration_seconds or 0,
            'actual_quantity': r.approved_quantity if (r.is_approved and r.approved_quantity is not None) else (r.quantity or 0),
            'inspection_quantity': r.inspection_quantity if r.inspection_quantity is not None else '-',
            'warehouse_quantity': r.warehouse_quantity if r.warehouse_quantity is not None else '-',
            'time_spent': r.duration_seconds or 0,
            'stop_duration_min': 0, 'stop_code': '-', 'stop_reason': '-'
        }
        write_row(ws_man, row, data)
        row += 1
    auto_width(ws_man)

    # ---------- توقف ----------
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
            'shift': '-', 'shift_date': r.date.strftime('%Y-%m-%d %H:%M'),
            'product_name': '-', 'part_size': '-', 'stage_title': '-',
            'machine_code': r.machine_code or '-',
            'total_production_time_sec': 0, 'actual_quantity': 0,
            'inspection_quantity': '-', 'warehouse_quantity': '-',
            'time_spent': 0,
            'stop_duration_min': duration_min,
            'stop_code': r.stop_code or '-', 'stop_reason': r.reason or '-'
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