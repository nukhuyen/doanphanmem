-- =====================================================
-- HỆ THỐNG ĐĂNG KÝ HỌC PHẦN — SCHEMA v2
-- =====================================================

DROP DATABASE IF EXISTS hethong_dkhp;
CREATE DATABASE hethong_dkhp
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE hethong_dkhp;

-- =====================================================
-- 1. MAJORS (NGÀNH HỌC)
-- =====================================================
CREATE TABLE majors (
    id         INT PRIMARY KEY AUTO_INCREMENT,
    code       VARCHAR(20)  UNIQUE NOT NULL,
    name       VARCHAR(200) NOT NULL,
    active     BOOLEAN      DEFAULT TRUE,
    created_at DATETIME     DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- 2. USERS (NGƯỜI DÙNG)
-- =====================================================
CREATE TABLE users (
    id            INT PRIMARY KEY AUTO_INCREMENT,
    username      VARCHAR(80)  UNIQUE NOT NULL,
    password      VARCHAR(200) NOT NULL,          -- bcrypt hash
    full_name     VARCHAR(200),
    role          VARCHAR(20)  DEFAULT 'student', -- admin | phongdaotao | student
    active        BOOLEAN      DEFAULT TRUE,
    failed_logins INT          DEFAULT 0,
    major_id      INT,                            -- NULL nếu không phải sinh viên
    created_at    DATETIME     DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (major_id) REFERENCES majors(id) ON DELETE SET NULL
);

-- =====================================================
-- 3. COURSES (MÔN HỌC)
-- =====================================================
CREATE TABLE courses (
    id         INT PRIMARY KEY AUTO_INCREMENT,
    code       VARCHAR(20)  UNIQUE NOT NULL,
    name       VARCHAR(200) NOT NULL,
    credits    INT          DEFAULT 3,
    active     BOOLEAN      DEFAULT TRUE,
    created_at DATETIME     DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- 4. SECTIONS (LỚP HỌC PHẦN)
-- Mỗi môn có thể có nhiều lớp (CTDL01, CTDL02...)
-- =====================================================
CREATE TABLE sections (
    id               INT PRIMARY KEY AUTO_INCREMENT,
    code             VARCHAR(30)  UNIQUE NOT NULL,  -- VD: CTDL01
    course_id        INT          NOT NULL,
    instructor       VARCHAR(100),
    schedule         VARCHAR(200),  -- VD: "Thu2,Tiet1-3|Thu4,Tiet1-3"
    semester         VARCHAR(20),
    max_students     INT          DEFAULT 40,
    current_enrolled INT          DEFAULT 0,
    active           BOOLEAN      DEFAULT TRUE,
    created_at       DATETIME     DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
);

-- =====================================================
-- 5. CURRICULUMS (CHƯƠNG TRÌNH ĐÀO TẠO)
-- Mỗi dòng = 1 môn học trong khung của 1 ngành
-- =====================================================
CREATE TABLE curriculums (
    id           INT PRIMARY KEY AUTO_INCREMENT,
    major_id     INT  NOT NULL,
    course_id    INT  NOT NULL,
    semester_no  INT,                       -- Học kỳ khuyến nghị
    is_elective  BOOLEAN DEFAULT FALSE,     -- Tự chọn?
    prerequisite VARCHAR(200),              -- Mã môn tiên quyết (text)
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_curriculum (major_id, course_id),
    FOREIGN KEY (major_id)  REFERENCES majors(id)   ON DELETE CASCADE,
    FOREIGN KEY (course_id) REFERENCES courses(id)  ON DELETE CASCADE
);

-- =====================================================
-- 6. REGISTRATIONS (ĐĂNG KÝ HỌC PHẦN)
-- =====================================================
CREATE TABLE registrations (
    id           INT PRIMARY KEY AUTO_INCREMENT,
    user_id      INT NOT NULL,
    section_id   INT NOT NULL,
    status       VARCHAR(20) DEFAULT 'pending',  -- pending | approved | rejected
    submitted_at DATETIME    DEFAULT CURRENT_TIMESTAMP,
    processed_by INT,
    FOREIGN KEY (user_id)      REFERENCES users(id)    ON DELETE CASCADE,
    FOREIGN KEY (section_id)   REFERENCES sections(id) ON DELETE CASCADE,
    FOREIGN KEY (processed_by) REFERENCES users(id)    ON DELETE SET NULL
);

-- =====================================================
-- 7. NOTIFICATIONS (THÔNG BÁO)
-- =====================================================
CREATE TABLE notifications (
    id         INT PRIMARY KEY AUTO_INCREMENT,
    title      VARCHAR(200) NOT NULL,
    content    TEXT         NOT NULL,
    target     VARCHAR(20)  DEFAULT 'all',  -- all | student | phongdaotao
    created_at DATETIME     DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- 8. SYSTEM_LOGS (NHẬT KÝ)
-- =====================================================
CREATE TABLE system_logs (
    id         INT PRIMARY KEY AUTO_INCREMENT,
    user_id    INT,
    action     VARCHAR(100),
    detail     TEXT,
    ip         VARCHAR(50),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- =====================================================
-- 9. SYSTEM_CONFIG (CẤU HÌNH)
-- =====================================================
CREATE TABLE system_config (
    id    INT PRIMARY KEY AUTO_INCREMENT,
    `key`   VARCHAR(50)  UNIQUE,
    `value` VARCHAR(255)
);

-- =====================================================
-- 10. SEED DATA
-- =====================================================

-- Cấu hình mặc định
INSERT INTO system_config (`key`, `value`) VALUES
    ('max_credits',  '24'),
    ('max_sections', '8'),
    ('min_gpa',      '0.0'),
    ('reg_open',     '1'),
    ('reg_deadline', '');

-- Ngành học (từ dữ liệu ảnh)
INSERT INTO majors (code, name) VALUES
    ('CNTT',  'Công nghệ Thông tin'),
    ('GDTH',  'Giáo dục Tiểu học'),
    ('LUAT',  'Luật'),
    ('HCNN',  'Hành chính Nhà nước'),
    ('QTKD',  'Quản trị Kinh doanh'),
    ('KTOAN', 'Kế toán'),
    ('TCNH',  'Tài chính - Ngân hàng');

-- Lưu ý: Tài khoản admin và phongdaotao được tạo bởi seed_all() trong main.py
-- vì cần bcrypt hash. Chạy: python main.py một lần để seed.

-- =====================================================
-- KIỂM TRA
-- =====================================================
SHOW TABLES;
SELECT * FROM majors;
SELECT * FROM system_config;
SELECT '✅ SCHEMA v2 CREATED SUCCESSFULLY!' AS STATUS;