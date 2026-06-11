from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from app.models import db, ProductionReport, StoppageReport
from sqlalchemy import func
from datetime import datetime, timedelta

analytics_bp = Blueprint('analytics', __name__)

@analytics_bp.route('/dashboard')
@login_required
def dashboard():
    if not current_user.is_admin:
        flash('دسترسی غیرمجاز', 'danger')
        return redirect(url_for('reports.dashboard'))
    return render_template('admin/dashboard.html')

@analytics_bp.route('/api/dashboard-data')
@login_required
def dashboard_data():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    shift = request.args.get('shift')
    machine = request.args.get('machine')
    product = request.args.get('product')

    prod_query = ProductionReport.query
    stop_query = StoppageReport.query

    if start_date:
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            prod_query = prod_query.filter(ProductionReport.date >= start_dt)
            stop_query = stop_query.filter(StoppageReport.date >= start_dt)
        except ValueError:
            pass
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            end_dt = end_dt.replace(hour=23, minute=59, second=59)
            prod_query = prod_query.filter(ProductionReport.date <= end_dt)
            stop_query = stop_query.filter(StoppageReport.date <= end_dt)
        except ValueError:
            pass
    if shift:
        prod_query = prod_query.filter(ProductionReport.shift == shift)
    if machine:
        prod_query = prod_query.filter(ProductionReport.machine_code == machine)
        stop_query = stop_query.filter(StoppageReport.machine_code == machine)
    if product:
        prod_query = prod_query.filter(ProductionReport.product_name == product)

    total_production = prod_query.count()

    total_prod_time = db.session.query(func.sum(
        (func.julianday(ProductionReport.end_time) - func.julianday(ProductionReport.start_time)) * 86400
    )).filter(ProductionReport.end_time != None, ProductionReport.id.in_(
        [r.id for r in prod_query.all()]
    )).scalar() or 0
    avg_cycle_time = round(total_prod_time / total_production, 1) if total_production else 0

    shift_data = db.session.query(ProductionReport.shift, func.count(ProductionReport.id)) \
        .filter(ProductionReport.id.in_([r.id for r in prod_query.all()])) \
        .group_by(ProductionReport.shift).all()
    shift_counts = {row[0]: row[1] for row in shift_data}
    shift_labels = {'A': 'صبح', 'B': 'ظهر', 'C': 'شب'}
    production_by_shift = {shift_labels.get(k, k): v for k, v in shift_counts.items()}

    machine_data = db.session.query(ProductionReport.machine_code, func.count(ProductionReport.id)) \
        .filter(ProductionReport.id.in_([r.id for r in prod_query.all()])) \
        .group_by(ProductionReport.machine_code).order_by(func.count(ProductionReport.id).desc()).all()
    production_by_machine = [{'machine': row[0], 'count': row[1]} for row in machine_data]

    product_data = db.session.query(ProductionReport.product_name, func.count(ProductionReport.id)) \
        .filter(ProductionReport.id.in_([r.id for r in prod_query.all()])) \
        .group_by(ProductionReport.product_name).order_by(func.count(ProductionReport.id).desc()).limit(10).all()
    top_products = [{'product': row[0], 'count': row[1]} for row in product_data]

    total_stoppage = stop_query.count()
    total_stop_time = db.session.query(func.sum(
        (func.julianday(StoppageReport.end_time) - func.julianday(StoppageReport.start_time)) * 86400
    )).filter(StoppageReport.end_time != None, StoppageReport.id.in_(
        [r.id for r in stop_query.all()]
    )).scalar() or 0
    avg_stop_time = round(total_stop_time / total_stoppage / 60, 1) if total_stoppage else 0

    stop_machine_data = db.session.query(StoppageReport.machine_code, func.count(StoppageReport.id)) \
        .filter(StoppageReport.id.in_([r.id for r in stop_query.all()])) \
        .group_by(StoppageReport.machine_code).order_by(func.count(StoppageReport.id).desc()).all()
    stoppage_by_machine = [{'machine': row[0], 'count': row[1]} for row in stop_machine_data]

    availability = round(total_prod_time / (total_prod_time + total_stop_time) * 100, 1) if (total_prod_time + total_stop_time) > 0 else 100

    all_machines = [r[0] for r in db.session.query(ProductionReport.machine_code).distinct()]
    all_products = [r[0] for r in db.session.query(ProductionReport.product_name).distinct()]

    return jsonify({
        'summary': {
            'total_production': total_production,
            'total_stoppage': total_stoppage,
            'avg_cycle_time': avg_cycle_time,
            'avg_stop_time': avg_stop_time,
            'availability': availability
        },
        'production_by_shift': production_by_shift,
        'production_by_machine': production_by_machine,
        'top_products': top_products,
        'stoppage_by_machine': stoppage_by_machine,
        'filters': {
            'machines': all_machines,
            'products': all_products
        }
    })