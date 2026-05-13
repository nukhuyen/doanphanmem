import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, session, url_for, flash
from database import db
from backend.models import (User, Major, Course, Section, Curriculum, 
                             Registration, Notification, SystemLog, SystemConfig)
import pymysql
pymysql.install_as_MySQLdb()
# ══════════════════════════════════
#  CẤU HÌNH ỨNG DỤNG
# ══════════════════════════════════
BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.normpath(os.path.join(BASE_DIR, 'front-end', 'templates'))
ROOT_DIR     = os.path.normpath(os.path.join(BASE_DIR))
current_dir = os.path.dirname(os.path.abspath(__file__))
CA_CERT_PATH = os.path.join(current_dir, "ca.pem")

class Config:
    # ... các cấu hình khác ...
    SQLALCHEMY_ENGINE_OPTIONS = {
        'connect_args': {
            'ssl': {
                'ca': CA_CERT_PATH
            }
        },
        'pool_recycle': 280,
        'pool_pre_ping': True
    }  

app = Flask(__name__, template_folder=TEMPLATE_DIR)
database_uri = os.environ.get('DATABASE_URL')
if not database_uri:
    DB_USER = os.environ.get('DB_USER', 'root')
    DB_PASS = os.environ.get('DB_PASS', '')
    DB_HOST = os.environ.get('DB_HOST', 'localhost')
    DB_PORT = os.environ.get('DB_PORT', '3306')
    DB_NAME = os.environ.get('DB_NAME', 'hethong_dkhp')
    database_uri = f'mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
# 2. Cấu hình Flask-SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = database_uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.environ.get('SECRET_KEY', 'dkhp_secret_2026')

# 3. Cấu hình Engine để duy trì kết nối ổn định trên Render/Aiven
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_recycle': 280,
    'pool_pre_ping': True,
}

db.init_app(app)

with app.app_context():
    db.create_all()  # Lệnh này sẽ kiểm tra, bảng nào chưa có thì nó mới tạo
# ══════════════════════════════════
#  SEED
# ══════════════════════════════════
def seed_all():
    try:
        if not User.query.filter_by(username='admin').first():
            u = User(username='admin', full_name='Quản trị viên',
                     role='admin', active=True)
            u.password = 'Admin@2026'
            db.session.add(u)
            print('>>> ĐÃ TẠO: admin / Admin@2026')

        if not User.query.filter_by(username='phongdaotao').first():
            u = User(username='phongdaotao', full_name='Phòng Đào Tạo',
                     role='phongdaotao', active=True)
            u.password = 'Pdt@2026'
            db.session.add(u)
            print('>>> ĐÃ TẠO: phongdaotao / Pdt@2026')

        defaults = [
            ('max_credits', '24'),
            ('max_sections', '8'),
            ('min_gpa', '0.0'),
            ('reg_open', '1'),
            ('reg_deadline', ''),
        ]
        for key, val in defaults:
            if not SystemConfig.query.filter_by(key=key).first():
                db.session.add(SystemConfig(key=key, value=val))

        db.session.commit()
        print('>>> KHỞI TẠO DỮ LIỆU THÀNH CÔNG!')
    except Exception as e:
        db.session.rollback()
        print(f'>>> LỖI SEED: {e}')


# ══════════════════════════════════
#  HELPERS
# ══════════════════════════════════
def require_admin():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

def require_pdt():
    if session.get('role') not in ('admin', 'phongdaotao'):
        return redirect(url_for('login'))

def require_student():
    if not session.get('uid') or session.get('role') != 'student':
        return redirect(url_for('login'))

def get_config(key, default=None):
    cfg = SystemConfig.query.filter_by(key=key).first()
    return cfg.value if cfg else default

def log_action(action, detail=''):
    try:
        db.session.add(SystemLog(
            user_id=session.get('uid'),
            action=action, detail=detail,
            ip=request.remote_addr,
            created_at=datetime.utcnow()
        ))
        db.session.commit()
    except Exception:
        db.session.rollback()

def get_pending_count():
    return Registration.query.filter_by(status='pending').count()

def _column_exists(table: str, column: str) -> bool:
    """Kiểm tra cột có tồn tại trong DB chưa — dùng để tránh crash khi chưa migration."""
    try:
        result = db.session.execute(
            db.text(
                "SELECT COUNT(*) FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = DATABASE() "
                "AND TABLE_NAME = :tbl AND COLUMN_NAME = :col"
            ),
            {'tbl': table, 'col': column}
        ).scalar()
        return bool(result)
    except Exception:
        return False

def schedules_conflict(s1: str, s2: str) -> bool:
    if not s1 or not s2:
        return False
    def parse(s):
        slots = set()
        for slot in s.split('|'):
            parts = slot.strip().split(',')
            if len(parts) < 2:
                continue
            day  = parts[0].strip()
            tiet = parts[1].strip().replace('Tiet', '').replace('tiet', '')
            try:
                start, end = map(int, tiet.split('-'))
                for t in range(start, end + 1):
                    slots.add((day, t))
            except Exception:
                pass
        return slots
    return bool(parse(s1) & parse(s2))


# ══════════════════════════════════
#  AUTH
# ══════════════════════════════════
@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            if not user.active:
                flash('Tài khoản đã bị khóa!', 'error')
                return redirect(url_for('login'))
            user.failed_logins = 0
            db.session.commit()
            session['uid']  = user.id
            session['role'] = user.role
            session['name'] = user.full_name
            log_action('LOGIN', f'User {username} đăng nhập')
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            if user.role == 'phongdaotao':
                return redirect(url_for('pdt_dashboard'))
            return redirect(url_for('sv_dashboard'))
        if user:
            user.failed_logins = (user.failed_logins or 0) + 1
            db.session.commit()
        flash('Sai tài khoản hoặc mật khẩu!', 'error')
    return render_template('login.html')

# ════════════════════════════════════════════════════════
#  ĐĂNG KÝ TÀI KHOẢN — CÓ THÊM FIELD class_name
# ════════════════════════════════════════════════════════
@app.route('/register', methods=['GET', 'POST'])
def register():
    majors = Major.query.filter_by(active=True).all()
    if request.method == 'POST':
        username   = request.form.get('username', '').strip()
        password   = request.form.get('password', '').strip()
        full_name  = request.form.get('full_name', '').strip()
        major_id   = request.form.get('major_id') or None
        # ── MỚI: lấy lớp sinh viên từ form ──────────────────
        class_name = request.form.get('class_name', '').strip() or None
        if User.query.filter_by(username=username).first():
            flash('Tên đăng nhập đã tồn tại!', 'error')
        else:
            u = User(username=username, full_name=full_name,
                     role='student', active=True,
                     major_id=int(major_id) if major_id else None)
            u.password = password
            db.session.add(u)
            db.session.flush()  # lấy u.id trước khi commit
            # Ghi class_name qua raw SQL — an toàn khi chưa migration
            if class_name and _column_exists('users', 'class_name'):
                db.session.execute(
                    db.text("UPDATE users SET class_name = :cn WHERE id = :uid"),
                    {'cn': class_name, 'uid': u.id}
                )
            db.session.commit()
            flash('Đăng ký thành công! Vui lòng đăng nhập.', 'success')
            return redirect(url_for('login'))
    return render_template('register.html', majors=majors)

@app.route('/logout')
def logout():
    log_action('LOGOUT', f"User {session.get('name')} đăng xuất")
    session.clear()
    return redirect(url_for('login'))


# ══════════════════════════════════
#  REDIRECT TƯƠNG THÍCH URL CŨ
# ══════════════════════════════════
@app.route('/sv/courses')
def sv_courses_redirect():
    return redirect(url_for('sv_sections'))


