import os
from datetime import date
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-before-deploying")

database_url = os.environ.get("DATABASE_URL", "sqlite:///studytrack.db")
# Some providers supply postgres://; SQLAlchemy expects postgresql://.
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)


class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    subject = db.Column(db.String(80), nullable=False)
    deadline = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="Pending")


class Assessment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(80), nullable=False)
    assessment_name = db.Column(db.String(120), nullable=False)
    marks_obtained = db.Column(db.Float, nullable=False)
    maximum_marks = db.Column(db.Float, nullable=False)

    @property
    def percentage(self):
        if self.maximum_marks <= 0:
            return 0
        return round((self.marks_obtained / self.maximum_marks) * 100, 2)


with app.app_context():
    db.create_all()


@app.route("/")
def index():
    assignments = Assignment.query.order_by(Assignment.deadline.asc(), Assignment.id.desc()).all()
    assessments = Assessment.query.order_by(Assessment.id.desc()).all()
    total = len(assignments)
    completed = sum(1 for item in assignments if item.status == "Completed")
    pending = total - completed
    average = round(sum(item.percentage for item in assessments) / len(assessments), 2) if assessments else None
    return render_template(
        "index.html",
        assignments=assignments,
        assessments=assessments,
        total=total,
        completed=completed,
        pending=pending,
        average=average,
        today=date.today()
    )


@app.post("/assignments/add")
def add_assignment():
    title = request.form.get("title", "").strip()
    subject = request.form.get("subject", "").strip()
    deadline_raw = request.form.get("deadline", "").strip()
    if not title or not subject:
        flash("Please enter both an assignment title and subject.", "error")
        return redirect(url_for("index"))
    deadline = date.fromisoformat(deadline_raw) if deadline_raw else None
    db.session.add(Assignment(title=title, subject=subject, deadline=deadline))
    db.session.commit()
    flash("Assignment added.", "success")
    return redirect(url_for("index"))


@app.post("/assignments/<int:assignment_id>/status")
def update_status(assignment_id):
    assignment = db.get_or_404(Assignment, assignment_id)
    assignment.status = "Completed" if assignment.status == "Pending" else "Pending"
    db.session.commit()
    flash("Assignment status updated.", "success")
    return redirect(url_for("index"))


@app.post("/assignments/<int:assignment_id>/delete")
def delete_assignment(assignment_id):
    assignment = db.get_or_404(Assignment, assignment_id)
    db.session.delete(assignment)
    db.session.commit()
    flash("Assignment deleted.", "success")
    return redirect(url_for("index"))


@app.post("/assessments/add")
def add_assessment():
    subject = request.form.get("subject", "").strip()
    name = request.form.get("assessment_name", "").strip()
    try:
        obtained = float(request.form.get("marks_obtained", ""))
        maximum = float(request.form.get("maximum_marks", ""))
    except ValueError:
        flash("Enter valid numbers for marks.", "error")
        return redirect(url_for("index"))

    if not subject or not name:
        flash("Please enter a subject and assessment name.", "error")
    elif maximum <= 0 or obtained < 0 or obtained > maximum:
        flash("Marks must be between 0 and the maximum marks, and maximum marks must be greater than 0.", "error")
    else:
        db.session.add(Assessment(
            subject=subject,
            assessment_name=name,
            marks_obtained=obtained,
            maximum_marks=maximum
        ))
        db.session.commit()
        flash("Assessment saved and percentage calculated.", "success")
    return redirect(url_for("index"))


@app.post("/assessments/<int:assessment_id>/delete")
def delete_assessment(assessment_id):
    assessment = db.get_or_404(Assessment, assessment_id)
    db.session.delete(assessment)
    db.session.commit()
    flash("Assessment deleted.", "success")
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)
