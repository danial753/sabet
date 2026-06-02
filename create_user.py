# create_user.py
from app import create_app
from app.models import db, User, Factory
from werkzeug.security import generate_password_hash

app = create_app()
with app.app_context():
    db.create_all()

    # ----- ایجاد کارخانه‌ها -----
    factory_names = ['آذین 1', 'آذین 2', 'آذین 3', 'آذین 4']
    for name in factory_names:
        if not Factory.query.filter_by(name=name).first():
            db.session.add(Factory(name=name))
    db.session.commit()
    print("✔ کارخانه‌ها ایجاد شدند.")

    # ----- کاربر ادمین (تعلق به آذین 1) -----
    if not User.query.filter_by(username='admin').first():
        admin = User(
            username='admin',
            password=generate_password_hash('admin123'),
            first_name='مدیر',
            last_name='سیستم',
            code='ADM-001',
            is_admin=True,
            is_approver=False,
            factory_id=Factory.query.filter_by(name='آذین 1').first().id
        )
        db.session.add(admin)

    # ----- کاربر تأییدکننده نمونه (آذین 1) -----
    if not User.query.filter_by(username='approver1').first():
        approver = User(
            username='approver1',
            password=generate_password_hash('app123'),
            first_name='تأییدکننده',
            last_name='کیفیت',
            code='APR-001',
            is_admin=False,
            is_approver=True,
            factory_id=Factory.query.filter_by(name='آذین 1').first().id
        )
        db.session.add(approver)

    # ----- کاربر اپراتور نمونه (آذین 1) -----
    if not User.query.filter_by(username='operator1').first():
        operator = User(
            username='operator1',
            password=generate_password_hash('op123'),
            first_name='اپراتور',
            last_name='تولید',
            code='OPR-001',
            is_admin=False,
            is_approver=False,
            factory_id=Factory.query.filter_by(name='آذین 1').first().id
        )
        db.session.add(operator)

    db.session.commit()
    print("✔ کاربران پیش‌فرض ایجاد شدند.")