# ══════════════════════════════════
#  SINH VIÊN — DASHBOARD
# ══════════════════════════════════
@app.route('/sv/dashboard')
def sv_dashboard():
    guard = require_student()
    if guard: return guard
    uid     = session.get('uid')
    my_regs = Registration.query.filter_by(user_id=uid).all()
    stats = {
        'pending':  sum(1 for r in my_regs if r.status == 'pending'),
        'approved': sum(1 for r in my_regs if r.status == 'approved'),
        'rejected': sum(1 for r in my_regs if r.status == 'rejected'),
        'total':    len(my_regs),
    }
    approved_regs = []
    for r in [x for x in my_regs if x.status == 'approved']:
        approved_regs.append({'reg': r, 'section': r.section,
                               'course': r.section.course if r.section else None})
    notifs = Notification.query.filter(
        Notification.target.in_(['all', 'student'])
    ).order_by(Notification.created_at.desc()).limit(5).all()
    open_sections  = Section.query.filter_by(active=True).limit(4).all()
    my_section_ids = {r.section_id for r in my_regs if r.status in ('pending', 'approved')}
    return render_template('sv_dashboard.html',
        stats=stats, approved_regs=approved_regs,
        notifs=notifs, open_sections=open_sections,
        my_section_ids=my_section_ids
    )


# ══════════════════════════════════
#  SINH VIÊN — CHƯƠNG TRÌNH ĐÀO TẠO
# ══════════════════════════════════
@app.route('/sv/curriculum')
def sv_curriculum():
    guard = require_student()
    if guard: return guard
    uid  = session.get('uid')
    user = User.query.get(uid)
    if not user.major_id:
        flash('Bạn chưa được phân ngành. Vui lòng liên hệ Phòng Đào Tạo.', 'error')
        return redirect(url_for('sv_dashboard'))
    items = (Curriculum.query
             .filter_by(major_id=user.major_id)
             .join(Course)
             .order_by(Curriculum.semester_no, Course.code)
             .all())
    by_semester = {}
    for item in items:
        s = item.semester_no or 0
        by_semester.setdefault(s, []).append(item)
    return render_template('sv_curriculum.html',
        major=user.major, by_semester=by_semester)


# ══════════════════════════════════════════════════════════════
#  SINH VIÊN — DANH SÁCH LỚP HỌC PHẦN
#  Filter theo ngành, lớp (class_name), và từ khóa tìm kiếm
# ══════════════════════════════════════════════════════════════
@app.route('/sv/sections')
def sv_sections():
    guard = require_student()
    if guard: return guard

    uid  = session.get('uid')
    user = User.query.get(uid)

    q            = request.args.get('q', '').strip()
    major_filter = request.args.get('major_id', '').strip()
    class_filter = request.args.get('class_name', '').strip()

    query = Section.query.filter_by(active=True).join(Course)

    if q:
        query = query.filter(
            Course.name.ilike(f'%{q}%') |
            Course.code.ilike(f'%{q}%') |
            Section.code.ilike(f'%{q}%') |
            Section.instructor.ilike(f'%{q}%')
        )

    # Lọc theo ngành: chỉ hiện HP thuộc CTĐT của ngành đó
    if major_filter:
        try:
            mid = int(major_filter)
            course_ids_in_major = [
                cu.course_id for cu in Curriculum.query.filter_by(major_id=mid).all()
            ]
            query = query.filter(Section.course_id.in_(course_ids_in_major))
        except ValueError:
            pass

    sections       = query.order_by(Section.id.desc()).all()
    my_regs        = Registration.query.filter_by(user_id=uid).all()
    my_section_ids = {r.section_id for r in my_regs if r.status in ('pending', 'approved')}
    reg_open       = get_config('reg_open', '1')
    majors         = Major.query.filter_by(active=True).order_by(Major.code).all()

    # ── Lấy danh sách lớp — dùng raw SQL, an toàn khi chưa chạy migration ──
    all_classes = []
    try:
        if _column_exists('users', 'class_name'):
            rows = db.session.execute(
                db.text(
                    "SELECT DISTINCT class_name FROM users "
                    "WHERE role = 'student' "
                    "  AND class_name IS NOT NULL "
                    "  AND class_name != '' "
                    "ORDER BY class_name"
                )
            ).fetchall()
            all_classes = [r[0] for r in rows]
    except Exception:
        all_classes = []

    # ── Filter theo lớp — chỉ chạy khi cột đã tồn tại trong DB ──
    if class_filter and _column_exists('users', 'class_name'):
        try:
            rows = db.session.execute(
                db.text(
                    "SELECT DISTINCT major_id FROM users "
                    "WHERE role = 'student' "
                    "  AND class_name = :cls "
                    "  AND major_id IS NOT NULL"
                ),
                {'cls': class_filter}
            ).fetchall()
            class_major_ids = [r[0] for r in rows]
            if class_major_ids:
                course_ids_for_class = list({
                    cu.course_id
                    for cu in Curriculum.query.filter(
                        Curriculum.major_id.in_(class_major_ids)
                    ).all()
                })
                sections = [s for s in sections if s.course_id in course_ids_for_class]
            else:
                sections = []
        except Exception:
            pass

    return render_template('sv_courses.html',
        courses=sections,
        q=q,
        my_course_ids=my_section_ids,
        reg_open=reg_open,
        majors=majors,
        major_filter=major_filter,
        all_classes=all_classes,
        class_filter=class_filter,
        current_user=user,
    )


# ══════════════════════════════════
#  SINH VIÊN — ĐĂNG KÝ LỚP HP
# ══════════════════════════════════
@app.route('/sv/sections/<int:sid>/register', methods=['POST'])
def sv_register_section(sid):
    guard = require_student()
    if guard: return guard
    uid     = session.get('uid')
    section = Section.query.get_or_404(sid)
    course  = section.course

    if get_config('reg_open', '1') != '1':
        flash('Hệ thống hiện đang đóng đăng ký học phần!', 'error')
        return redirect(url_for('sv_sections'))

    if not section.active:
        flash(f'Lớp {section.code} đã đóng đăng ký!', 'error')
        return redirect(url_for('sv_sections'))

    if (section.current_enrolled or 0) >= section.max_students:
        flash(f'Lớp {section.code} đã đầy ({section.max_students}/{section.max_students})!', 'error')
        return redirect(url_for('sv_sections'))

    existing = Registration.query.filter_by(user_id=uid, section_id=sid).filter(
        Registration.status.in_(['pending', 'approved'])
    ).first()
    if existing:
        flash(f'Bạn đã đăng ký lớp {section.code} rồi!', 'error')
        return redirect(url_for('sv_sections'))

    same_course_reg = (Registration.query
        .join(Section).filter(
            Registration.user_id == uid,
            Section.course_id == course.id,
            Registration.status.in_(['pending', 'approved'])
        ).first())
    if same_course_reg:
        flash(f'Bạn đã đăng ký môn {course.code} – {course.name} ở lớp khác rồi!', 'error')
        return redirect(url_for('sv_sections'))

    max_sections  = int(get_config('max_sections', '8'))
    current_count = (Registration.query
        .filter_by(user_id=uid)
        .filter(Registration.status.in_(['pending', 'approved']))
        .count())
    if current_count >= max_sections:
        flash(f'Bạn đã đăng ký tối đa {max_sections} lớp học phần!', 'error')
        return redirect(url_for('sv_sections'))

    my_active_regs = (Registration.query
        .filter_by(user_id=uid)
        .filter(Registration.status.in_(['pending', 'approved']))
        .all())
    for reg in my_active_regs:
        if reg.section and schedules_conflict(section.schedule, reg.section.schedule):
            flash(
                f'Lớp {section.code} bị trùng lịch với lớp {reg.section.code} '
                f'({reg.section.course.name})!', 'error'
            )
            return redirect(url_for('sv_sections'))

    min_gpa = float(get_config('min_gpa', '0.0'))
    if min_gpa > 0:
        user     = User.query.get(uid)
        user_gpa = float(getattr(user, 'gpa', 0) or 0)
        if user_gpa < min_gpa:
            flash(f'GPA của bạn ({user_gpa}) chưa đạt yêu cầu tối thiểu ({min_gpa})!', 'error')
            return redirect(url_for('sv_sections'))

    reg = Registration(user_id=uid, section_id=sid, status='pending',
                       submitted_at=datetime.utcnow())
    db.session.add(reg)
    db.session.commit()
    log_action('SUBMIT_REG', f'SV đăng ký lớp {section.code} – {course.code}')
    flash(
        f'Đã nộp đơn đăng ký <strong>{section.code} — {course.name}</strong>! '
        f'Vui lòng chờ Phòng Đào Tạo xét duyệt.', 'success'
    )
    return redirect(url_for('sv_my_registrations'))


