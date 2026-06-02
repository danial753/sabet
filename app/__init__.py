# app/__init__.py
from flask import Flask, redirect, url_for
from flask_compress import Compress
from flask_caching import Cache
from config import Config
from app.models import db
from flask_login import LoginManager, current_user

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
compress = Compress()
cache = Cache(config={'CACHE_TYPE': 'SimpleCache', 'CACHE_DEFAULT_TIMEOUT': 300})

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    compress.init_app(app)
    cache.init_app(app)

    # ثبت Blueprint ها
    from app.auth.routes import auth_bp
    from app.reports.routes import reports_bp
    from app.admin.routes import admin_bp
    from app.admin_report.routes import admin_report_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(reports_bp, url_prefix='/reports')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(admin_report_bp, url_prefix='/admin')

    # مسیر اصلی (ریشه)
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            if current_user.is_admin:
                return redirect(url_for('admin.view_user_reports'))
            if current_user.is_approver:
                return redirect(url_for('reports.approver_dashboard'))
            return redirect(url_for('reports.dashboard'))
        return redirect(url_for('auth.login'))

    with app.app_context():
        db.create_all()

    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        return User.query.get(int(user_id))

    return app