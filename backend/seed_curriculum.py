"""
seed_curriculum.py
Nạp toàn bộ môn học + chương trình đào tạo từ dữ liệu ảnh vào DB.
Chạy sau khi đã tạo DB và chạy main.py một lần (để có bảng).

    python seed_curriculum.py
"""
from main import app
from database import db
from models import Major, Course, Curriculum

# ══════════════════════════════════════════════════════════════════════
# DỮ LIỆU CURRICULUM
# Format: (ma_mon, ten_mon, so_tc, hoc_ky, tu_chon)
# ══════════════════════════════════════════════════════════════════════

CURRICULUM_DATA = {

    # ------------------------------------------------------------------
    # CÔNG NGHỆ THÔNG TIN (ảnh 1–2)
    # ------------------------------------------------------------------
    'CNTT': [
        ('10903611', 'Kỹ năng giao tiếp',                          1, 1, True),
        ('1010003',  'Triết học Mác-Lênin',                        3, 1, False),
        ('1020052',  'Pháp luật đại cương',                        2, 1, False),
        ('1040101',  'Giáo dục thể chất 1',                        1, 1, True),
        ('1060163',  'Tin học văn phòng',                          3, 1, False),
        ('1301001',  'Nhập môn ngành Công nghệ thông tin',         1, 1, False),
        ('1301014',  'Kỹ thuật Lập trình',                         4, 1, False),
        ('1301021',  'Tư duy thiết kế',                            1, 1, False),
        ('1090333',  'Giải tích',                                   3, 1, False),
        ('1090371',  'Kỹ năng lập kế hoạch và quản lý thời gian', 1, 1, False),
        ('1301044',  'Lập trình cơ bản với C',                     4, 1, False),
        ('1301054',  'Cấu trúc dữ liệu & giải thuật',              4, 1, False),
        ('1010012',  'Kinh tế chính trị Mác-Lênin',                2, 1, False),
        ('1301033',  'Toán rời rạc',                               3, 1, False),
        ('1040111',  'Giáo dục thể chất 2',                        1, 1, True),
        ('1090342',  'Đại số tuyến tính',                          2, 1, False),
        ('1030063',  'Tiếng Anh 1',                                3, 1, False),
        ('1301082',  'Cấu trúc máy tính',                          2, 1, False),
        ('1301063',  'Cơ sở dữ liệu I',                            3, 1, False),
        ('1301102',  'Lý thuyết đồ thị',                           2, 1, False),
        ('1301073',  'Mạng Máy tính',                              3, 1, False),
        ('1301093',  'Thiết kế Web',                               3, 1, False),
        ('1090352',  'Xác suất thống kê',                          2, 1, False),
        ('1010022',  'Chủ nghĩa Xã hội khoa học',                  2, 1, False),
        ('1040121',  'Giáo dục thể chất 3',                        1, 1, True),
        ('1030073',  'Tiếng Anh 2',                                3, 1, False),
        ('1040131',  'Giáo dục thể chất 4',                        1, 4, True),
        ('1030083',  'Tiếng Anh 3',                                3, 4, False),
        ('1010032',  'Tư tưởng Hồ Chí Minh',                       2, 4, False),
        ('1304003',  'Cơ sở dữ liệu II',                           3, 4, False),
        ('1304022',  'Đồ hoạ ứng dụng',                            2, 4, False),
        ('1304243',  'Hệ điều hành',                               3, 4, False),
        ('1301113',  'Lập trình hướng đối tượng',                  3, 4, False),
        ('1304014',  'Lập trình Web nâng cao',                     4, 4, False),
        ('1090381',  'Kỹ năng làm việc nhóm',                      1, 4, False),
        ('1304103',  'CSDL phi quan hệ',                           3, 5, False),
        ('1304044',  'Lập trình Java',                             4, 5, False),
        ('1304064',  'Lập trình Python',                           4, 5, False),
        ('1304033',  'Phân tích thiết kế hệ thống hướng đối tượng', 3, 5, False),
        ('1010042',  'Lịch sử của Đảng cộng sản Việt Nam',         2, 5, False),
        ('1030093',  'Tiếng Anh 4',                                3, 5, False),
        ('1304283',  'Khởi nghiệp',                                3, 5, False),
        ('1304053',  'Quản trị mạng',                              3, 5, False),
    ],

    # ------------------------------------------------------------------
    # GIÁO DỤC TIỂU HỌC (ảnh 3–4)
    # ------------------------------------------------------------------
    'GDTH': [
        ('1040101',  'Giáo dục thể chất 1',                                 1, 1, True),
        ('1111023',  'Cơ sở Việt ngữ 1 của việc dạy học tiếng Việt tiểu học', 3, 1, False),
        ('1111043',  'Cơ sở Toán học 1 của việc dạy học toán tiểu học',     3, 1, False),
        ('1114002',  'Nhập môn Giáo dục Tiểu học',                          2, 1, False),
        ('1114124',  'Tâm lý học Sư phạm tiểu học',                         4, 1, False),
        ('1060172',  'Tin học đại cương (Tin học CN1)',                      2, 1, False),
        ('1010003',  'Triết học Mác-Lênin',                                 3, 1, True),
        ('1010012',  'Kinh tế chính trị Mác-Lênin',                         2, 2, False),
        ('1040111',  'Giáo dục thể chất 2',                                 1, 2, True),
        ('1114024',  'Văn học thiếu nhi',                                   4, 2, False),
        ('1111033',  'Cơ sở Việt ngữ 2 của việc dạy học tiếng Việt tiểu học', 3, 2, False),
        ('1111053',  'Cơ sở Toán học 2 của việc dạy học toán tiểu học',     3, 2, False),
        ('1114133',  'Giáo dục học tiểu học',                               3, 2, False),
        ('1030063',  'Tiếng Anh 1',                                         3, 2, False),
        ('1010022',  'Chủ nghĩa Xã hội khoa học',                           2, 3, False),
        ('1030073',  'Tiếng Anh 2',                                         3, 3, False),
        ('1111002',  'Cơ sở văn hóa Việt Nam',                              2, 3, False),
        ('1114043',  'Cơ sở Khoa học Tự nhiên ở tiểu học',                  3, 3, False),
        ('1040121',  'Giáo dục thể chất 3',                                 1, 3, True),
        ('1020052',  'Pháp luật đại cương',                                 2, 3, False),
        ('1111062',  'Sinh lí học trẻ em',                                  2, 3, False),
        ('1111012',  'Tiếng Việt thực hành ở tiểu học',                     2, 3, False),
        ('SP.251',   'Xác suất và thống kê trong giáo dục tiểu học',        2, 3, False),
        ('1114142',  'Thực hành tổ chức hoạt động giáo dục',                2, 3, False),
        ('1111072',  'Xác suất và Thống kê trong giáo dục tiểu học',        2, 3, False),
    ],

    # ------------------------------------------------------------------
    # LUẬT (ảnh 5–6)
    # ------------------------------------------------------------------
    'LUAT': [
        ('1010003',  'Triết học Mác-Lênin',                        3, 1, False),
        ('1060152',  'Tin học đại cương',                          2, 1, False),
        ('1070192',  'Logic học',                                   2, 1, False),
        ('1070203',  'Kinh tế học',                                 3, 1, False),
        ('1040101',  'Giáo dục thể chất 1',                        1, 1, True),
        ('1101003',  'Lịch sử nhà nước và pháp luật',              3, 1, False),
        ('1070182',  'Giao tiếp trong kinh doanh',                  2, 1, False),
        ('1010012',  'Kinh tế chính trị Mác-Lênin',                2, 1, False),
        ('1040111',  'Giáo dục thể chất 2',                        1, 1, True),
        ('1101014',  'Lý luận chung về Nhà nước và Pháp luật',     4, 1, False),
        ('1060163',  'Tin học văn phòng',                          3, 1, False),
        ('1070212',  'Quản trị học',                               2, 1, False),
        ('1101033',  'Luật Hiến pháp',                             3, 1, False),
        ('1030063',  'Tiếng Anh 1',                                3, 1, False),
        ('1010022',  'Chủ nghĩa Xã hội khoa học',                  2, 1, False),
        ('1010032',  'Tư tưởng Hồ Chí Minh',                       2, 1, False),
        ('1030073',  'Tiếng Anh 2',                                3, 1, False),
        ('1040121',  'Giáo dục thể chất 3',                        1, 1, True),
        ('1101063',  'Luật dân sự 1',                              3, 1, False),
        ('1101043',  'Luật Hành chính',                            3, 1, False),
        ('1101053',  'Luật Hình sự 1',                             3, 1, False),
        ('1101083',  'Công pháp quốc tế',                          3, 4, False),
        ('1040131',  'Giáo dục thể chất 4',                        1, 4, True),
        ('1109512',  'Kiến tập năm 2',                             2, 4, False),
        ('1010042',  'Lịch sử của Đảng cộng sản Việt Nam',         2, 4, False),
        ('1101073',  'Luật dân sự 2',                              3, 4, False),
        ('1101123',  'Luật hình sự 2',                             3, 4, False),
        ('1104003',  'Luật Thương mại 1',                          3, 4, False),
        ('1030083',  'Tiếng Anh 3',                                3, 4, False),
        ('1101093',  'Kỹ năng nghiên cứu và lập luận',             3, 5, False),
        ('1104053',  'Luật đất đai',                               3, 5, False),
        ('1101102',  'Luật Hôn nhân – Gia đình',                   2, 5, False),
        ('1104013',  'Luật thương mại 2',                          3, 5, False),
        ('1101153',  'Luật tố tụng dân sự',                        3, 5, False),
        ('1101143',  'Luật tố tụng hình sự',                       3, 5, False),
        ('1030093',  'Tiếng Anh 4',                                3, 5, False),
    ],

    # ------------------------------------------------------------------
    # HÀNH CHÍNH NHÀ NƯỚC (ảnh 7–8)
    # ------------------------------------------------------------------
    'HCNN': [
        ('1232062',  'Chính phủ điện tử',                          2, 1, True),
        ('1232012',  'Giao tiếp cộng đồng',                        2, 1, True),
        ('1234032',  'Quản lý nhà nước về nông thôn - đô thị',     2, 1, True),
        ('1232043',  'Quản lý nguồn nhân lực trong tổ chức công',  3, 1, True),
        ('1232022',  'Tâm lý học trong quản lý nhà nước',          2, 1, True),
        ('1010032',  'Tư tưởng Hồ Chí Minh',                       2, 1, True),
        ('1030083',  'Tiếng Anh 3',                                3, 1, True),
        ('1101043',  'Luật Hành chính',                            3, 1, True),
        ('1040131',  'Giáo dục thể chất 4',                        1, 1, True),
        ('1010003',  'Triết học Mác-Lênin',                        3, 1, False),
        ('1231034',  'Lí luận Nhà nước và Pháp luật',              3, 1, False),
        ('1060152',  'Tin học đại cương',                          2, 1, False),
        ('1040101',  'Giáo dục thể chất 1',                        1, 1, True),
        ('1230012',  'Quản lý học',                                 2, 1, False),
        ('1291003',  'Kinh tế vi mô',                              3, 1, False),
        ('1080283',  'Kỹ năng mềm',                                3, 1, False),
        ('1080322',  'Xã hội học',                                  2, 2, False),
        ('1060163',  'Tin học văn phòng',                          3, 2, False),
        ('1231022',  'Chính trị học',                              2, 2, False),
        ('1040111',  'Giáo dục thể chất 2',                        1, 2, True),
        ('1070192',  'Logic học',                                   2, 2, False),
        ('1234002',  'Tổ chức bộ máy hành chính nhà nước',         2, 2, False),
        ('1291013',  'Kinh tế vĩ mô',                              3, 2, False),
        ('1030063',  'Tiếng Anh 1',                                3, 2, False),
        ('1010012',  'Kinh tế chính trị Mác-Lênin',                2, 2, False),
        ('1040121',  'Giáo dục thể chất 3',                        1, 3, True),
        ('1231052',  'Luật hiến pháp',                             2, 3, False),
        ('1030073',  'Tiếng Anh 2',                                3, 3, False),
        ('1232003',  'Lý luận hành chính Nhà nước',                3, 3, False),
        ('1231092',  'Đại cương văn hóa Việt Nam',                 2, 3, False),
        ('1234083',  'Kĩ thuật soạn thảo văn bản',                 3, 3, False),
        ('1010022',  'Chủ nghĩa Xã hội khoa học',                  2, 3, False),
        ('1234053',  'Hành chính công',                            3, 3, False),
        ('1291072',  'Hệ thống thông tin quản lý',                 2, 3, False),
    ],

    # ------------------------------------------------------------------
    # QUẢN TRỊ KINH DOANH (ảnh 9–10)
    # ------------------------------------------------------------------
    'QTKD': [
        ('1080283',  'Kỹ năng mềm',                                3, 1, False),
        ('1291003',  'Kinh tế vi mô',                              3, 1, False),
        ('1291023',  'Quản trị học',                               3, 1, False),
        ('1060152',  'Tin học đại cương',                          2, 1, False),
        ('1010003',  'Triết học Mác-Lênin',                        3, 1, False),
        ('1020052',  'Pháp luật đại cương',                        2, 1, False),
        ('1040101',  'Giáo dục thể chất 1',                        1, 1, True),
        ('1060163',  'Tin học văn phòng',                          3, 2, False),
        ('1040111',  'Giáo dục thể chất 2',                        1, 2, True),
        ('1291013',  'Kinh tế vĩ mô',                              3, 2, False),
        ('1291033',  'Nguyên lý kế toán',                          3, 2, False),
        ('1291043',  'Marketing căn bản',                          3, 2, False),
        ('1030063',  'Tiếng Anh 1',                                3, 2, False),
        ('1291053',  'Luật kinh doanh',                            3, 3, False),
        ('1030073',  'Tiếng Anh 2',                                3, 3, False),
        ('1292013',  'Hệ thống thông tin quản lý',                 3, 3, False),
        ('1292023',  'Thị trường và các định chế tài chính',       3, 3, False),
        ('1040121',  'Giáo dục thể chất 3',                        1, 3, True),
        ('1080263',  'Toán ứng dụng trong kinh tế',                3, 3, False),
        ('1010012',  'Kinh tế chính trị Mác-Lênin',                2, 3, False),
        ('1209512',  'Kiến tập năm 2',                             2, 4, False),
        ('1080273',  'Thống kê kinh doanh và kinh tế',             3, 4, False),
        ('1292033',  'Hành vi tổ chức',                            3, 4, False),
        ('1292003',  'Kinh doanh quốc tế',                         3, 4, False),
        ('1204073',  'Nghiên cứu Marketing',                       3, 4, False),
        ('1030083',  'Tiếng Anh 3',                                3, 4, False),
        ('1040131',  'Giáo dục thể chất 4',                        1, 4, True),
        ('1010022',  'Chủ nghĩa Xã hội khoa học',                  2, 4, False),
        ('1080293',  'Giao tiếp trong kinh doanh',                  3, 4, False),
        ('1010032',  'Tư tưởng Hồ Chí Minh',                       2, 5, False),
        ('1209073',  'Hành vi người tiêu dùng',                    3, 5, False),
        ('1204083',  'Quản trị chuỗi cung ứng',                    3, 5, False),
        ('1204013',  'Quản trị Marketing',                         3, 5, False),
        ('1204043',  'Quản trị nguồn nhân lực',                    3, 5, False),
        ('1204033',  'Quản trị sản xuất',                          3, 5, False),
        ('1030093',  'Tiếng Anh 4',                                3, 5, False),
        ('1010042',  'Lịch sử của Đảng cộng sản Việt Nam',         2, 5, False),
    ],

    # ------------------------------------------------------------------
    # KẾ TOÁN (ảnh 11–12)
    # ------------------------------------------------------------------
    'KTOAN': [
        ('1222053',  'Kế toán quản trị',                           3, 1, True),
        ('1010003',  'Triết học Mác-Lênin',                        3, 1, False),
        ('1020052',  'Pháp luật đại cương',                        2, 1, False),
        ('1040101',  'Giáo dục thể chất 1',                        1, 1, True),
        ('1080283',  'Kỹ năng mềm',                                3, 1, False),
        ('1291003',  'Kinh tế vi mô',                              3, 1, False),
        ('1291023',  'Quản trị học',                               3, 1, False),
        ('1060152',  'Tin học đại cương',                          2, 1, False),
        ('1010012',  'Kinh tế chính trị Mác-Lênin',                2, 2, False),
        ('1040111',  'Giáo dục thể chất 2',                        1, 2, True),
        ('1060163',  'Tin học văn phòng',                          3, 2, False),
        ('1291013',  'Kinh tế vĩ mô',                              3, 2, False),
        ('1291033',  'Nguyên lý kế toán',                          3, 2, False),
        ('1080263',  'Toán ứng dụng trong kinh tế',                3, 2, False),
        ('1030063',  'Tiếng Anh 1',                                3, 2, False),
        ('1010022',  'Chủ nghĩa Xã hội khoa học',                  2, 3, False),
        ('1030073',  'Tiếng Anh 2',                                3, 3, False),
        ('1040121',  'Giáo dục thể chất 3',                        1, 3, True),
        ('1080293',  'Giao tiếp trong kinh doanh',                  3, 3, False),
        ('1222043',  'Kế toán tài chính 1',                        3, 3, False),
        ('1291043',  'Marketing căn bản',                          3, 3, False),
        ('1080273',  'Thống kê kinh doanh và kinh tế',             3, 3, False),
        ('1222093',  'Hệ thống thông tin kế toán',                 3, 4, False),
        ('1222083',  'Kế toán tài chính 2',                        3, 4, False),
        ('1224063',  'Kế toán thuế',                               3, 4, False),
        ('1229512',  'Kiến tập năm 2',                             2, 4, False),
        ('1010032',  'Tư tưởng Hồ Chí Minh',                       2, 4, False),
        ('1030083',  'Tiếng Anh 3',                                3, 4, False),
        ('1291053',  'Luật kinh doanh',                            3, 4, False),
        ('1040131',  'Giáo dục thể chất 4',                        1, 4, True),
        ('1292033',  'Hành vi tổ chức',                            3, 5, False),
        ('1224053',  'Kế toán công ty',                            3, 5, False),
        ('1299003',  'Khởi nghiệp',                                3, 5, False),
        ('1211003',  'Nghiệp vụ ngân hàng thương mại',             3, 5, False),
        ('1030093',  'Tiếng Anh 4',                                3, 5, False),
        ('1010042',  'Lịch sử của Đảng cộng sản Việt Nam',         2, 5, False),
        ('1229103',  'Tài chính công ty',                          3, 5, False),
    ],

    # ------------------------------------------------------------------
    # TÀI CHÍNH - NGÂN HÀNG (ảnh 13–14)
    # ------------------------------------------------------------------
    'TCNH': [
        ('1212083',  'Tài chính công',                             3, 1, True),
        ('1010042',  'Lịch sử của Đảng cộng sản Việt Nam',         2, 1, True),
        ('1212103',  'Tiếng Anh chuyên ngành',                     3, 1, True),
        ('1214033',  'Phân tích tín dụng và cho vay',              3, 1, True),
        ('1209033',  'Quản trị quan hệ khách hàng',                3, 1, True),
        ('12291031', 'Thuế',                                       3, 1, True),
        ('12395231', 'Thực tập năm 3',                             3, 1, True),
        ('1010003',  'Triết học Mác-Lênin',                        3, 1, False),
        ('1020052',  'Pháp luật đại cương',                        2, 1, False),
        ('1040101',  'Giáo dục thể chất 1',                        1, 1, True),
        ('1060152',  'Tin học đại cương',                          2, 1, False),
        ('1080283',  'Kỹ năng mềm',                                3, 1, False),
        ('1291003',  'Kinh tế vi mô',                              3, 1, False),
        ('1291023',  'Quản trị học',                               3, 1, False),
        ('1224083',  'Kiểm toán',                                  3, 1, False),
        ('1060163',  'Tin học văn phòng',                          3, 2, False),
        ('1040111',  'Giáo dục thể chất 2',                        1, 2, True),
        ('1080263',  'Toán ứng dụng trong kinh tế',                3, 2, False),
        ('1080293',  'Giao tiếp trong kinh doanh',                  3, 2, False),
        ('1291013',  'Kinh tế vĩ mô',                              3, 2, False),
        ('1291043',  'Marketing căn bản',                          3, 2, False),
        ('1030063',  'Tiếng Anh 1',                                3, 2, False),
        ('1040121',  'Giáo dục thể chất 3',                        1, 3, True),
        ('1010012',  'Kinh tế chính trị Mác-Lênin',                2, 3, False),
        ('1030073',  'Tiếng Anh 2',                                3, 3, False),
        ('1212052',  'Toán tài chính',                             2, 3, False),
        ('1080273',  'Thống kê kinh doanh và kinh tế',             3, 3, False),
        ('1292023',  'Thị trường và các định chế tài chính',       3, 3, False),
        ('1291033',  'Nguyên lý kế toán',                          3, 3, False),
        ('1221043',  'Kế toán tài chính',                          3, 4, False),
        ('1219512',  'Kiến tập năm 2',                             2, 4, False),
        ('1212073',  'Nghiệp vụ ngân hàng thương mại',             3, 4, False),
        ('1212063',  'Tài chính công ty',                          3, 4, False),
        ('1030083',  'Tiếng Anh 3',                                3, 4, False),
        ('1291053',  'Luật kinh doanh',                            3, 4, False),
        ('1040131',  'Giáo dục thể chất 4',                        1, 4, True),
        ('1010022',  'Chủ nghĩa Xã hội khoa học',                  2, 4, False),
        ('1030093',  'Tiếng Anh 4',                                3, 5, False),
        ('1010032',  'Tư tưởng Hồ Chí Minh',                       2, 5, False),
        ('1292033',  'Hành vi tổ chức',                            3, 5, False),
        ('1299003',  'Khởi nghiệp',                                3, 5, False),
        ('1224003',  'Phân tích tài chính doanh nghiệp',           3, 5, False),
        ('1214053',  'Quản trị ngân hàng',                         3, 5, False),
    ],
}


