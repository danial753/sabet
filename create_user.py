# create_user.py
from app import create_app
from app.models import db, User
from werkzeug.security import generate_password_hash

app = create_app()

with app.app_context():
    db.create_all()

    if not User.query.filter_by(username='admin').first():
        admin = User(
            username='admin',
            password=generate_password_hash('admin123'),
            first_name='مدیر',
            last_name='سیستم',
            code='ADM-001',
            is_admin=True
        )
        db.session.add(admin)
        print("✔ ادمین ایجاد شد.")

    if not User.query.filter_by(username='user1').first():
        user = User(
            username='alo',
            password=generate_password_hash('123'),
            first_name='کاربر',
            last_name='عادی',
            code='123',
            is_admin=False
        )
        db.session.add(user)
        print("✔ کاربر عادی ایجاد شد.")

    db.session.commit()