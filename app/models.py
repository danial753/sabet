from datetime import datetime, timezone, timedelta
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

IRAN_TZ = timezone(timedelta(hours=3, minutes=30))

# ------------------------------------------------------------
#   کارخانه
# ------------------------------------------------------------
class Factory(db.Model):
    __tablename__ = 'factory'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

    def __repr__(self):
        return f'<Factory {self.name}>'

# ------------------------------------------------------------
#   کاربر
# ------------------------------------------------------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    first_name = db.Column(db.String(50), nullable=False, default='')
    last_name = db.Column(db.String(50), nullable=False, default='')
    code = db.Column(db.String(20), unique=True, nullable=False, default='')
    is_admin = db.Column(db.Boolean, default=False)
    is_approver = db.Column(db.Boolean, default=False)
    factory_id = db.Column(db.Integer, db.ForeignKey('factory.id'), nullable=True)
    factory = db.relationship('Factory', backref='users', lazy=True)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def is_operator(self):
        return not self.is_admin and not self.is_approver

# ------------------------------------------------------------
#   گزارش تولید
# ------------------------------------------------------------
class ProductionReport(db.Model):
    __tablename__ = 'production_report'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True, nullable=False)
    user = db.relationship('User', foreign_keys=[user_id], backref='production_reports', lazy=True)
    date = db.Column(db.DateTime, default=lambda: datetime.now(IRAN_TZ), index=True)
    type = db.Column(db.String(10), nullable=False, default='CNC', index=True)

    product_name = db.Column(db.String(100))
    quantity = db.Column(db.Integer)

    shift = db.Column(db.String(20))
    part_size = db.Column(db.String(50))
    machine_code = db.Column(db.String(50))
    operation_stage_code = db.Column(db.String(50))
    manual_title = db.Column(db.String(100), nullable=True)

    start_time = db.Column(db.DateTime, default=lambda: datetime.now(IRAN_TZ))
    end_time = db.Column(db.DateTime)

    expected_duration_seconds = db.Column(db.Integer, nullable=True)

    # فیلدهای تأیید
    is_approved = db.Column(db.Boolean, default=False)
    approved_quantity = db.Column(db.Integer, nullable=True)
    approved_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    approval_date = db.Column(db.DateTime, nullable=True)

    approved_by = db.relationship('User', foreign_keys=[approved_by_id], lazy=True)

    @property
    def shift_fa(self):
        mapping = {'A': 'صبح', 'B': 'ظهر', 'C': 'شب'}
        return mapping.get(self.shift, self.shift or '-')

    @property
    def duration_seconds(self):
        if self.start_time and self.end_time:
            return int((self.end_time - self.start_time).total_seconds())
        return None

    @property
    def duration(self):
        sec = self.duration_seconds
        if sec is not None:
            hours, remainder = divmod(sec, 3600)
            minutes, seconds = divmod(remainder, 60)
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return None

    @property
    def expected_duration_formatted(self):
        if self.expected_duration_seconds is not None:
            hours, remainder = divmod(self.expected_duration_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return None

    @property
    def duration_warning(self):
        if self.expected_duration_seconds and self.duration_seconds:
            expected = self.expected_duration_seconds
            actual = self.duration_seconds
            if expected == 0:
                return False
            if actual > expected * 1.05:
                return True
        return False

    @property
    def quantity_diff(self):
        if self.is_approved and self.approved_quantity is not None:
            return self.quantity - self.approved_quantity
        return None

# ------------------------------------------------------------
#   گزارش توقف
# ------------------------------------------------------------
class StoppageReport(db.Model):
    __tablename__ = 'stoppage_report'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True, nullable=False)
    date = db.Column(db.DateTime, default=lambda: datetime.now(IRAN_TZ), index=True)
    machine_code = db.Column(db.String(50), nullable=False)
    stop_code = db.Column(db.String(50), nullable=False)
    reason = db.Column(db.Text, nullable=True)
    start_time = db.Column(db.DateTime, default=lambda: datetime.now(IRAN_TZ))
    end_time = db.Column(db.DateTime)

    expected_duration_seconds = db.Column(db.Integer, nullable=True)

    @property
    def duration_seconds(self):
        if self.start_time and self.end_time:
            return int((self.end_time - self.start_time).total_seconds())
        return None

    @property
    def duration(self):
        sec = self.duration_seconds
        if sec is not None:
            hours, remainder = divmod(sec, 3600)
            minutes, seconds = divmod(remainder, 60)
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return None

    @property
    def expected_duration_formatted(self):
        if self.expected_duration_seconds is not None:
            hours, remainder = divmod(self.expected_duration_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return None

    @property
    def duration_warning(self):
        if self.expected_duration_seconds and self.duration_seconds:
            expected = self.expected_duration_seconds
            actual = self.duration_seconds
            if expected == 0:
                return False
            if actual > expected * 1.05:
                return True
        return False

    @property
    def time_diff_seconds(self):
        if self.duration_seconds is not None and self.expected_duration_seconds is not None:
            return self.duration_seconds - self.expected_duration_seconds
        return None

    @property
    def time_diff_formatted(self):
        diff = self.time_diff_seconds
        if diff is None:
            return None
        sign = '+' if diff >= 0 else '-'
        abs_diff = abs(diff)
        hours, remainder = divmod(abs_diff, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{sign}{hours:02d}:{minutes:02d}:{seconds:02d}"

    @property
    def time_diff_is_positive(self):
        diff = self.time_diff_seconds
        return diff is not None and diff > 0

# ------------------------------------------------------------
#   لاگ سیستم
# ------------------------------------------------------------
class SystemLog(db.Model):
    __tablename__ = 'system_log'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    user = db.relationship('User', backref='logs', lazy=True)
    action = db.Column(db.String(200), nullable=False)
    details = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(IRAN_TZ))

# ------------------------------------------------------------
#   تنظیمات
# ------------------------------------------------------------
class ConfigSetting(db.Model):
    __tablename__ = 'config_setting'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.String(200), nullable=False)