# ══════════════════════════════════
#  SINH VIÊN — ĐƠN ĐĂNG KÝ CỦA TÔI
# ══════════════════════════════════
@app.route('/sv/my-registrations')
def sv_my_registrations():
    guard = require_student()
    if guard: return guard
    uid           = session.get('uid')
    status_filter = request.args.get('status', '')
    query         = Registration.query.filter_by(user_id=uid)
    if status_filter:
        query = query.filter_by(status=status_filter)
    regs     = query.order_by(Registration.submitted_at.desc()).all()
    reg_data = []
    for r in regs:
        reg_data.append({
            'reg':     r,
            'section': r.section,
            'course':  r.section.course if r.section else None,
        })
    all_regs = Registration.query.filter_by(user_id=uid).all()
    stats = {
        'pending':  sum(1 for r in all_regs if r.status == 'pending'),
        'approved': sum(1 for r in all_regs if r.status == 'approved'),
        'rejected': sum(1 for r in all_regs if r.status == 'rejected'),
    }
    return render_template('sv_my_registrations.html',
        reg_data=reg_data, stats=stats, status_filter=status_filter)

@app.route('/sv/my-registrations/<int:rid>/cancel', methods=['POST'])
def sv_cancel_reg(rid):
    guard = require_student()
    if guard: return guard
    reg = Registration.query.get_or_404(rid)
    if reg.user_id != session.get('uid'):
        flash('Bạn không có quyền hủy đơn này!', 'error')
        return redirect(url_for('sv_my_registrations'))
    if reg.status != 'pending':
        flash('Chỉ có thể hủy đơn đang chờ duyệt!', 'error')
        return redirect(url_for('sv_my_registrations'))
    code = reg.section.code if reg.section else rid
    db.session.delete(reg)
    db.session.commit()
    log_action('CANCEL_REG', f'SV hủy đơn lớp {code}')
    flash('Đã hủy đơn đăng ký!', 'success')
    return redirect(url_for('sv_my_registrations'))

@app.route('/sv/notifications')
def sv_notifications():
    guard = require_student()
    if guard: return guard
    notifs = Notification.query.filter(
        Notification.target.in_(['all', 'student'])
    ).order_by(Notification.created_at.desc()).all()
    return render_template('sv_notifications.html', notifs=notifs)


# ══════════════════════════════════
#  ADMIN — DASHBOARD
# ══════════════════════════════════
@app.route('/admin/dashboard')
def admin_dashboard():
    guard = require_admin()
    if guard: return guard
    stats = {
        'total_users':    User.query.count(),
        'total_courses':  Course.query.filter_by(active=True).count(),
        'total_sections': Section.query.filter_by(active=True).count(),
        'total_majors':   Major.query.filter_by(active=True).count(),
        'pending_regs':   Registration.query.filter_by(status='pending').count(),
        'approved_regs':  Registration.query.filter_by(status='approved').count(),
        'rejected_regs':  Registration.query.filter_by(status='rejected').count(),
    }
    recent_regs_raw = Registration.query.order_by(
        Registration.submitted_at.desc()).limit(5).all()
    recent_regs = [{
        'user_name':    r.student.full_name if r.student else '?',
        'section_code': r.section.code if r.section else '?',
        'course_name':  r.section.course.name if r.section and r.section.course else '?',
        'status':       r.status,
    } for r in recent_regs_raw]
    recent_notifs = Notification.query.order_by(
        Notification.created_at.desc()).limit(4).all()
    reg_open = get_config('reg_open', '1')
    return render_template('admin_dashboard.html',
        stats=stats, recent_regs=recent_regs,
        recent_notifs=recent_notifs,
        pending_count=get_pending_count(),
        reg_open=reg_open
    )


# ══════════════════════════════════
#  ADMIN — MỞ/ĐÓNG ĐĂNG KÝ NHANH
# ══════════════════════════════════
@app.route('/admin/toggle-registration', methods=['POST'])
def admin_toggle_registration():
    guard = require_admin()
    if guard: return guard
    cfg = SystemConfig.query.filter_by(key='reg_open').first()
    if not cfg:
        cfg = SystemConfig(key='reg_open', value='0')
        db.session.add(cfg)
    new_val   = '0' if cfg.value == '1' else '1'
    cfg.value = new_val
    db.session.commit()
    state_label = 'MỞ' if new_val == '1' else 'ĐÓNG'
    log_action('TOGGLE_REG_OPEN',
               f'Admin {state_label} đăng ký học phần toàn hệ thống')
    flash(
        f'Đã {"MỞ" if new_val == "1" else "ĐÓNG"} cổng đăng ký học phần!',
        'success' if new_val == '1' else 'warning'
    )
    return redirect(request.referrer or url_for('admin_dashboard'))


@app.route('/admin/sections/bulk-toggle', methods=['POST'])
def admin_bulk_toggle_sections():
    guard = require_admin()
    if guard: return guard
    ids        = request.form.getlist('ids')
    new_active = request.form.get('action') == 'open'
    count      = 0
    for sid in ids:
        sec = Section.query.get(int(sid))
        if sec:
            sec.active = new_active
            count += 1
    db.session.commit()
    action_label = 'mở' if new_active else 'đóng'
    log_action('BULK_TOGGLE_SECTIONS', f'Admin {action_label} {count} lớp HP')
    flash(f'Đã {action_label} {count} lớp học phần!', 'success')
    return redirect(url_for('admin_sections'))


# ══════════════════════════════════════════════════════════════
#  ADMIN — USERS (CÓ THÊM class_name)
# ══════════════════════════════════════════════════════════════
@app.route('/admin/users')
def admin_users():
    guard = require_admin()
    if guard: return guard
    q     = request.args.get('q', '').strip()
    query = User.query
    if q:
        query = query.filter(
            User.full_name.ilike(f'%{q}%') | User.username.ilike(f'%{q}%')
        )
    users  = query.order_by(User.created_at.desc()).all()
    majors = Major.query.filter_by(active=True).all()
    return render_template('admin_users.html', users=users, q=q,
                           majors=majors, pending_count=get_pending_count())

