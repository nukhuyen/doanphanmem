from main import app
from models import User

with app.app_context():
    users = User.query.all()
    if not users:
        print('No users found in database')
    for u in users:
        print(f'username={u.username!s} | password={u.password!s} | role={u.role!s} | active={u.active!s}')
