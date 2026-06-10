from flask import Flask, redirect, url_for, request
from flask_compress import Compress
from flask_caching import Cache
from flask_socketio import SocketIO
from config import Config
from app.models import db
from flask_login import LoginManager, current_user
from persiantools.jdatetime import JalaliDateTime
from sqlalchemy import event
from sqlalchemy.engine import Engine

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
compress = Compress()
cache = Cache(config={'CACHE_TYPE': 'SimpleCache', 'CACHE_DEFAULT_TIMEOUT': 300})
socketio = SocketIO()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    compress.init_app(app)
    cache.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*")

    @event.listens_for(Engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

    @app.after_request
    def add_cache_header(response):
        if request.path.startswith('/static'):
            response.cache_control.max_age = 86400
            response.cache_control.public = True
        return response

    from app.auth.routes import auth_bp
    from app.reports.routes import reports_bp
    from app.admin.routes import admin_bp
    from app.admin_report.routes import admin_report_bp
    from app.profile.routes import profile_bp
    from app.analytics.routes import analytics_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(reports_bp, url_prefix='/reports')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(admin_report_bp, url_prefix='/admin')
    app.register_blueprint(profile_bp, url_prefix='/profile')
    app.register_blueprint(analytics_bp, url_prefix='/admin')

    @app.template_filter('jalali_date')
    def jalali_date_filter(dt, format='%Y-%m-%d %H:%M'):
        if dt is None:
            return '-'
        return JalaliDateTime.to_jalali(dt).strftime(format)

    @app.route('/')
    def index():
        if current_user.is_authenticated:
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
        return redirect(url_for('auth.login'))

    with app.app_context():
        db.create_all()

    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        return User.query.get(int(user_id))

    return app