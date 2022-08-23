from flask import (
    Flask,
    request,
    flash,
    url_for,
    redirect,
    render_template,
    session,
    jsonify,
)
from flask_session import Session
from flask_qrcode import QRcode
from flask_sqlalchemy import SQLAlchemy
import slack
from sqlalchemy.dialects.mysql import FLOAT
from sqlalchemy import Enum
import os
from dotenv import load_dotenv
import json
import enum
from typing import List, Set, Dict, Tuple, Optional
from datetime import datetime, timedelta
import math
from auto.slack_bot import SlackWrapper
import random

load_dotenv()

with open("config.json", "r") as json_file:
    config = json.load(json_file)

base_url = config["base_url"]

slack_app = SlackWrapper(os.getenv("SLACK_KEY"))

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DB_URL")
app.config["SECRET_KEY"] = "the random string"
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)
QRcode(app)

db = SQLAlchemy(app)


class Students(db.Model):
    id = db.Column("student_id", db.Integer, primary_key=True)
    username = db.Column(db.String(20))
    school_id = db.Column(db.Integer)
    is_admin = db.Column(db.Boolean)
    cur_location = db.Column(db.String(50), nullable=True)
    last_logged_attendance_time = db.Column(db.DateTime(), nullable=True)
    hours_logged = db.Column(db.Integer)
    checked_in = db.Column(db.Boolean)

    def __init__(
        self,
        username: str,
        school_id: int,
        is_admin: bool,
        cur_location: Optional[str] = None,
        last_logged_attendance_time: Optional[datetime] = datetime.now(),
        hours_logged: Optional[int] = 0,
        checked_in: Optional[bool] = False,
    ):
        """
        Initialize a student object with their username, current_location (None on initialization), the last time their attendance was logged at any location (none on init),
        total number of hours logged (0 on init).

        @param username: Unique username of a student.
        @param school_id: Unique school id of a student.
        @param is_admin: Boolean to tell backend if the student should be given admin permissions or not.
        @param cur_location: Name of the build space/designated workspace location of a student if the student is checked in.
        @param last_logged_attendance_time: Last time a student checked in/out of a location.
        @param hours_logged: Total number of attendance hours logged.
        """
        self.username = username
        self.school_id = school_id
        self.is_admin = is_admin
        if cur_location:
            self.cur_location = cur_location
        else:
            self.cur_location = None
        self.last_logged_attendance_time = last_logged_attendance_time
        self.hours_logged = hours_logged
        self.checked_in = checked_in


class QRcode(db.Model):
    id = db.Column("qrcode_id", db.Integer, primary_key=True)
    location = db.Column(db.String(50))
    expr_date = db.Column(db.DateTime(), nullable=True)
    range_of_qrcode = db.Column(db.Integer)
    uses = db.Column(db.Integer)

    def __init__(
        self,
        location: str,
        expr_date: int,
        range_of_qrcode: Optional[int] = 300,
    ):
        cur_time = datetime.now()
        cur_time = cur_time - timedelta(microseconds=cur_time.microsecond)
        date_obj = datetime.strptime(str(expr_date), "%H")
        delta = timedelta(hours=date_obj.hour)

        self.location = location
        if expr_date != 0:
            self.expr_date = cur_time + delta
        self.range_of_qrcode = range_of_qrcode
        self.uses = 0


