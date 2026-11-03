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
db_url = os.environ.get("DATABASE_URL", "sqlite:///studytrack.db").strip()
# Always use the psycopg2 driver (the one installed in requirements.txt),
# whichever form of PostgreSQL address was pasted into DATABASE_URL.
for _prefix in ("postgres://", "postgresql://", "postgresql+psycopg://"):
    if db_url.startswith(_prefix):
        db_url = "postgresql+psycopg2://" + db_url[len(_prefix):]
        break
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
    return db.session.get(User, int(uid))


@app.route("/manifest.json")
def manifest():
    return send_from_directory("static", "manifest.json", mimetype="application/manifest+json")


@app.route("/sw.js")
def sw():
    r = send_from_directory("static", "sw.js", mimetype="application/javascript")
    r.headers["Service-Worker-Allowed"] = "/"
    return r


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        pw = request.form.get("password", "")
        if not name or not email or len(pw) < 6:
            flash("Enter name, email and a password of 6+ characters.", "error")
        elif User.query.filter_by(email=email).first():
            flash("That email is already registered.", "error")
        else:
            u = User(name=name, email=email, password_hash=generate_password_hash(pw))
            db.session.add(u)
            db.session.commit()
            login_user(u)
            return redirect(url_for("index"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = User.query.filter_by(email=request.form.get("email", "").strip().lower()).first()
        if u and check_password_hash(u.password_hash, request.form.get("password", "")):
            login_user(u)
            return redirect(url_for("index"))
        flash("Wrong email or password.", "error")
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def index():
    uid = current_user.id
    assignments = Assignment.query.filter_by(user_id=uid).order_by(
        Assignment.deadline.asc(), Assignment.id.desc()).all()
    assessments = Assessment.query.filter_by(user_id=uid).order_by(Assessment.id.desc()).all()
    today = date.today()
    total = len(assignments)
    completed = sum(1 for a in assignments if a.status == "Completed")
    pending_list = [a for a in assignments if a.status == "Pending"]
    overdue = [a for a in pending_list if a.deadline and a.deadline < today]
    due_today = [a for a in pending_list if a.deadline == today]
    average = (round(sum(a.percentage for a in assessments) / len(assessments), 2)
               if assessments else None)
    data = defaultdict(list)
    for a in assessments:
        data[a.subject].append(a.percentage)
    subject_averages = [{"subject": s, "average": round(sum(v) / len(v), 2), "count": len(v)}
                        for s, v in sorted(data.items())]
    dated = sorted((a for a in pending_list if a.deadline and a.deadline >= today), key=lambda a: a.deadline)
    next_due = dated[0] if dated else None
    subjects = sorted({a.subject for a in assignments})
    days = {x.day for x in Activity.query.filter_by(user_id=uid).all()}
    d = today if today in days else today - timedelta(days=1)
    streak = 0
    while d in days:
        streak += 1
        d -= timedelta(days=1)
    monday = today - timedelta(days=today.weekday())
    due_by = defaultdict(int)
    for a in pending_list:
        if a.deadline:
            due_by[a.deadline] += 1
    week = [{"name": (monday + timedelta(days=k)).strftime("%a"), "num": (monday + timedelta(days=k)).day,
             "today": monday + timedelta(days=k) == today, "due": due_by.get(monday + timedelta(days=k), 0),
             "active": (monday + timedelta(days=k)) in days} for k in range(7)]
    upnext = sorted((a for a in pending_list if a.deadline), key=lambda a: a.deadline)[:3]
    avg_map = {r["subject"]: r["average"] for r in subject_averages}
    goal_rows = []
    for g in Goal.query.filter_by(user_id=uid).order_by(Goal.subject).all():
        avg = avg_map.get(g.subject)
        if avg is None:
            pct, note = 0, "Add marks to track this goal."
        else:
            pct = min(100, round(avg / g.target * 100))
            note = "Goal reached." if avg >= g.target else f"{round(g.target - avg, 1)}% to go."
        goal_rows.append({"id": g.id, "subject": g.subject, "target": g.target, "avg": avg, "pct": pct, "note": note})
    return render_template("index.html", assignments=assignments, assessments=assessments,
                           total=total, completed=completed, pending=total - completed,
                           average=average, today=today, overdue=overdue,
                           due_today=due_today, subject_averages=subject_averages,
                           subjects=subjects, next_due=next_due, streak=streak, goal_rows=goal_rows, week=week, upnext=upnext)


@app.post("/assignments/add")
@login_required
def add_assignment():
    title = request.form.get("title", "").strip()
    subject = request.form.get("subject", "").strip()
    raw = request.form.get("deadline", "").strip()
    if not title or not subject:
        flash("Please enter both an assignment title and subject.", "error")
        return redirect(url_for("index"))
    try:
        deadline = date.fromisoformat(raw) if raw else None
    except ValueError:
        flash("Please enter a valid deadline.", "error")
        return redirect(url_for("index"))
    priority = request.form.get("priority", "Medium")
    if priority not in ("High", "Medium", "Low"):
        priority = "Medium"
    db.session.add(Assignment(user_id=current_user.id, title=title, subject=subject,
                              deadline=deadline, priority=priority))
    db.session.commit()
    flash("Assignment added.", "success")
    return redirect(url_for("index"))


def own(model, item_id):
    item = db.get_or_404(model, item_id)
    if item.user_id != current_user.id:
        from flask import abort
        abort(403)
    return item


@app.route("/assignments/<int:item_id>/edit", methods=["GET", "POST"])
@login_required
def edit_assignment(item_id):
    a = own(Assignment, item_id)
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        subject = request.form.get("subject", "").strip()
        raw = request.form.get("deadline", "").strip()
        priority = request.form.get("priority", "Medium")
        try:
            deadline = date.fromisoformat(raw) if raw else None
        except ValueError:
            deadline = a.deadline
        if not title or not subject:
            flash("Title and subject cannot be empty.", "error")
        else:
            a.title, a.subject, a.deadline = title, subject, deadline
            a.priority = priority if priority in ("High", "Medium", "Low") else "Medium"
            db.session.commit()
            flash("Assignment updated.", "success")
            return redirect(url_for("index"))
    return render_template("edit.html", a=a)


@app.route("/about")
def about():
    return render_template("about.html")


@app.errorhandler(404)
def not_found(e):
    return render_template("error.html"), 404


@app.post("/assignments/<int:item_id>/status")
@login_required
def update_status(item_id):
    a = own(Assignment, item_id)
    a.status = "Completed" if a.status == "Pending" else "Pending"
    db.session.commit()
    if a.status == "Completed":
        log_activity()
    return redirect(url_for("index"))


@app.post("/assignments/<int:item_id>/delete")
@login_required
def delete_assignment(item_id):
    db.session.delete(own(Assignment, item_id))
    db.session.commit()
    flash("Assignment deleted.", "success")
    return redirect(url_for("index"))


@app.post("/assessments/add")
@login_required
def add_assessment():
    subject = request.form.get("subject", "").strip()
    name = request.form.get("assessment_name", "").strip()
    try:
        got = float(request.form.get("marks_obtained", ""))
        mx = float(request.form.get("maximum_marks", ""))
    except (ValueError, TypeError):
        flash("Enter valid numbers for marks.", "error")
        return redirect(url_for("index"))
    if not subject or not name:
        flash("Please enter a subject and assessment name.", "error")
    elif mx <= 0 or got < 0 or got > mx:
        flash("Obtained marks must be between 0 and the maximum.", "error")
    else:
        db.session.add(Assessment(user_id=current_user.id, subject=subject,
                                  assessment_name=name, marks_obtained=got, maximum_marks=mx))
        db.session.commit()
        log_activity()
        flash("Assessment saved.", "success")
    return redirect(url_for("index"))


@app.post("/assessments/<int:item_id>/delete")
@login_required
def delete_assessment(item_id):
    db.session.delete(own(Assessment, item_id))
    db.session.commit()
    flash("Assessment deleted.", "success")
    return redirect(url_for("index"))


@app.post("/goals/set")
@login_required
def set_goal():
    subject = request.form.get("subject", "").strip()
    try:
        target = float(request.form.get("target", ""))
    except (ValueError, TypeError):
        target = 0
    if not subject or not 1 <= target <= 100:
        flash("Enter a subject and a target between 1 and 100.", "error")
        return redirect(url_for("index"))
    g = Goal.query.filter_by(user_id=current_user.id, subject=subject).first()
    if g:
        g.target = target
    else:
        db.session.add(Goal(user_id=current_user.id, subject=subject, target=target))
    db.session.commit()
    flash("Goal saved.", "success")
    return redirect(url_for("index"))


@app.post("/goals/<int:item_id>/delete")
@login_required
def delete_goal(item_id):
    db.session.delete(own(Goal, item_id))
    db.session.commit()
    flash("Goal removed.", "success")
    return redirect(url_for("index"))


@app.route("/demo")
def demo():
    email = "demo@studytrack.app"
    u = User.query.filter_by(email=email).first()
    if not u:
        u = User(name="Demo Student", email=email,
                 password_hash=generate_password_hash(os.urandom(16).hex()))
        db.session.add(u)
        db.session.commit()
    if not Assignment.query.filter_by(user_id=u.id).first():
        t = date.today()
        for title, sub, off, st in [
            ("Android lab report", "Android", -1, "Pending"), ("Java quiz prep", "Java", 0, "Pending"),
            ("DBMS ER diagram", "DBMS", 3, "Pending"), ("Networks notes", "Networks", 6, "Pending"),
            ("Maths sheet 4", "Maths", -5, "Completed"), ("OS assignment", "OS", -2, "Completed")]:
            db.session.add(Assignment(user_id=u.id, title=title, subject=sub,
                                      deadline=t + timedelta(days=off), status=st,
                                      priority=("High" if off <= 0 and st == "Pending" else "Medium" if off < 4 else "Low")))
        for sub, name, got, mx in [("Android", "Mid-term", 42, 50), ("Java", "Quiz 1", 16, 20),
                                   ("DBMS", "Mid-term", 34, 50), ("Maths", "Unit test", 38, 50)]:
            db.session.add(Assessment(user_id=u.id, subject=sub, assessment_name=name,
                                      marks_obtained=got, maximum_marks=mx))
        db.session.add(Goal(user_id=u.id, subject="Android", target=80))
        db.session.add(Goal(user_id=u.id, subject="DBMS", target=80))
        for k in range(3):
            db.session.add(Activity(user_id=u.id, day=t - timedelta(days=k)))
        db.session.commit()
    login_user(u)
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)
