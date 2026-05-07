# ══════════════════════════════════════════════════════════════════════
# PHÒNG ĐÀO TẠO — COURSES (MÔN HỌC)
# Dán toàn bộ đoạn này vào main.py, thay thế phần cũ
# ══════════════════════════════════════════════════════════════════════

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

    # Enrich: gắn .majors và .semester_no từ bảng Curriculum
    # Đồng thời lọc theo ngành/HK nếu có
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
    total_courses = len(courses_list)
    all_sections  = Section.query.all()
    stats = {
        'total':  total_courses,
        'active': sum(1 for c in courses_list if c.sections and c.sections[0].active),
        'closed': sum(1 for c in courses_list if not (c.sections and c.sections[0].active)),
        'shared': sum(1 for c in courses_list if len(getattr(c, 'majors', [])) >= 3),
    }

    # Pagination
    total_pages   = max(1, (total_courses + per_page - 1) // per_page)
    page          = max(1, min(page, total_pages))
    courses_paged = courses_list[(page - 1) * per_page : page * per_page]

    majors = Major.query.filter_by(active=True).order_by(Major.code).all()

    # Đợt đăng ký đang mở (nếu có model RegistrationPeriod)
    active_registration = None
    # Uncomment nếu bạn có model RegistrationPeriod:
    # active_registration = RegistrationPeriod.query.filter_by(is_active=True).first()

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


# ── Import từ Chương Trình Đào Tạo ──────────────────────────────────
@app.route('/pdt/courses/import-curriculum', methods=['POST'])
def pdt_import_curriculum():
    guard = require_pdt()
    if guard: return guard

    from seed_curriculum import CURRICULUM_DATA

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

            # 1. Upsert Course
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

            # 2. Tạo Section nếu chưa có
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

            # 3. Upsert Curriculum
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


# ── Mở đợt đăng ký hàng loạt (từ topbar modal) ──────────────────────
# QUAN TRỌNG: route static phải đứng TRƯỚC route dynamic <int:cid>
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

    # Đóng tất cả section đang mở nếu được chọn
    if auto_close:
        Section.query.filter_by(active=True).update({'active': False})
        db.session.flush()

    # Lấy tất cả course khớp ngành + học kỳ qua bảng Curriculum
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


# ── Đóng toàn bộ đợt đăng ký ────────────────────────────────────────
@app.route('/pdt/courses/close-registration', methods=['POST'])
def pdt_close_registration():
    guard = require_pdt()
    if guard: return guard

    updated = Section.query.filter_by(active=True).update({'active': False})
    db.session.commit()
    log_action('CLOSE_REGISTRATION', f'Đóng {updated} học phần')
    flash(f'Đã đóng toàn bộ {updated} học phần đang mở.', 'success')
    return redirect(url_for('pdt_courses'))


# ── Thêm học phần ────────────────────────────────────────────────────
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


# ── Sửa học phần ─────────────────────────────────────────────────────
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


# ── Toggle đóng/mở học phần ──────────────────────────────────────────
@app.route('/pdt/courses/<int:cid>/toggle', methods=['POST'])
def pdt_toggle_course(cid):
    guard = require_pdt()
    if guard: return guard

    course    = Course.query.get_or_404(cid)
    new_state = not (course.sections[0].active if course.sections else True)
    for s in course.sections:
        s.active = new_state

    db.session.commit()
    log_action('TOGGLE_COURSE',
               f'PDT {"mở" if new_state else "đóng"} môn {course.code}')
    flash(f'{"Đã mở" if new_state else "Đã đóng"} môn {course.code}!', 'success')
    return redirect(url_for('pdt_courses'))


# ── Mở đăng ký nhanh từng học phần (từ icon trong bảng) ─────────────
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


# ── Xóa học phần ─────────────────────────────────────────────────────
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