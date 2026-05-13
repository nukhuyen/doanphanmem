import sys
import os
# Thêm dòng này để Python tìm thấy các file ở thư mục gốc
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database import db