from database import db
from datetime import datetime
import bcrypt
import sys
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, '..'))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

try:
    from database import db
except ImportError:
    # Backup cho một số môi trường chạy local khác
    import database
    db = database.db
# ══════════════════════════════════
#  USER
# ══════════════════════════════════
class User(db.Model):
    __tablename__ = 'users'
    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(80), unique=True, nullable=False)
    _password     = db.Column('password', db.String(200), nullable=False)
    full_name     = db.Column(db.String(200))
    role          = db.Column(db.String(20), default='student')  # admin | phongdaotao | student
    active        = db.Column(db.Boolean, default=True)
    failed_logins = db.Column(db.Integer, default=0)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    # Sinh viên thuộc 1 ngành (n-1)
    major_id      = db.Column(db.Integer, db.ForeignKey('majors.id'), nullable=True)
    major         = db.relationship('Major', back_populates='students')

    # LƯU Ý: class_name được đọc/ghi qua raw SQL trong main.py
    # để tránh crash khi chưa chạy migration ALTER TABLE.
    # Sau khi đã chạy: ALTER TABLE users ADD COLUMN class_name VARCHAR(20) NULL;
    # bạn có thể bỏ comment dòng dưới để dùng ORM bình thường:
    # class_name = db.Column(db.String(20), nullable=True)

    registrations = db.relationship('Registration', foreign_keys='Registration.user_id',
                                    back_populates='student', cascade='all, delete-orphan')

    @property
    def password(self):
        raise AttributeError('Không đọc trực tiếp password')

    @password.setter
    def password(self, raw: str):
        self._password = bcrypt.hashpw(raw.encode(), bcrypt.gensalt()).decode()

    def check_password(self, raw: str) -> bool:
        try:
            return bcrypt.checkpw(raw.encode(), self._password.encode())
        except Exception:
            return False

    def set_raw_password(self, hashed: str):
        """Dùng khi seed — nhận thẳng chuỗi hash đã tạo sẵn."""
        self._password = hashed


# ══════════════════════════════════
#  MAJOR (NGÀNH)
# ══════════════════════════════════
class Major(db.Model):
    __tablename__ = 'majors'
    id         = db.Column(db.Integer, primary_key=True)
    code       = db.Column(db.String(20), unique=True, nullable=False)
    name       = db.Column(db.String(200), nullable=False)
    active     = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    students    = db.relationship('User', back_populates='major')
    curriculums = db.relationship('Curriculum', back_populates='major',
                                  cascade='all, delete-orphan')


# ══════════════════════════════════
#  COURSE (MÔN HỌC)
# ══════════════════════════════════
class Course(db.Model):
    __tablename__ = 'courses'
    id         = db.Column(db.Integer, primary_key=True)
    code       = db.Column(db.String(20), unique=True, nullable=False)
    name       = db.Column(db.String(200), nullable=False)
    credits    = db.Column(db.Integer, default=3)
    active     = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    sections    = db.relationship('Section', back_populates='course',
                                  cascade='all, delete-orphan')
    curriculums = db.relationship('Curriculum', back_populates='course')


# ══════════════════════════════════
#  SECTION (LỚP HỌC PHẦN)
# ══════════════════════════════════
class Section(db.Model):
    __tablename__ = 'sections'
    id               = db.Column(db.Integer, primary_key=True)
    code             = db.Column(db.String(30), unique=True, nullable=False)  # VD: CTDL01
    course_id        = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    instructor       = db.Column(db.String(100))
    schedule         = db.Column(db.String(200))   # VD: "Thu2,Tiet1-3|Thu4,Tiet1-3"
    semester         = db.Column(db.String(20))
    max_students     = db.Column(db.Integer, default=40)
    current_enrolled = db.Column(db.Integer, default=0)
    active           = db.Column(db.Boolean, default=True)
    created_at       = db.Column(db.DateTime, default=datetime.utcnow)

    course        = db.relationship('Course', back_populates='sections')
    registrations = db.relationship('Registration', back_populates='section',
                                    cascade='all, delete-orphan')


# ══════════════════════════════════
#  CURRICULUM (CHƯƠNG TRÌNH ĐÀO TẠO)
# Mỗi dòng = 1 môn trong khung của 1 ngành
# ══════════════════════════════════
class Curriculum(db.Model):
    __tablename__ = 'curriculums'
    id           = db.Column(db.Integer, primary_key=True)
    major_id     = db.Column(db.Integer, db.ForeignKey('majors.id'), nullable=False)
    course_id    = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    semester_no  = db.Column(db.Integer)                  # Học kỳ khuyến nghị
    is_elective  = db.Column(db.Boolean, default=False)   # Tự chọn?
    prerequisite = db.Column(db.String(200))              # Mã môn tiên quyết
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)

    major  = db.relationship('Major', back_populates='curriculums')
    course = db.relationship('Course', back_populates='curriculums')

    __table_args__ = (
        db.UniqueConstraint('major_id', 'course_id', name='uq_curriculum_major_course'),
    )


# ══════════════════════════════════
#  REGISTRATION (ĐĂNG KÝ HỌC PHẦN)
# ══════════════════════════════════
class Registration(db.Model):
    __tablename__ = 'registrations'
    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    section_id   = db.Column(db.Integer, db.ForeignKey('sections.id'), nullable=False)
    status       = db.Column(db.String(20), default='pending')  # pending | approved | rejected
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    processed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    student  = db.relationship('User', foreign_keys=[user_id], back_populates='registrations')
    section  = db.relationship('Section', back_populates='registrations')
    reviewer = db.relationship('User', foreign_keys=[processed_by])


# ══════════════════════════════════
#  NOTIFICATION
# ══════════════════════════════════
class Notification(db.Model):
    __tablename__ = 'notifications'
    id         = db.Column(db.Integer, primary_key=True)
    title      = db.Column(db.String(200), nullable=False)
    content    = db.Column(db.Text, nullable=False)
    target     = db.Column(db.String(20), default='all')  # all | student | phongdaotao
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ══════════════════════════════════
#  SYSTEM LOG
# ══════════════════════════════════
class SystemLog(db.Model):
    __tablename__ = 'system_logs'
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action     = db.Column(db.String(100))
    detail     = db.Column(db.Text)
    ip         = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ══════════════════════════════════
#  SYSTEM CONFIG
# ══════════════════════════════════
class SystemConfig(db.Model):
    __tablename__ = 'system_config'
    id    = db.Column(db.Integer, primary_key=True)
    key   = db.Column(db.String(50), unique=True)
    value = db.Column(db.String(255))