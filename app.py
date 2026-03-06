import os
import json
from datetime import datetime
from flask import Flask, render_template, request, redirect, session, send_from_directory
from pymongo import MongoClient
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "any_random_secret_key"

# ---------------- MongoDB setup ----------------
client = MongoClient("mongodb://localhost:27017/")
db = client.medtrack
appointments = db.appointments


# ---------------- Helper function ----------------
def ensure_json_file(filename):
    if not os.path.exists(filename):
        with open(filename, "w") as f:
            json.dump([], f)


# ---------------- Home ----------------
@app.route("/")
def home():
    return render_template("login_choice.html")


# ---------------- Signup ----------------
@app.route("/signup", methods=["GET", "POST"])
def signup():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        ensure_json_file("patients.json")

        with open("patients.json", "r") as f:
            patients = json.load(f)

        if any(p["email"] == email for p in patients):
            return "Email already registered"

        patients.append({
            "name": name,
            "email": email,
            "password": password
        })

        with open("patients.json", "w") as f:
            json.dump(patients, f)

        return redirect("/login")

    return render_template("signup.html")


# ---------------- Patient Login ----------------
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        ensure_json_file("patients.json")

        with open("patients.json", "r") as f:
            patients = json.load(f)

        user = next((p for p in patients if p["email"] == email), None)

        if user:

            if user["password"] == password:

                session["email"] = user["email"]
                session["name"] = user["name"]

                return redirect("/dashboard")

            else:
                return "Incorrect password"

        else:
            return "Email not found"

    return render_template("login.html")


# ---------------- Patient Dashboard ----------------
@app.route("/dashboard")
def dashboard():

    if "email" not in session:
        return redirect("/login")

    name = session["name"]

    # get appointments of this patient
    data = appointments.find({"patient": name})

    return render_template("dashboard.html", name=name, data=data)


# ---------------- Book Appointment ----------------
@app.route("/book", methods=["GET", "POST"])
def book():

    if "email" not in session:
        return redirect("/login")

    if request.method == "POST":

        doctor = request.form["doctor"]
        date = request.form["date"]
        problem = request.form["problem"]

        appointments.insert_one({
            "patient": session["name"],
            "doctor": doctor,
            "date": date,
            "problem": problem,
            "diagnosis": "Pending"
        })

        return redirect("/dashboard")

    return render_template("book.html")


# ---------------- Doctor Login ----------------
@app.route("/doctor_login", methods=["GET", "POST"])
def doctor_login():

    doctors = {
        "Dr.Asha": "asha123",
        "Dr.Ravi": "ravi123",
        "Dr.Meena": "meena123"
    }

    if request.method == "POST":

        doctor = request.form["doctor"]
        password = request.form["password"]

        if doctor in doctors and doctors[doctor] == password:
            session["doctor"] = doctor
            return redirect("/doctor_dashboard")

        else:
            return "Invalid Doctor or Password"

    return render_template("doctor_login.html")


# ---------------- Doctor Dashboard ----------------
@app.route("/doctor_dashboard")
def doctor_dashboard():

    if "doctor" not in session:
        return redirect("/doctor_login")

    doctor = session["doctor"]

    data = appointments.find({"doctor": doctor})

    return render_template("doctor_dashboard.html", data=data, doctor=doctor)


# ---------------- Update Diagnosis ----------------
@app.route("/update_diagnosis", methods=["POST"])
def update_diagnosis():

    patient = request.form["patient"]
    diagnosis = request.form["diagnosis"]

    appointments.update_one(
        {"patient": patient, "diagnosis": "Pending"},
        {"$set": {"diagnosis": diagnosis}}
    )

    return redirect("/doctor_dashboard")


# ---------------- Upload Medical Report ----------------
@app.route("/upload_report", methods=["GET", "POST"])
def upload_report():

    if "email" not in session:
        return redirect("/login")

    if request.method == "POST":

        if "report" not in request.files:
            return "No file selected"

        file = request.files["report"]

        if file.filename == "":
            return "No file selected"

        if not os.path.exists("uploads"):
            os.makedirs("uploads")

        filename = secure_filename(session["email"] + "_" + file.filename)
        path = os.path.join("uploads", filename)

        file.save(path)

        ensure_json_file("reports.json")

        with open("reports.json", "r") as f:
            data = json.load(f)

        data.append({
            "email": session["email"],
            "file": filename,
            "date": str(datetime.now())
        })

        with open("reports.json", "w") as f:
            json.dump(data, f)

        return redirect("/view_reports")

    return render_template("upload_report.html")


# ---------------- View Patient Reports ----------------
@app.route("/view_reports")
def view_reports():

    if "email" not in session:
        return redirect("/login")

    ensure_json_file("reports.json")

    with open("reports.json", "r") as f:
        data = json.load(f)

    user_reports = [r for r in data if r["email"] == session["email"]]

    return render_template("view_reports.html", reports=user_reports)


# ---------------- Doctor View Reports ----------------
@app.route("/doctor_view_reports")
def doctor_view_reports():

    if "doctor" not in session:
        return redirect("/doctor_login")

    ensure_json_file("reports.json")

    with open("reports.json", "r") as f:
        data = json.load(f)

    return render_template("view_reports_doctor.html", reports=data)


# ---------------- Open Uploaded File ----------------
@app.route("/uploads/<filename>")
def uploaded_file(filename):

    return send_from_directory("uploads", filename)


# ---------------- Logout ----------------
@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


# ---------------- Run App ----------------
if __name__ == "__main__":

    ensure_json_file("patients.json")
    ensure_json_file("reports.json")

    if not os.path.exists("uploads"):
        os.makedirs("uploads")

    app.run(debug=True)