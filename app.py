from flask import Flask, request, flash, url_for, redirect, render_template, session
from flask_qrcode import QRcode
from flask_sqlalchemy import SQLAlchemy
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
        print(expr_date)
        cur_time = datetime.now()
        date_obj = datetime.strptime(str(expr_date), "%H")
        delta = timedelta(hours=date_obj.hour)

        self.location = Locations(location)
        if expr_date != 0:
            self.expr_date = cur_time + delta
        self.range_of_qrcode = range_of_qrcode
        self.uses = 0


def set_base_param():
    data = {
        "cdn": [
            "https://cdnjs.cloudflare.com/ajax/libs/d3/7.6.1/d3.min.js",
            "https://unpkg.com/flowbite@1.5.2/dist/datepicker.js",
            "https://unpkg.com/flowbite@1.5.2/dist/flowbite.js",
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

    return data


@app.route("/")
def homepage():

    return render_template("index.html", title="Home", base=set_base_param())


@app.route("/generate", methods=["GET", "POST"])
def generate():
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
                locations=config["locations"],
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
                    locations=config["locations"],
                    url="Failed to generate QRcode",
                    flash_color="text-red-500",
                    base=set_base_param(),
                )

            qrcode = QRcode(location, exprdate, qrcode_range)

            db.session.add(qrcode)
            db.session.commit()

            fields = {"encoded": f"{base_url}?id={qrcode.id}&loc={location}"}
            flash("QRcode successfully created.")
            return render_template(
                "generate.html",
                title="Generate QR Code",
                locations=config["locations"],
                url=fields["encoded"],
                flash_color="text-green-500",
                base=set_base_param() ** fields,
            )

    else:
        return render_template(
            "generate.html",
            title="Generate QR Code",
            locations=config["locations"],
            base=set_base_param(),
        )


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

            db.session.add(student)
            db.session.commit()
            flash("Record was successfully added")
            return redirect(url_for("show_all"))
    return render_template("new.html")


@app.route("/logout", methods=["GET"])
def logout():
    session["user"] = None
    session["isLoggedIn"] = False
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


if __name__ == "__main__":
    db.create_all()
    app.run(debug=True, host="0.0.0.0")
