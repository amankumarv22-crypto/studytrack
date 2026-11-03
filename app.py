import os
from collections import defaultdict
from datetime import date, timedelta
from flask import (Flask, render_template, request, redirect, url_for,
                   flash, send_from_directory)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (LoginManager, UserMixin, login_user, logout_user,
                         login_required, current_user)
from sqlalchemy import inspect, text
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-before-deploying")
db_url = os.environ.get("DATABASE_URL", "sqlite:///studytrack.db")
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"


class User(UserMixin, db.Model):
    __tablename__ = "st_user"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)


class Assignment(db.Model):
    __tablename__ = "st_assignment"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("st_user.id"), nullable=False)
    title = db.Column(db.String(120), nullable=False)
    subject = db.Column(db.String(80), nullable=False)
    deadline = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="Pending")
    priority = db.Column(db.String(10), nullable=False, default="Medium")


class Assessment(db.Model):
    __tablename__ = "st_assessment"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("st_user.id"), nullable=False)
    subject = db.Column(db.String(80), nullable=False)
    assessment_name = db.Column(db.String(120), nullable=False)
    marks_obtained = db.Column(db.Float, nullable=False)
    maximum_marks = db.Column(db.Float, nullable=False)

    @property
    def percentage(self):
        if self.maximum_marks <= 0:
            return 0
        return round(self.marks_obtained / self.maximum_marks * 100, 2)


class Activity(db.Model):
    __tablename__ = "st_activity"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("st_user.id"), nullable=False)
    day = db.Column(db.Date, nullable=False)


class Goal(db.Model):
    __tablename__ = "st_goal"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("st_user.id"), nullable=False)
    subject = db.Column(db.String(80), nullable=False)
    target = db.Column(db.Float, nullable=False)


with app.app_context():
    db.create_all()
    # Add the priority column to databases created before this version.
    if "priority" not in [c["name"] for c in inspect(db.engine).get_columns("st_assignment")]:
        db.session.execute(text("ALTER TABLE st_assignment ADD COLUMN priority VARCHAR(10) DEFAULT 'Medium'"))
        db.session.commit()


def log_activity():
    today = date.today()
    if not Activity.query.filter_by(user_id=current_user.id, day=today).first():
        db.session.add(Activity(user_id=current_user.id, day=today))
        db.session.commit()


@app.template_filter("hue")
def hue(text):
    palette = [215, 150, 28, 330, 265, 180, 355, 48]
    return palette[sum(ord(c) * (i + 1) for i, c in enumerate(str(text).lower())) % len(palette)]


@login_manager.user_loader
def load_user(uid):