@app.route('/admin/users/add', methods=['POST'])
def admin_add_user():
    guard = require_admin()
    if guard: return guard
    username   = request.form.get('username', '').strip()
    password   = request.form.get('password', '').strip()
    full_name  = request.form.get('full_name', '').strip()
    role       = request.form.get('role', 'student')
    major_id   = request.form.get('major_id') or None
    # ── MỚI: lấy lớp từ form admin ──────────────────────────
    class_name = request.form.get('class_name', '').strip() or None
    if User.query.filter_by(username=username).first():
        flash('Tên đăng nhập đã tồn tại!', 'error')
    else:
        u = User(username=username, full_name=full_name, role=role,
                 active=True,
                 major_id=int(major_id) if major_id else None)
        u.password = password
        db.session.add(u)
        db.session.flush()
        # Ghi class_name qua raw SQL — an toàn khi chưa migration
        if class_name and _column_exists('users', 'class_name'):
            db.session.execute(
                db.text("UPDATE users SET class_name = :cn WHERE id = :uid"),
                {'cn': class_name, 'uid': u.id}
            )
        db.session.commit()
        log_action('ADD_USER', f'Thêm user {username}')
        flash(f'Đã tạo tài khoản {username}!', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/users/<int:uid>/edit', methods=['POST'])
def admin_edit_user(uid):
    guard = require_admin()
    if guard: return guard
    user = User.query.get_or_404(uid)
    user.full_name  = request.form.get('full_name', user.full_name).strip()
    user.role       = request.form.get('role', user.role)
    major_id        = request.form.get('major_id') or None
    user.major_id   = int(major_id) if major_id else None
    # Cập nhật class_name qua raw SQL — an toàn khi chưa migration
    class_name = request.form.get('class_name', '').strip() or None
    if _column_exists('users', 'class_name'):
        db.session.execute(
            db.text("UPDATE users SET class_name = :cn WHERE id = :uid"),
            {'cn': class_name, 'uid': uid}
        )
    new_pw = request.form.get('password', '').strip()
    if new_pw:
        user.password = new_pw
    db.session.commit()
    log_action('EDIT_USER', f'Sửa user {user.username}')
    flash('Đã cập nhật người dùng!', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/users/<int:uid>/toggle', methods=['POST'])
def admin_toggle_user(uid):
    guard = require_admin()
    if guard: return guard
    user        = User.query.get_or_404(uid)
    user.active = not user.active
    db.session.commit()
    log_action('TOGGLE_USER', f'{"Mở khóa" if user.active else "Khóa"} user {user.username}')
    flash(f'{"Đã mở khóa" if user.active else "Đã khóa"} tài khoản {user.username}!', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/users/<int:uid>/delete', methods=['POST'])
def admin_delete_user(uid):
    guard = require_admin()
    if guard: return guard
    user = User.query.get_or_404(uid)
    if user.role == 'admin':
        flash('Không thể xóa tài khoản admin!', 'error')
        return redirect(url_for('admin_users'))
    username = user.username
    db.session.delete(user)
    db.session.commit()
    log_action('DELETE_USER', f'Xóa user {username}')
    flash(f'Đã xóa tài khoản {username}!', 'success')
    return redirect(url_for('admin_users'))


# ══════════════════════════════════
#  ADMIN — MAJORS (NGÀNH)
# ══════════════════════════════════
@app.route('/admin/majors')
def admin_majors():
    guard = require_admin()
    if guard: return guard
    majors = Major.query.order_by(Major.code).all()
    return render_template('admin_majors.html', majors=majors,
                           pending_count=get_pending_count())

@app.route('/admin/majors/add', methods=['POST'])
def admin_add_major():
    guard = require_admin()
    if guard: return guard
    code = request.form.get('code', '').strip()
    name = request.form.get('name', '').strip()
    if Major.query.filter_by(code=code).first():
        flash(f'Mã ngành {code} đã tồn tại!', 'error')
    else:
        db.session.add(Major(code=code, name=name, active=True))
        db.session.commit()
        log_action('ADD_MAJOR', f'Thêm ngành {code}')
        flash(f'Đã thêm ngành {name}!', 'success')
    return redirect(url_for('admin_majors'))

@app.route('/admin/majors/<int:mid>/edit', methods=['POST'])
def admin_edit_major(mid):
    guard = require_admin()
    if guard: return guard
    major      = Major.query.get_or_404(mid)
    major.code = request.form.get('code', major.code).strip()
    major.name = request.form.get('name', major.name).strip()
    db.session.commit()
    log_action('EDIT_MAJOR', f'Sửa ngành {major.code}')
    flash('Đã cập nhật ngành!', 'success')
    return redirect(url_for('admin_majors'))

@app.route('/admin/majors/<int:mid>/toggle', methods=['POST'])
def admin_toggle_major(mid):
    guard = require_admin()
    if guard: return guard
    major        = Major.query.get_or_404(mid)
    major.active = not major.active
    db.session.commit()
    flash(f'{"Đã mở" if major.active else "Đã đóng"} ngành {major.code}!', 'success')
    return redirect(url_for('admin_majors'))


# ══════════════════════════════════
#  ADMIN — COURSES (MÔN HỌC)
# ══════════════════════════════════
@app.route('/admin/courses')
def admin_courses():
    guard = require_admin()
    if guard: return guard
    q             = request.args.get('q', '').strip()
    status_filter = request.args.get('status', '')
    query         = Course.query
    if q:
        query = query.filter(
            Course.name.ilike(f'%{q}%') | Course.code.ilike(f'%{q}%')
        )
    if status_filter == 'active':
        query = query.filter_by(active=True)
    elif status_filter == 'closed':
        query = query.filter_by(active=False)
    courses = query.order_by(Course.code).all()
    return render_template('admin_courses.html',
        courses=courses, q=q, status_filter=status_filter,
        pending_count=get_pending_count()
    )

@app.route('/admin/courses/add', methods=['POST'])
def admin_add_course():
    guard = require_admin()
    if guard: return guard
    code = request.form.get('code', '').strip()
    if Course.query.filter_by(code=code).first():
        flash(f'Mã môn {code} đã tồn tại!', 'error')
        return redirect(url_for('admin_courses'))
    db.session.add(Course(
        code=code,
        name=request.form.get('name', '').strip(),
        credits=int(request.form.get('credits', 3)),
        active=True
    ))
    db.session.commit()
    log_action('ADD_COURSE', f'Thêm môn {code}')
    flash(f'Đã thêm môn học {code}!', 'success')
    return redirect(url_for('admin_courses'))

@app.route('/admin/courses/<int:cid>/edit', methods=['POST'])
def admin_edit_course(cid):
    guard = require_admin()
    if guard: return guard
    course         = Course.query.get_or_404(cid)
    course.code    = request.form.get('code', course.code).strip()
    course.name    = request.form.get('name', course.name).strip()
    course.credits = int(request.form.get('credits', course.credits))
    db.session.commit()
    log_action('EDIT_COURSE', f'Sửa môn {course.code}')
    flash('Đã cập nhật môn học!', 'success')
    return redirect(url_for('admin_courses'))

@app.route('/admin/courses/<int:cid>/toggle', methods=['POST'])
def admin_toggle_course(cid):
    guard = require_admin()
    if guard: return guard
    course        = Course.query.get_or_404(cid)
    course.active = not course.active
    db.session.commit()
    flash(f'{"Đã mở" if course.active else "Đã đóng"} môn {course.code}!', 'success')
    return redirect(url_for('admin_courses'))

@app.route('/admin/courses/<int:cid>/delete', methods=['POST'])
def admin_delete_course(cid):
    guard = require_admin()
    if guard: return guard
    course = Course.query.get_or_404(cid)
    code   = course.code
    db.session.delete(course)
    db.session.commit()
    log_action('DELETE_COURSE', f'Xóa môn {code}')
    flash(f'Đã xóa môn học {code}!', 'success')
    return redirect(url_for('admin_courses'))


# ══════════════════════════════════
#  ADMIN — SECTIONS (LỚP HỌC PHẦN)
# ══════════════════════════════════
@app.route('/admin/sections')
def admin_sections():
    guard = require_admin()
    if guard: return guard
    q             = request.args.get('q', '').strip()
    status_filter = request.args.get('status', '')
    query         = Section.query.join(Course)
    if q:
        query = query.filter(
            Section.code.ilike(f'%{q}%') |
            Course.name.ilike(f'%{q}%') |
            Section.instructor.ilike(f'%{q}%')
        )
    if status_filter == 'active':
        query = query.filter(Section.active == True)
    elif status_filter == 'closed':
        query = query.filter(Section.active == False)
    sections = query.order_by(Section.code).all()
    courses  = Course.query.filter_by(active=True).order_by(Course.code).all()
    return render_template('admin_sections.html',
        sections=sections, courses=courses,
        q=q, status_filter=status_filter,
        pending_count=get_pending_count()
    )

@app.route('/admin/sections/add', methods=['POST'])
def admin_add_section():
    guard = require_admin()
    if guard: return guard
    code = request.form.get('code', '').strip()
    if Section.query.filter_by(code=code).first():
        flash(f'Mã lớp {code} đã tồn tại!', 'error')
        return redirect(url_for('admin_sections'))
    db.session.add(Section(
        code=code,
        course_id=int(request.form.get('course_id')),
        instructor=request.form.get('instructor', '').strip() or None,
        schedule=request.form.get('schedule', '').strip() or None,
        semester=request.form.get('semester', '').strip() or None,
        max_students=int(request.form.get('max_students', 40)),
        active=True
    ))
    db.session.commit()
    log_action('ADD_SECTION', f'Thêm lớp HP {code}')
    flash(f'Đã thêm lớp học phần {code}!', 'success')
    return redirect(url_for('admin_sections'))

@app.route('/admin/sections/<int:sid>/edit', methods=['POST'])
def admin_edit_section(sid):
    guard = require_admin()
    if guard: return guard
    sec              = Section.query.get_or_404(sid)
    sec.code         = request.form.get('code', sec.code).strip()
    sec.course_id    = int(request.form.get('course_id', sec.course_id))
    sec.instructor   = request.form.get('instructor', '').strip() or None
    sec.schedule     = request.form.get('schedule', '').strip() or None
    sec.semester     = request.form.get('semester', '').strip() or None
    sec.max_students = int(request.form.get('max_students', sec.max_students))
    db.session.commit()
    log_action('EDIT_SECTION', f'Sửa lớp HP {sec.code}')
    flash('Đã cập nhật lớp học phần!', 'success')
    return redirect(url_for('admin_sections'))

@app.route('/admin/sections/<int:sid>/toggle', methods=['POST'])
def admin_toggle_section(sid):
    guard = require_admin()
    if guard: return guard
    sec        = Section.query.get_or_404(sid)
    sec.active = not sec.active
    db.session.commit()
    flash(f'{"Đã mở" if sec.active else "Đã đóng"} lớp {sec.code}!', 'success')
    return redirect(url_for('admin_sections'))

@app.route('/admin/sections/<int:sid>/delete', methods=['POST'])
def admin_delete_section(sid):
    guard = require_admin()
    if guard: return guard
    sec  = Section.query.get_or_404(sid)
    code = sec.code
    db.session.delete(sec)
    db.session.commit()
    log_action('DELETE_SECTION', f'Xóa lớp HP {code}')
    flash(f'Đã xóa lớp học phần {code}!', 'success')
    return redirect(url_for('admin_sections'))


# ══════════════════════════════════
#  ADMIN — CURRICULUM
# ══════════════════════════════════
@app.route('/admin/curriculum')
def admin_curriculum():
    guard = require_admin()
    if guard: return guard
    major_id = request.args.get('major_id', type=int)
    majors   = Major.query.filter_by(active=True).order_by(Major.code).all()
    items    = []
    selected = None
    if major_id:
        selected = Major.query.get(major_id)
        items = (Curriculum.query
                 .filter_by(major_id=major_id)
                 .join(Course)
                 .order_by(Curriculum.semester_no, Course.code)
                 .all())
    courses = Course.query.filter_by(active=True).order_by(Course.code).all()
    return render_template('admin_curriculum.html',
        majors=majors, items=items, selected=selected,
        courses=courses, pending_count=get_pending_count()
    )

@app.route('/admin/curriculum/add', methods=['POST'])
def admin_add_curriculum():
    guard = require_admin()
    if guard: return guard
    major_id     = int(request.form.get('major_id'))
    course_id    = int(request.form.get('course_id'))
    semester_no  = request.form.get('semester_no', type=int)
    is_elective  = request.form.get('is_elective') == '1'
    prerequisite = request.form.get('prerequisite', '').strip() or None
    exists = Curriculum.query.filter_by(
        major_id=major_id, course_id=course_id).first()
    if exists:
        flash('Môn học đã có trong chương trình này!', 'error')
    else:
        db.session.add(Curriculum(
            major_id=major_id, course_id=course_id,
            semester_no=semester_no, is_elective=is_elective,
            prerequisite=prerequisite
        ))
        db.session.commit()
        log_action('ADD_CURRICULUM', f'Thêm môn vào CTĐT ngành {major_id}')
        flash('Đã thêm môn vào chương trình!', 'success')
    return redirect(url_for('admin_curriculum', major_id=major_id))

@app.route('/admin/curriculum/<int:cid>/delete', methods=['POST'])
def admin_delete_curriculum(cid):
    guard = require_admin()
    if guard: return guard
    item     = Curriculum.query.get_or_404(cid)
    major_id = item.major_id
    db.session.delete(item)
    db.session.commit()
    log_action('DELETE_CURRICULUM', f'Xóa môn khỏi CTĐT #{cid}')
    flash('Đã xóa môn khỏi chương trình!', 'success')
    return redirect(url_for('admin_curriculum', major_id=major_id))


# ══════════════════════════════════
#  ADMIN — REGISTRATIONS
# ══════════════════════════════════
@app.route('/admin/registrations')
def admin_registrations():
    guard = require_admin()
    if guard: return guard
    status_filter = request.args.get('status', '')
    query         = Registration.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    regs = query.order_by(Registration.submitted_at.desc()).all()
    reg_data = [{
        'reg':     r,
        'user':    r.student,
        'section': r.section,
        'course':  r.section.course if r.section else None,
    } for r in regs]
    return render_template('admin_registrations.html',
        reg_data=reg_data, status_filter=status_filter,
        pending_count=get_pending_count()
    )

def _approve_reg(reg):
    reg.status       = 'approved'
    reg.processed_by = session.get('uid')
    if reg.section:
        reg.section.current_enrolled = (reg.section.current_enrolled or 0) + 1

def _reject_reg(reg):
    reg.status       = 'rejected'
    reg.processed_by = session.get('uid')

@app.route('/admin/registrations/<int:rid>/approve', methods=['POST'])
def admin_approve_reg(rid):
    guard = require_admin()
    if guard: return guard
    reg = Registration.query.get_or_404(rid)
    _approve_reg(reg)
    db.session.commit()
    log_action('APPROVE_REG', f'Duyệt đơn #{rid}')
    flash('Đã duyệt đơn!', 'success')
    return redirect(url_for('admin_registrations'))

@app.route('/admin/registrations/<int:rid>/reject', methods=['POST'])
def admin_reject_reg(rid):
    guard = require_admin()
    if guard: return guard
    reg = Registration.query.get_or_404(rid)
    _reject_reg(reg)
    db.session.commit()
    log_action('REJECT_REG', f'Từ chối đơn #{rid}')
    flash('Đã từ chối đơn!', 'success')
    return redirect(url_for('admin_registrations'))

@app.route('/admin/registrations/bulk-action', methods=['POST'])
def admin_bulk_action():
    guard = require_admin()
    if guard: return guard
    ids         = request.form.getlist('ids')
    bulk_action = request.form.get('bulk_action')
    count       = 0
    for rid in ids:
        reg = Registration.query.get(int(rid))
        if reg and reg.status == 'pending':
            _approve_reg(reg) if bulk_action == 'approve' else _reject_reg(reg)
            count += 1
    db.session.commit()
    log_action('BULK_ACTION',
               f'{"Duyệt" if bulk_action=="approve" else "Từ chối"} {count} đơn')
    flash(f'Đã xử lý {count} đơn!', 'success')
    return redirect(url_for('admin_registrations'))


# ══════════════════════════════════
#  ADMIN — NOTIFICATIONS
# ══════════════════════════════════
@app.route('/admin/notifications')
def admin_notifications():
    guard = require_admin()
    if guard: return guard
    notifs = Notification.query.order_by(Notification.created_at.desc()).all()
    return render_template('admin_notifications.html', notifs=notifs,
                           pending_count=get_pending_count())

@app.route('/admin/notifications/add', methods=['POST'])
def admin_add_notif():
    guard = require_admin()
    if guard: return guard
    title   = request.form.get('title', '').strip()
    content = request.form.get('content', '').strip()
    target  = request.form.get('target', 'all')
    if title and content:
        db.session.add(Notification(title=title, content=content, target=target))
        db.session.commit()
        log_action('ADD_NOTIF', f'Tạo thông báo: {title}')
        flash('Đã gửi thông báo!', 'success')
    else:
        flash('Vui lòng nhập đầy đủ thông tin!', 'error')
    return redirect(url_for('admin_notifications'))

@app.route('/admin/notifications/<int:nid>/delete', methods=['POST'])
def admin_delete_notif(nid):
    guard = require_admin()
    if guard: return guard
    notif = Notification.query.get_or_404(nid)
    db.session.delete(notif)
    db.session.commit()
    log_action('DELETE_NOTIF', f'Xóa thông báo #{nid}')
    flash('Đã xóa thông báo!', 'success')
    return redirect(url_for('admin_notifications'))


# ══════════════════════════════════
#  ADMIN — LOGS & CONFIG
# ══════════════════════════════════
@app.route('/admin/logs')
def admin_logs():
    guard = require_admin()
    if guard: return guard
    logs      = SystemLog.query.order_by(SystemLog.created_at.desc()).limit(200).all()
    users_map = {u.id: u for u in User.query.all()}
    return render_template('admin_logs.html', logs=logs, users_map=users_map,
                           pending_count=get_pending_count())

@app.route('/admin/config')
def admin_config():
    guard = require_admin()
    if guard: return guard
    configs  = SystemConfig.query.all()
    reg_open = get_config('reg_open', '1')
    return render_template('admin_config.html', configs=configs,
                           pending_count=get_pending_count(),
                           reg_open=reg_open)

@app.route('/admin/config/save', methods=['POST'])
def admin_save_config():
    guard = require_admin()
    if guard: return guard
    for key, value in request.form.items():
        if key.startswith('cfg_'):
            config_key = key[4:]
            cfg = SystemConfig.query.filter_by(key=config_key).first()
            if cfg:
                cfg.value = value.strip()
            else:
                db.session.add(SystemConfig(key=config_key, value=value.strip()))
    db.session.commit()
    log_action('SAVE_CONFIG', 'Cập nhật cấu hình hệ thống')
    flash('Đã lưu cấu hình!', 'success')
    return redirect(url_for('admin_config'))


# ══════════════════════════════════
#  PHÒNG ĐÀO TẠO — DASHBOARD
# ══════════════════════════════════
@app.route('/pdt/dashboard')
def pdt_dashboard():
    guard = require_pdt()
    if guard: return guard
    stats = {
        'total_courses':  Course.query.filter_by(active=True).count(),
        'total_sections': Section.query.filter_by(active=True).count(),
        'pending_regs':   Registration.query.filter_by(status='pending').count(),
        'approved_regs':  Registration.query.filter_by(status='approved').count(),
        'rejected_regs':  Registration.query.filter_by(status='rejected').count(),
    }
    recent_regs_raw = Registration.query.order_by(
        Registration.submitted_at.desc()).limit(5).all()
    recent_regs = [{
        'user_name':    r.student.full_name if r.student else '?',
        'section_code': r.section.code if r.section else '?',
        'course_name':  r.section.course.name if r.section and r.section.course else '?',
        'status':       r.status,
    } for r in recent_regs_raw]
    recent_notifs = Notification.query.order_by(
        Notification.created_at.desc()).limit(4).all()
    reg_open = get_config('reg_open', '1')
    return render_template('pdt_dashboard.html',
        stats=stats, recent_regs=recent_regs,
        recent_notifs=recent_notifs,
        pending_count=get_pending_count(),
        reg_open=reg_open
    )


# ══════════════════════════════════
#  PHÒNG ĐÀO TẠO — MỞ/ĐÓNG ĐĂNG KÝ NHANH
# ══════════════════════════════════
@app.route('/pdt/toggle-registration', methods=['POST'])
def pdt_toggle_registration():
    guard = require_pdt()
    if guard: return guard
    cfg = SystemConfig.query.filter_by(key='reg_open').first()
    if not cfg:
        cfg = SystemConfig(key='reg_open', value='0')
        db.session.add(cfg)
    new_val   = '0' if cfg.value == '1' else '1'
    cfg.value = new_val
    db.session.commit()
    state_label = 'MỞ' if new_val == '1' else 'ĐÓNG'
    log_action('TOGGLE_REG_OPEN',
               f'PDT {state_label} đăng ký học phần toàn hệ thống')
    flash(
        f'Đã {"MỞ" if new_val == "1" else "ĐÓNG"} cổng đăng ký học phần!',
        'success' if new_val == '1' else 'warning'
    )
    return redirect(request.referrer or url_for('pdt_dashboard'))


@app.route('/pdt/sections/bulk-toggle', methods=['POST'])
def pdt_bulk_toggle_sections():
    guard = require_pdt()
    if guard: return guard
    ids        = request.form.getlist('ids')
    new_active = request.form.get('action') == 'open'
    count      = 0
    for sid in ids:
        sec = Section.query.get(int(sid))
        if sec:
            sec.active = new_active
            count += 1
    db.session.commit()
    action_label = 'mở' if new_active else 'đóng'
    log_action('BULK_TOGGLE_SECTIONS', f'PDT {action_label} {count} lớp HP')
    flash(f'Đã {action_label} {count} lớp học phần!', 'success')
    return redirect(url_for('pdt_sections'))


# ══════════════════════════════════
#  PHÒNG ĐÀO TẠO — COURSES (MÔN HỌC)
#  QUAN TRỌNG: các route static phải đứng TRƯỚC route dynamic <int:cid>
# ══════════════════════════════════
@app.route('/pdt/courses')
def pdt_courses():
    guard = require_pdt()
    if guard: return guard

    q               = request.args.get('q', '').strip()
    status_filter   = request.args.get('status', '')
    major_filter    = request.args.get('major', '').strip()
    semester_filter = request.args.get('semester', '').strip()
    page            = int(request.args.get('page', 1))
    per_page        = 15

    query = Course.query
    if q:
        query = query.filter(
            Course.name.ilike(f'%{q}%') | Course.code.ilike(f'%{q}%')
        )
    if status_filter == 'active':
        query = query.filter(Course.sections.any(Section.active == True))
    elif status_filter == 'closed':
        query = query.filter(~Course.sections.any(Section.active == True))

    courses_raw = query.order_by(Course.code).all()

    courses_list = []
    for c in courses_raw:
        curricula = Curriculum.query.filter_by(course_id=c.id).all()

        if major_filter:
            major_obj = Major.query.filter_by(code=major_filter).first()
            curricula = [cu for cu in curricula if major_obj and cu.major_id == major_obj.id]

        if semester_filter:
            curricula = [cu for cu in curricula if str(cu.semester_no) == semester_filter]

        if (major_filter or semester_filter) and not curricula:
            continue

        major_ids     = list({cu.major_id for cu in curricula})
        c.majors      = Major.query.filter(Major.id.in_(major_ids)).all() if major_ids else []
        c.semester_no = curricula[0].semester_no if curricula else None
        courses_list.append(c)

    # Stats
    total_all    = Course.query.count()
    active_count = Course.query.filter(Course.sections.any(Section.active == True)).count()
    closed_count = total_all - active_count
    shared_count = 0
    for c in Course.query.all():
        unique_majors = len({cu.major_id for cu in Curriculum.query.filter_by(course_id=c.id).all()})
        if unique_majors >= 3:
            shared_count += 1
    stats = {
        'total':  total_all,
        'active': active_count,
        'closed': closed_count,
        'shared': shared_count,
    }

    # Pagination
    total_courses = len(courses_list)
    total_pages   = max(1, (total_courses + per_page - 1) // per_page)
    page          = max(1, min(page, total_pages))
    courses_paged = courses_list[(page - 1) * per_page : page * per_page]

    majors = Major.query.filter_by(active=True).order_by(Major.code).all()

    active_registration = None

    return render_template('pdt_courses.html',
        courses=courses_paged,
        majors=majors,
        stats=stats,
        q=q,
        status_filter=status_filter,
        major_filter=major_filter,
        semester_filter=semester_filter,
        page=page,
        total_pages=total_pages,
        total_courses=total_courses,
        active_registration=active_registration,
        pending_count=get_pending_count(),
    )


@app.route('/pdt/courses/import-curriculum', methods=['POST'])
def pdt_import_curriculum():
    guard = require_pdt()
    if guard: return guard

    from backend.seed_curriculum import CURRICULUM_DATA

    selected_majors    = request.form.getlist('majors')
    selected_semesters = [int(s) for s in request.form.getlist('semesters')]
    default_max        = int(request.form.get('default_max_students', 40))
    semester_label     = request.form.get('default_semester_label', '').strip() or None
    skip_existing      = bool(request.form.get('skip_existing'))
    auto_open          = bool(request.form.get('auto_open'))

    if not selected_majors or not selected_semesters:
        flash('Vui lòng chọn ít nhất 1 ngành và 1 học kỳ.', 'warning')
        return redirect(url_for('pdt_courses'))

    new_courses = new_sections = new_curricula = skipped = 0

    for major_code in selected_majors:
        if major_code not in CURRICULUM_DATA:
            continue
        major = Major.query.filter_by(code=major_code).first()
        if not major:
            flash(f'Ngành {major_code} chưa tồn tại trong DB.', 'danger')
            continue

        for (code, name, credits, semester_no, is_elective) in CURRICULUM_DATA[major_code]:
            if semester_no not in selected_semesters:
                continue

            course = Course.query.filter_by(code=code).first()
            if not course:
                course = Course(code=code, name=name, credits=credits, active=True)
                db.session.add(course)
                db.session.flush()
                new_courses += 1
            elif not skip_existing:
                course.name    = name
                course.credits = credits
            else:
                skipped += 1

            section_code = f"{code}-{major_code}-HK{semester_no}"
            if not Section.query.filter_by(code=section_code).first():
                db.session.add(Section(
                    code=section_code,
                    course_id=course.id,
                    semester=semester_label,
                    max_students=default_max,
                    current_enrolled=0,
                    active=auto_open,
                ))
                new_sections += 1

            if not Curriculum.query.filter_by(major_id=major.id, course_id=course.id).first():
                db.session.add(Curriculum(
                    major_id=major.id,
                    course_id=course.id,
                    semester_no=semester_no,
                    is_elective=is_elective,
                ))
                new_curricula += 1

    db.session.commit()
    log_action('IMPORT_CURRICULUM',
               f'Import {new_courses} môn, {new_sections} lớp, {new_curricula} CTĐT')

    msg = (f'Import thành công: {new_courses} môn mới, '
           f'{new_sections} lớp học phần, {new_curricula} liên kết CTĐT.')
    if skipped:
        msg += f' ({skipped} môn đã tồn tại, bỏ qua.)'
    flash(msg, 'success')
    return redirect(url_for('pdt_courses'))


@app.route('/pdt/courses/open-registration', methods=['POST'])
def pdt_open_registration():
    guard = require_pdt()
    if guard: return guard

    reg_majors    = request.form.getlist('reg_majors')
    reg_semesters = [int(s) for s in request.form.getlist('reg_semesters')]
    reg_label     = request.form.get('reg_label', '').strip()
    auto_close    = bool(request.form.get('auto_close_prev'))

    if not reg_majors or not reg_semesters:
        flash('Vui lòng chọn ít nhất 1 ngành và 1 học kỳ.', 'warning')
        return redirect(url_for('pdt_courses'))

    if auto_close:
        Section.query.filter_by(active=True).update({'active': False})
        db.session.flush()

    major_ids = [m.id for m in Major.query.filter(Major.code.in_(reg_majors)).all()]
    curricula = Curriculum.query.filter(
        Curriculum.major_id.in_(major_ids),
        Curriculum.semester_no.in_(reg_semesters),
    ).all()

    course_ids = list({cu.course_id for cu in curricula})
    count = 0

    for course in Course.query.filter(Course.id.in_(course_ids)).all():
        sec = course.sections[0] if course.sections else None
        if sec is None:
            sec = Section(
                code=f"{course.code}-AUTO",
                course_id=course.id,
                max_students=40,
                current_enrolled=0,
                active=True,
            )
            db.session.add(sec)
        else:
            sec.active = True
        count += 1

    db.session.commit()
    log_action('OPEN_REGISTRATION',
               f'Mở {count} học phần | Ngành: {",".join(reg_majors)} '
               f'| HK: {reg_semesters} | {reg_label}')
    flash(f'✅ Đã mở đăng ký {count} học phần'
          + (f' — {reg_label}' if reg_label else '') + '.', 'success')
    return redirect(url_for('pdt_courses'))


@app.route('/pdt/courses/close-registration', methods=['POST'])
def pdt_close_registration():
    guard = require_pdt()
    if guard: return guard

    updated = Section.query.filter_by(active=True).update({'active': False})
    db.session.commit()
    log_action('CLOSE_REGISTRATION', f'Đóng {updated} học phần')
    flash(f'Đã đóng toàn bộ {updated} học phần đang mở.', 'success')
    return redirect(url_for('pdt_courses'))


@app.route('/pdt/courses/add', methods=['POST'])
def pdt_add_course():
    guard = require_pdt()
    if guard: return guard

    code         = request.form.get('code', '').strip().upper()
    name         = request.form.get('name', '').strip()
    credits      = int(request.form.get('credits', 3))
    instructor   = request.form.get('instructor', '').strip() or None
    max_students = int(request.form.get('max_students', 40))
    schedule     = request.form.get('schedule', '').strip() or None
    semester     = request.form.get('semester', '').strip() or None

    if Course.query.filter_by(code=code).first():
        flash(f'Mã môn {code} đã tồn tại!', 'error')
        return redirect(url_for('pdt_courses'))

    course = Course(code=code, name=name, credits=credits, active=True)
    db.session.add(course)
    db.session.flush()

    db.session.add(Section(
        code=f"{code}-01",
        course_id=course.id,
        instructor=instructor,
        schedule=schedule,
        semester=semester,
        max_students=max_students,
        current_enrolled=0,
        active=True,
    ))
    db.session.commit()
    log_action('ADD_COURSE', f'PDT thêm môn {code}')
    flash(f'Đã thêm môn học {code}!', 'success')
    return redirect(url_for('pdt_courses'))


# ── Route dynamic <int:cid> — phải đứng SAU tất cả route static ──────

@app.route('/pdt/courses/<int:cid>/edit', methods=['POST'])
def pdt_edit_course(cid):
    guard = require_pdt()
    if guard: return guard

    course         = Course.query.get_or_404(cid)
    course.code    = request.form.get('code', course.code).strip().upper()
    course.name    = request.form.get('name', course.name).strip()
    course.credits = int(request.form.get('credits', course.credits))
    sec = course.sections[0] if course.sections else None
    if sec:
        sec.instructor   = request.form.get('instructor', '').strip() or None
        sec.max_students = int(request.form.get('max_students', sec.max_students))
        sec.schedule     = request.form.get('schedule', '').strip() or None
        sec.semester     = request.form.get('semester', '').strip() or None
    db.session.commit()
    log_action('EDIT_COURSE', f'PDT sửa môn {course.code}')
    flash('Đã cập nhật môn học!', 'success')
    return redirect(url_for('pdt_courses'))


@app.route('/pdt/courses/<int:cid>/toggle', methods=['POST'])
def pdt_toggle_course(cid):
    guard = require_pdt()
    if guard: return guard

    course    = Course.query.get_or_404(cid)
    new_state = not (course.sections[0].active if course.sections else True)
    for s in course.sections:
        s.active = new_state
    db.session.commit()
    log_action('TOGGLE_COURSE', f'PDT {"mở" if new_state else "đóng"} môn {course.code}')
    flash(f'{"Đã mở" if new_state else "Đã đóng"} môn {course.code}!', 'success')
    return redirect(url_for('pdt_courses'))


@app.route('/pdt/courses/<int:cid>/open-quick', methods=['POST'])
def pdt_open_quick(cid):
    guard = require_pdt()
    if guard: return guard

    course = Course.query.get_or_404(cid)
    sec    = course.sections[0] if course.sections else None

    if sec is None:
        sec = Section(
            code=f"{course.code}-01",
            course_id=course.id,
            max_students=40,
            current_enrolled=0,
            active=True,
        )
        db.session.add(sec)
    else:
        sec.active = True

    db.session.commit()
    log_action('OPEN_QUICK', f'Mở nhanh học phần {course.code}')
    flash(f'Đã mở đăng ký học phần {course.code}!', 'success')
    return redirect(url_for('pdt_courses'))


@app.route('/pdt/courses/<int:cid>/delete', methods=['POST'])
def pdt_delete_course(cid):
    guard = require_pdt()
    if guard: return guard

    course = Course.query.get_or_404(cid)
    code   = course.code
    Curriculum.query.filter_by(course_id=cid).delete()
    db.session.delete(course)
    db.session.commit()
    log_action('DELETE_COURSE', f'PDT xóa môn {code}')
    flash(f'Đã xóa môn học {code}!', 'success')
    return redirect(url_for('pdt_courses'))


# ══════════════════════════════════
#  PHÒNG ĐÀO TẠO — SECTIONS
# ══════════════════════════════════
@app.route('/pdt/sections')
def pdt_sections():
    guard = require_pdt()
    if guard: return guard
    q             = request.args.get('q', '').strip()
    status_filter = request.args.get('status', '')
    query         = Section.query.join(Course)
    if q:
        query = query.filter(
            Section.code.ilike(f'%{q}%') |
            Course.name.ilike(f'%{q}%') |
            Section.instructor.ilike(f'%{q}%')
        )
    if status_filter == 'active':
        query = query.filter(Section.active == True)
    elif status_filter == 'closed':
        query = query.filter(Section.active == False)
    sections = query.order_by(Section.code).all()
    courses  = Course.query.filter_by(active=True).order_by(Course.code).all()
    return render_template('pdt_sections.html',
        sections=sections, courses=courses,
        q=q, status_filter=status_filter,
        pending_count=get_pending_count()
    )

@app.route('/pdt/sections/add', methods=['POST'])
def pdt_add_section():
    guard = require_pdt()
    if guard: return guard
    code = request.form.get('code', '').strip()
    if Section.query.filter_by(code=code).first():
        flash(f'Mã lớp {code} đã tồn tại!', 'error')
        return redirect(url_for('pdt_sections'))
    db.session.add(Section(
        code=code,
        course_id=int(request.form.get('course_id')),
        instructor=request.form.get('instructor', '').strip() or None,
        schedule=request.form.get('schedule', '').strip() or None,
        semester=request.form.get('semester', '').strip() or None,
        max_students=int(request.form.get('max_students', 40)),
        active=True
    ))
    db.session.commit()
    log_action('ADD_SECTION', f'PDT thêm lớp HP {code}')
    flash(f'Đã thêm lớp học phần {code}!', 'success')
    return redirect(url_for('pdt_sections'))

@app.route('/pdt/sections/<int:sid>/edit', methods=['POST'])
def pdt_edit_section(sid):
    guard = require_pdt()
    if guard: return guard
    sec              = Section.query.get_or_404(sid)
    sec.code         = request.form.get('code', sec.code).strip()
    sec.course_id    = int(request.form.get('course_id', sec.course_id))
    sec.instructor   = request.form.get('instructor', '').strip() or None
    sec.schedule     = request.form.get('schedule', '').strip() or None
    sec.semester     = request.form.get('semester', '').strip() or None
    sec.max_students = int(request.form.get('max_students', sec.max_students))
    db.session.commit()
    log_action('EDIT_SECTION', f'PDT sửa lớp HP {sec.code}')
    flash('Đã cập nhật lớp học phần!', 'success')
    return redirect(url_for('pdt_sections'))

@app.route('/pdt/sections/<int:sid>/toggle', methods=['POST'])
def pdt_toggle_section(sid):
    guard = require_pdt()
    if guard: return guard
    sec        = Section.query.get_or_404(sid)
    sec.active = not sec.active
    db.session.commit()
    log_action('TOGGLE_SECTION',
               f'PDT {"mở" if sec.active else "đóng"} lớp {sec.code}')
    flash(f'{"Đã mở" if sec.active else "Đã đóng"} lớp {sec.code}!', 'success')
    return redirect(url_for('pdt_sections'))

@app.route('/pdt/sections/<int:sid>/delete', methods=['POST'])
def pdt_delete_section(sid):
    guard = require_pdt()
    if guard: return guard
    sec  = Section.query.get_or_404(sid)
    code = sec.code
    db.session.delete(sec)
    db.session.commit()
    log_action('DELETE_SECTION', f'PDT xóa lớp HP {code}')
    flash(f'Đã xóa lớp học phần {code}!', 'success')
    return redirect(url_for('pdt_sections'))


# ══════════════════════════════════
#  PHÒNG ĐÀO TẠO — REGISTRATIONS
# ══════════════════════════════════
@app.route('/pdt/registrations')
def pdt_registrations():
    guard = require_pdt()
    if guard: return guard
    status_filter = request.args.get('status', '')
    query         = Registration.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    regs = query.order_by(Registration.submitted_at.desc()).all()
    reg_data = [{
        'reg':     r,
        'user':    r.student,
        'section': r.section,
        'course':  r.section.course if r.section else None,
    } for r in regs]
    return render_template('pdt_registrations.html',
        reg_data=reg_data, status_filter=status_filter,
        pending_count=get_pending_count()
    )

@app.route('/pdt/registrations/<int:rid>/approve', methods=['POST'])
def pdt_approve_reg(rid):
    guard = require_pdt()
    if guard: return guard
    reg = Registration.query.get_or_404(rid)
    _approve_reg(reg)
    db.session.commit()
    log_action('APPROVE_REG', f'PDT duyệt đơn #{rid}')
    flash('Đã duyệt đơn!', 'success')
    return redirect(url_for('pdt_registrations'))

@app.route('/pdt/registrations/<int:rid>/reject', methods=['POST'])
def pdt_reject_reg(rid):
    guard = require_pdt()
    if guard: return guard
    reg = Registration.query.get_or_404(rid)
    _reject_reg(reg)
    db.session.commit()
    log_action('REJECT_REG', f'PDT từ chối đơn #{rid}')
    flash('Đã từ chối đơn!', 'success')
    return redirect(url_for('pdt_registrations'))

@app.route('/pdt/registrations/bulk-action', methods=['POST'])
def pdt_bulk_action():
    guard = require_pdt()
    if guard: return guard
    ids         = request.form.getlist('ids')
    bulk_action = request.form.get('bulk_action')
    count       = 0
    for rid in ids:
        reg = Registration.query.get(int(rid))
        if reg and reg.status == 'pending':
            _approve_reg(reg) if bulk_action == 'approve' else _reject_reg(reg)
            count += 1
    db.session.commit()
    log_action('BULK_ACTION',
               f'PDT {"duyệt" if bulk_action=="approve" else "từ chối"} {count} đơn')
    flash(f'Đã xử lý {count} đơn!', 'success')
    return redirect(url_for('pdt_registrations'))


# ══════════════════════════════════
#  PHÒNG ĐÀO TẠO — CONFIG & NOTIFS
# ══════════════════════════════════
@app.route('/pdt/config')
def pdt_config():
    guard = require_pdt()
    if guard: return guard
    configs  = SystemConfig.query.all()
    reg_open = get_config('reg_open', '1')
    return render_template('pdt_config.html', configs=configs,
                           pending_count=get_pending_count(),
                           reg_open=reg_open)

@app.route('/pdt/config/save', methods=['POST'])
def pdt_save_config():
    guard = require_pdt()
    if guard: return guard
    for key, value in request.form.items():
        if key.startswith('cfg_'):
            config_key = key[4:]
            cfg = SystemConfig.query.filter_by(key=config_key).first()
            if cfg:
                cfg.value = value.strip()
            else:
                db.session.add(SystemConfig(key=config_key, value=value.strip()))
    db.session.commit()
    log_action('SAVE_CONFIG', 'PDT cập nhật quy tắc đăng ký')
    flash('Đã lưu quy tắc đăng ký!', 'success')
    return redirect(url_for('pdt_config'))

@app.route('/pdt/notifications')
def pdt_notifications():
    guard = require_pdt()
    if guard: return guard
    notifs = Notification.query.order_by(Notification.created_at.desc()).all()
    return render_template('pdt_notifications.html', notifs=notifs,
                           pending_count=get_pending_count())

@app.route('/pdt/notifications/add', methods=['POST'])
def pdt_add_notif():
    guard = require_pdt()
    if guard: return guard
    title   = request.form.get('title', '').strip()
    content = request.form.get('content', '').strip()
    target  = request.form.get('target', 'all')
    if title and content:
        db.session.add(Notification(title=title, content=content,
                                    target=target, created_at=datetime.utcnow()))
        db.session.commit()
        log_action('ADD_NOTIF', f'PDT gửi thông báo: {title}')
        flash('Đã gửi thông báo!', 'success')
    else:
        flash('Vui lòng nhập đầy đủ thông tin!', 'error')
    return redirect(url_for('pdt_notifications'))

@app.route('/pdt/notifications/<int:nid>/delete', methods=['POST'])
def pdt_delete_notif(nid):
    guard = require_pdt()
    if guard: return guard
    notif = Notification.query.get_or_404(nid)
    db.session.delete(notif)
    db.session.commit()
    log_action('DELETE_NOTIF', f'PDT xóa thông báo #{nid}')
    flash('Đã xóa thông báo!', 'success')
    return redirect(url_for('pdt_notifications'))


# ══════════════════════════════════
#  KHỞI CHẠY
# ══════════════════════════════════
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        seed_all()
    app.run(debug=True, port=5000)