class Location(db.Model):
    id = db.Column("loc_id", db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    latitude = db.Column(FLOAT(precision=32, scale=10))
    longitude = db.Column(FLOAT(precision=32, scale=10))
    last_edited_by = db.Column(db.String(50))
    last_edited_on = db.Column(db.DateTime(), nullable=True)
    created_on = db.Column(db.DateTime(), nullable=True)

    def __init__(
        self,
        name: str,
        latitude: float,
        longitude: float,
        created_by: str,
    ):
        self.name = name
        self.latitude = latitude
        self.longitude = longitude
        self.last_edited_by = created_by
        created_on = datetime.now()
        self.created_on = created_on - timedelta(microseconds=created_on.microsecond)
        last_edited_on = datetime.now()
        self.last_edited_on = last_edited_on - timedelta(
            microseconds=last_edited_on.microsecond
        )


class AttendanceLog(db.Model):
    id = db.Column("log_id", db.Integer, primary_key=True)
    log_time = db.Column(db.DateTime())
    location = db.Column(db.String(50))
    attendee = db.Column(db.String(50))

    def __init__(
        self, name: str, location: str, log_time: Optional[datetime] = datetime.now()
    ):
        self.log_time = log_time
        self.attendee = name
        self.location = location


def set_base_param():
    data = {
        "cdn": [
            "https://cdnjs.cloudflare.com/ajax/libs/d3/7.6.1/d3.min.js",
            "https://unpkg.com/flowbite@1.5.2/dist/datepicker.js",
            "https://unpkg.com/flowbite@1.5.2/dist/flowbite.js",
            "https://ajax.googleapis.com/ajax/libs/jquery/3.5.1/jquery.min.js",
        ],
        "name": "",
        "isLoggedIn": False,
        "isAdmin": False,
    }
    try:
        data["name"] = session["user"]
    except:
        data["name"] = ""

    try:
        data["isLoggedIn"] = session["user"] != None
    except:
        data["isLoggedIn"] = False

    try:
        data["isAdmin"] = session["is_admin"]
    except:
        data["isAdmin"] = False

    return data


@app.route("/")
def homepage():
    if "isLoggedIn" in session and session["isLoggedIn"]:
        students = Students.query.all()
        locations = set()
        active_students = set()
        for student in students:
            if student.checked_in:
                active_students.add(student)
                locations.add(
                    Location.query.filter_by(name=student.cur_location).first()
                )
        return render_template(
            "index.html",
            title="Home",
            base=set_base_param(),
            flash_color="text-white",
            locations=locations,
            active_students=active_students,
        )
    return redirect(url_for("login"))


@app.route("/generate", methods=["GET", "POST"])
def generate():
    if "isLoggedIn" in session and session["isLoggedIn"]:
        if session["is_admin"]:
            if request.method == "POST":
                if (
                    not request.form["location"]
                    or not request.form["exprdate"]
                    or not request.form["range"]
                ):
                    flash("Please fill out all fields.")
                    return render_template(
                        "generate.html",
                        title="Generate QR Code",
                        locations=Location.query.all(),
                        url="Failed to generate QRcode",
                        flash_color="text-red-500",
                        base=set_base_param(),
                    )
                else:
                    error_catch = False
                    location = request.form["location"]
                    exprdate = int(request.form["exprdate"])
                    if location == "Online Meeting":
                        qrcode_range = 100000000
                    else:
                        qrcode_range = request.form["range"]
                    try:
                        qrcode_range = int(qrcode_range)
                        if qrcode_range < 300:
                            flash("Range is less than 300 ft.")
                            error_catch = True
                    except ValueError:
                        flash("Range is not a number.")
                        error_catch = True

                    if error_catch:
                        return render_template(
                            "generate.html",
                            title="Generate QR Code",
                            locations=Location.query.all(),
                            url="Failed to generate QRcode",
                            flash_color="text-red-500",
                            base=set_base_param(),
                        )

                    qrcode = QRcode(location, exprdate, qrcode_range)
                    db.session.flush()
                    db.session.add(qrcode)
                    db.session.commit()

                    fields = {
                        "encoded": f"https://{base_url}/attendance?id={qrcode.id}&loc={location}"
                    }
                    flash("QRcode successfully created.")
                    return render_template(
                        "generate.html",
                        title="Generate QR Code",
                        locations=Location.query.all(),
                        url=fields["encoded"],
                        flash_color="text-green-500",
                        base=set_base_param(),
                        **fields,
                    )

            else:
                return render_template(
                    "generate.html",
                    title="Generate QR Code",
                    locations=Location.query.all(),
                    base=set_base_param(),
                )
        return redirect(url_for("error"))
    return redirect(url_for("login"))


@app.route("/logout", methods=["GET"])
def logout():
    session["user"] = None
    session["isLoggedIn"] = False
    session["is_admin"] = False
    return redirect(url_for("homepage"))


@app.route("/login", methods=["GET", "POST"])
def login():
    return render_template("login.html", title="Home", base=set_base_param())


@app.route("/process_login", methods=["POST"])
def process_login():
    login_info = request.get_json()

    if login_info[0]["action"] == "init":
        if not login_info[1]["username"] or not login_info[2]["password"]:
            return jsonify({"action": "Enter all info"})
        else:
            name = login_info[1]["username"]
            student = Students.query.filter(Students.username.contains(name)).first()
            if student is not None:
                if str(student.school_id) == login_info[2]["password"]:
                    if name == "root":
                        session["user"] = student.username
                        session["isLoggedIn"] = True
                        session["is_admin"] = student.is_admin
                        return jsonify({"action": "logged"})

                    else:
                        print(student.username)
                        session["verification_number"] = random.randrange(
                            100000, 999999
                        )
                        slack_app.send_verification_message(
                            student.username.split(" ")[0],
                            student.username.split(" ")[1],
                            session["verification_number"],
                        )
                        return jsonify({"action": "verify"})
                else:
                    return jsonify({"action": "Incorrect username or password"})
            else:
                return jsonify({"action": "Incorrect username or password"})

    elif login_info[0]["action"] == "verification":
        name = login_info[2]["username"]
        student = Students.query.filter(Students.username.contains(name)).first()

        if login_info[1]["code"] == str(session["verification_number"]):
            session["user"] = student.username
            session["isLoggedIn"] = True
            session["is_admin"] = student.is_admin
            return jsonify({"action": "logged"})
        else:
            session["user"] = None
            return jsonify({"action": "Incorrect verification number"})


@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if "isLoggedIn" in session and session["isLoggedIn"]:
        flash_color = "text-green-500"
        if request.method == "POST":
            if "student-add" in request.form:
                if not request.form["username"] or not request.form["studentid"]:
                    flash("Please enter all the fields")
                    flash_color = "text-red-500"
                else:
                    try:
                        is_admin = (
                            request.form["student_type"] == "admin"
                            or request.form["student_type"] == "root"
                        )
                    except KeyError:
                        is_admin = False

                    student_name = request.form["username"]
                    student_id = request.form["studentid"]
                    db.session.flush()
                    student = Students(student_name, student_id, is_admin)

                    db.session.add(student)
                    db.session.commit()

                    flash(f"{student_name} was successfully added")
                    flash_color = "text-green-500"

                    return redirect(url_for("dashboard"))
            if "location-add" in request.form:
                error_catch = False
                if (
                    not request.form["location_name"]
                    or not request.form["lat"]
                    or not request.form["long"]
                ):
                    flash("Please enter all location fields")
                    flash_color = "text-red-500"
                else:
                    name = request.form["location_name"]
                    try:
                        latitude = float(request.form["lat"])
                        longitude = float(request.form["long"])
                    except ValueError:
                        flash("Latitude/Longitude needs to be a number")
                        flash_color = "text-red-500"
                        error_catch = True

                    if Location.query.filter_by(name=name).first() is not None and not (
                        error_catch
                    ):
                        flash("Location already exists")
                        flash_color = "text-red-500"
                        error_catch = True
                    else:
                        if not (error_catch):
                            db.session.flush()
                            new_loc = Location(
                                name, latitude, longitude, session["user"]
                            )

                            db.session.add(new_loc)
                            db.session.commit()

                            flash(f"{name} was successfully added as a location")
                            flash_color = "text-green-500"
                            return redirect(url_for("dashboard"))
        if Students.query.filter_by(username=session["user"]).first().is_admin == True:
            return render_template(
                "dashboard.html",
                title="Dashboard",
                flash_color=flash_color,
                base=set_base_param(),
                students=Students.query.all(),
                locations=Location.query.all(),
                active_students=Students.query.filter_by(checked_in=True),
            )
    return redirect(url_for("error"))


@app.route("/add_student", methods=["POST"])
def add_student():
    if "isLoggedIn" in session and session["isLoggedIn"]:
        if session["is_admin"]:
            db.session.flush()
            student_data = request.get_json()

            student = Students(
                username=student_data[0]["username"],
                school_id=student_data[1]["school_id"],
                is_admin=(student_data[2]["type"] != "student"),
            )

            db.session.add(student)

            db.session.commit()


@app.route("/process_student_change", methods=["POST", "GET"])
def process_student_change():
    if "isLoggedIn" in session and session["isLoggedIn"]:
        if session["is_admin"]:
            if request.method == "POST":
                db.session.flush()
                student_data = request.get_json()

                student_edit = Students.query.filter_by(
                    id=student_data[0]["id"]
                ).first()
                student_edit.username = student_data[1]["username"]
                student_edit.school_id = student_data[2]["school_id"]

                if student_data[3]["is_admin"] == "student":
                    student_edit.is_admin = False
                else:
                    student_edit.is_admin = True

                db.session.commit()

                return jsonify({"action_code": "200"})
    else:
        return redirect(url_for("error"))


@app.route("/process_location_change", methods=["POST"])
def process_location_change():
    if "isLoggedIn" in session and session["isLoggedIn"]:
        if request.method == "POST":
            db.session.flush()
            location_data = request.get_json()

            location_edit = Location.query.filter_by(id=location_data[0]["id"]).first()
            location_edit.name = location_data[1]["name"]
            location_edit.latitude = float(location_data[2]["lat"])
            location_edit.longitude = float(location_data[3]["long"])
            location_edit.last_edited_on = datetime.fromtimestamp(
                int(location_data[4]["current_time"])
            )
            location_edit.last_edited_by = session["user"]

            db.session.commit()

            return jsonify({"action_code": "200"})
    else:
        return redirect(url_for("error"))


@app.route("/error")
def error():
    return render_template(
        "403.html", title="403 - Access Denied", base=set_base_param()
    )


@app.errorhandler(404)
def page_not_found(e):
    # note that we set the 404 status explicitly
    return render_template(
        "404.html", title="404 - Page Not Found", base=set_base_param()
    )


@app.errorhandler(500)
def page_not_found(e):
    # note that we set the 404 status explicitly
    return render_template(
        "500.html", title="500 - Internal Server Error", base=set_base_param()
    )


@app.route("/add_attendance", methods=["POST"])
def process_attendance():
    if "isLoggedIn" in session and session["isLoggedIn"]:
        flash_color = "text-white"
        student = Students.query.filter_by(username=session["user"]).first()
        if student != None:
            check_in_button_text = "Check Out" if student.checked_in else "Check In"
        data = request.get_json()
        id = data["id"]
        location_name = data["loc"]
        coords = data["location"]
        if id is not None and location_name is not None:
            qrcode = QRcode.query.filter_by(id=id, location=location_name).first()
            if qrcode != None:
                qrcode.uses += 1
            else:
                return jsonify({"action_code": "201"})

            if qrcode.expr_date != None and datetime.now() > qrcode.expr_date:
                return jsonify({"action_code": "205"})

            student = Students.query.filter_by(username=session["user"]).first()
            if student != None:
                student.checked_in = not (student.checked_in)
            else:
                return jsonify({"action_code": "202"})

            location = Location.query.filter_by(name=location_name).first()
            if location != None:
                if student.checked_in:
                    student.cur_location = location_name
                else:
                    student.cur_location = None
                lat_1, lng_1, lat_2, lng_2 = map(
                    math.radians,
                    [
                        location.latitude,
                        location.longitude,
                        coords["lat"],
                        coords["lng"],
                    ],
                )
                dist = get_distance(lat_1, lng_1, lat_2, lng_2)
            else:
                return jsonify({"action_code": "203"})

            if dist <= qrcode.range_of_qrcode:
                student.last_logged_attendance_time = datetime.now()
                db.session.flush()
                log = AttendanceLog(session["user"], location_name)
                db.session.add(log)

                db.session.commit()
            else:
                return jsonify({"action_code": "204"})

            return jsonify({"action_code": "200"})
    return redirect(url_for("error"))


@app.route("/attendance", methods=["GET", "POST"])
def log():
    if "isLoggedIn" in session and session["isLoggedIn"]:
        if request.method == "GET":
            id = request.args.get("id")
            location = request.args.get("loc")
            if id is not None and location is not None:
                student = Students.query.filter_by(username=session["user"]).first()
                if student != None:
                    check_in_button_text = (
                        "Check Out" if student.checked_in else "Check In"
                    )
                    return render_template(
                        "log.html",
                        title="Attendance Logging",
                        base=set_base_param(),
                        checked_in=check_in_button_text,
                    )
        return redirect(url_for("error"))
    return redirect(url_for("login"))


@app.route("/checkout_student", methods=["POST"])
def checkout():
    if "isLoggedIn" in session and session["isLoggedIn"]:
        if session["is_admin"]:
            db.session.flush()

            student_data = request.get_json()
            student = Students.query.filter_by(id=student_data[0]["id"]).first()

            student.checked_in = False
            student.cur_location = None
            student.last_logged_attendance_time = datetime.fromtimestamp(
                int(student_data[1]["time"])
            )

            db.session.commit()

            return jsonify({"action_code": "200"})
        return redirect(url_for("error"))
    return redirect(url_for("login"))


@app.route("/delete_student", methods=["POST"])
def delete_student():
    if "isLoggedIn" in session and session["isLoggedIn"]:
        if request.method == "POST":
            db.session.flush()
            student_data = request.get_json()

            student = Students.query.filter_by(id=student_data[0]["id"]).first()
            db.session.delete(student)

            db.session.commit()

            return jsonify({"action_code": "200"})
    else:
        return redirect(url_for("error"))


@app.route("/delete_location", methods=["POST"])
def delete_location():
    if "isLoggedIn" in session and session["isLoggedIn"]:
        if request.method == "POST":
            db.session.flush()
            location_data = request.get_json()

            location = Location.query.filter_by(id=location_data[0]["id"]).first()
            db.session.delete(location)

            db.session.commit()

            return jsonify({"action_code": "200"})
    else:
        return redirect(url_for("error"))


def get_distance(lat_1, lng_1, lat_2, lng_2):
    d_lat = lat_2 - lat_1
    d_lng = lng_2 - lng_1

    temp = (
        math.sin(d_lat / 2) ** 2
        + math.cos(lat_1) * math.cos(lat_2) * math.sin(d_lng / 2) ** 2
    )

    return (
        6373.0 * (2 * math.atan2(math.sqrt(temp), math.sqrt(1 - temp))) * 3280.84
    )  # converting kilometer output into feet


if __name__ == "__main__":
    db.create_all()
    if Location.query.filter(Location.name == "Online Meeting").first() == None:
        db.session.flush()
        db.session.add(Location("Online Meeting", 39, 49, "root"))
        db.session.commit()
    if Students.query.filter(Students.username == config["rootuser"]).first() == None:
        db.session.flush()
        db.session.add(Students(config["rootuser"], int(config["rootpass"]), True))
        db.session.commit()
    app.run(debug=True, host="0.0.0.0")
