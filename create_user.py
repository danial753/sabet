from app import create_app
from app.models import db, User, Factory
from werkzeug.security import generate_password_hash

app = create_app()
with app.app_context():
    db.create_all()

    factory_names = ['آذین 1', 'آذین 2', 'آذین 3', 'آذین 4']
    for name in factory_names:
        if not Factory.query.filter_by(name=name).first():
            db.session.add(Factory(name=name))
    db.session.commit()
    print("✔ کارخانه‌ها ایجاد شدند.")

    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', password=generate_password_hash('admin123'),
                     first_name='مدیر', last_name='سیستم', code='ADM-001',
                     is_admin=True, factory_id=Factory.query.filter_by(name='آذین 1').first().id)
        db.session.add(admin)

    if not User.query.filter_by(username='planner1').first():
        planner = User(username='planner1', password=generate_password_hash('plan123'),
                       first_name='سرپرست', last_name='تولید', code='PLN-001',
                       is_shift_planner=True, factory_id=Factory.query.filter_by(name='آذین 1').first().id)
        db.session.add(planner)

    if not User.query.filter_by(username='inspector1').first():
        inspector = User(username='inspector1', password=generate_password_hash('insp123'),
                         first_name='بازرس', last_name='کیفیت', code='INS-001',
                         is_quality_inspector=True, factory_id=Factory.query.filter_by(name='آذین 1').first().id)
        db.session.add(inspector)

    if not User.query.filter_by(username='warehouse1').first():
        warehouse = User(username='warehouse1', password=generate_password_hash('wh123'),
                         first_name='انباردار', last_name='کالا', code='WH-001',
                         is_warehouse=True, factory_id=Factory.query.filter_by(name='آذین 1').first().id)
        db.session.add(warehouse)

    if not User.query.filter_by(username='approver1').first():
        approver = User(username='approver1', password=generate_password_hash('app123'),
                        first_name='تأییدکننده', last_name='کیفیت', code='APR-001',
                        is_approver=True, factory_id=Factory.query.filter_by(name='آذین 1').first().id)
        db.session.add(approver)

    if not User.query.filter_by(username='operator1').first():
        operator = User(username='operator1', password=generate_password_hash('op123'),
                        first_name='اپراتور', last_name='تولید', code='OPR-001',
                        factory_id=Factory.query.filter_by(name='آذین 1').first().id)
        db.session.add(operator)

    db.session.commit()
    print("✔ کاربران پیش‌فرض ایجاد شدند.")