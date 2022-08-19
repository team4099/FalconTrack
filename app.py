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
from flask_qrcode import QRcode
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.mysql import FLOAT
from sqlalchemy import Enum
import os
from dotenv import load_dotenv
import json
import enum
from typing import List, Set, Dict, Tuple, Optional
from datetime import datetime, timedelta
import json

load_dotenv()

with open("config.json", "r") as json_file:
    config = json.load(json_file)

base_url = config["base_url"]

location_list = config["locations"]
location_dict = {loc: loc for loc in location_list}
Locations = enum.Enum("Locations", location_dict)

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DB_URL")
app.config["SECRET_KEY"] = "the random string"
app.permanent_session_lifetime = timedelta(days=365)


QRcode(app)

db = SQLAlchemy(app)


class Students(db.Model):
    id = db.Column("student_id", db.Integer, primary_key=True)
    username = db.Column(db.String(20))
    school_id = db.Column(db.Integer)
    is_admin = db.Column(db.Boolean)
    cur_location = db.Column(Enum(Locations), nullable=True)
    last_logged_attendance_time = db.Column(db.DateTime(), nullable=True)
    hours_logged = db.Column(db.Integer)

    def __init__(
        self,
        username: str,
        school_id: int,
        is_admin: bool,
        cur_location: Optional[str] = None,
        last_logged_attendance_time: Optional[datetime] = datetime.now(),
        hours_logged: Optional[int] = 0,
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
            self.cur_location = Locations(cur_location)
        else:
            self.cur_location = None
        self.last_logged_attendance_time = last_logged_attendance_time
        self.hours_logged = hours_logged


class QRcode(db.Model):
    id = db.Column("qrcode_id", db.Integer, primary_key=True)
    location = db.Column(Enum(Locations))
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
        cur_time = cur_time - datetime.timedelta(microseconds=cur_time.microsecond)
        date_obj = datetime.strptime(str(expr_date), "%H")
        delta = timedelta(hours=date_obj.hour)

        self.location = Locations(location)
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

    def __init__(self, name: str, latitude: float, longitude: float, created_by: str):
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

    return render_template(
        "index.html", title="Home", base=set_base_param(), flash_color="text-white"
    )


@app.route("/generate", methods=["GET", "POST"])
def generate():
    if session["isLoggedIn"]:
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

                fields = {"encoded": f"{base_url}?id={qrcode.id}&loc={location}"}
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
    else:
        return redirect(url_for("error"))


@app.route("/current_students")
def show_all():
    return render_template("show_all.html", students=Students.query.all())


@app.route("/new", methods=["GET", "POST"])
def new():
    if request.method == "POST":
        if not request.form["username"] or not request.form["studentid"]:
            flash("Please enter all the fields")
        else:
            try:
                is_admin = request.form["is_admin"] == "on"
            except KeyError:
                is_admin = False
            student = Students(
                request.form["username"], request.form["studentid"], is_admin
            )
            db.session.flush()
            db.session.add(student)
            db.session.commit()
            flash("Record was successfully added")
            return redirect(url_for("show_all"))
    return render_template("new.html")


@app.route("/logout", methods=["GET"])
def logout():
    session["user"] = None
    session["isLoggedIn"] = False
    session["is_admin"] = False
    return redirect(url_for("homepage"))


@app.route("/login", methods=["GET", "POST"])
def login():
    flash_color = "text-white"
    if request.method == "POST":
        if not request.form["username"] or not request.form["password"]:
            flash("Please enter all the fields")
            flash_color = "text-red-500"
        else:
            name = request.form["username"]
            student = Students.query.filter(Students.username == name).first()
            if student is not None:
                if str(student.school_id) == request.form["password"]:
                    flash_color = "text-green-500"
                    session["user"] = name
                    session["isLoggedIn"] = True
                    session["is_admin"] = student.is_admin
                    return redirect(url_for("homepage"))
                else:
                    flash("Incorrect password.")
                    flash_color = "text-red-500"
            else:
                flash("Student does not exist.")
                flash_color = "text-red-500"

    return render_template(
        "login.html", title="Home", flash_color=flash_color, base=set_base_param()
    )


@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if session["isLoggedIn"]:
        flash_color = "text-white"
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

        if Students.query.filter_by(username=session["user"]).first().is_admin == True:
            return render_template(
                "dashboard.html",
                title="Dashboard",
                flash_color=flash_color,
                base=set_base_param(),
                students=Students.query.all(),
                locations=Location.query.all(),
            )
    return redirect(url_for("error"))


@app.route("/process_student_change", methods=["POST", "GET"])
def process_student_change():
    if session["isLoggedIn"]:
        if request.method == "POST":
            db.session.flush()
            student_data = request.get_json()

            student_edit = Students.query.filter_by(id=student_data[0]["id"]).first()
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
    if session["isLoggedIn"]:
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
        "access_denied.html", title="Access Denied", base=set_base_param()
    )


@app.errorhandler(404)
def page_not_found(e):
    # note that we set the 404 status explicitly
    return render_template(
        "404.html", title="404 - Page Not Found", base=set_base_param()
    )


@app.route("/postmethod", methods=["POST"])
def postmethod():
    data = request.get_json()
    print(data)
    return jsonify(data)


@app.route("/attendance", methods=["GET", "POST"])
def log():
    if session["isLoggedIn"]:
        if request.method == "GET":
            return render_template(
                "log.html", title="Attendance Logging", base=set_base_param()
            )
        elif request.method == "POST":
            flash_color = "text-white"
            data = request.get_json()
            id = data["id"]
            location = data["loc"]
            if id is None or location is None:
                flash_color = "text-red-500"
                flash("Error in processing location logging.")
            else:
                flash_color = "text-green-500"
                flash("Data successfully obtained.")
                data = request.get_json()
                print(data)

        return render_template(
            "index.html", title="Home", base=set_base_param(), flash_color=flash_color
        )
    return redirect(url_for("error"))


if __name__ == "__main__":
    db.create_all()
    if Students.query.filter(Students.username == config["rootuser"]).first() == None:
        db.session.flush()
        db.session.add(Students(config["rootuser"], int(config["rootpass"]), True))
        db.session.commit()
    app.run(debug=True, host="0.0.0.0")