def seed_curriculum():
    with app.app_context():
        db.create_all()

        total_courses = 0
        total_currs   = 0

        for major_code, items in CURRICULUM_DATA.items():
            major = Major.query.filter_by(code=major_code).first()
            if not major:
                print(f'[SKIP] Ngành {major_code} chưa có trong DB. Chạy mysql.sql trước.')
                continue

            print(f'\n[{major_code}] {major.name}')

            for (code, name, credits, semester_no, is_elective) in items:
                # Upsert course
                course = Course.query.filter_by(code=code).first()
                if not course:
                    course = Course(code=code, name=name, credits=credits, active=True)
                    db.session.add(course)
                    db.session.flush()  # lấy id ngay
                    total_courses += 1
                    print(f'  + Môn mới: {code} – {name}')

                # Upsert curriculum
                curr = Curriculum.query.filter_by(
                    major_id=major.id, course_id=course.id).first()
                if not curr:
                    curr = Curriculum(
                        major_id=major.id,
                        course_id=course.id,
                        semester_no=semester_no,
                        is_elective=is_elective,
                    )
                    db.session.add(curr)
                    total_currs += 1

        db.session.commit()
        print(f'\n✅ XONG: {total_courses} môn mới, {total_currs} mục curriculum.')


if __name__ == '__main__':
    seed_curriculum()