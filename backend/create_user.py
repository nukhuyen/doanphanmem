from main import app
from database import db
from models import User

users = [
    ("admin", "Abc123", "admin"),
    ("pdt", "Abc123", "training"),
    ("sv", "Abc123", "student"),
]

with app.app_context():
    db.create_all()
    created = []
    updated = []
    for username, password, role in users:
        u = User.query.filter_by(username=username).first()
        if not u:
            u = User(username=username, password=password, role=role, active=True)
            db.session.add(u)
            created.append(username)
        else:
            u.password = password
            u.role = role
            u.active = True
            updated.append(username)

    db.session.commit()

    if created:
        print('Created users:', ', '.join(created))
    if updated:
        print('Updated users:', ', '.join(updated))
    if not created and not updated:
        print('No changes; users already present with the given values.')
