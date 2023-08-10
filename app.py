import json
import os
import time
from functools import cache
from random import randrange

from certifi import where
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, redirect, request, session, url_for
from flask_session import Session
from googleapiclient.discovery import build
from pymongo.mongo_client import MongoClient

from auto.slack_bot import SlackWrapper

load_dotenv()

with open("config.json") as json_file:
    config = json.load(json_file)

ATTENDANCE_WEIGHTS = {"P": 1, "X": 0.75, "L": 0.75, "O": 1, "A": 0}
ATTENDANCE_SHORTHAND = {"P": "Attended", "X": "Excused", "L": "Late", "A": "Absent", "O": "Attended"}
ATTENDANCE_REQUIREMENT = 0.6  # As a percentage
SPREADSHEET_ID = "1u-GbQA4ZaARBbzUWO6t2a_7gC-GtSlHuYU2GxxO2pD8"
SHEET_NAME = "Test of Attendance Sheet"
COLOR_DIFFERENCE_TOLERANCE = 0.05

# Set up Mongo DB, Slack, the Google client that interfaces with the spreadsheet and Flask
slack_app = SlackWrapper(os.getenv("SLACK_KEY"))
service = build(
    "sheets",
    "v4",
    developerKey=os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
)

client = MongoClient(
    (
        f"mongodb+srv://swadkar1:{os.getenv('MONGODB_PASSWORD')}@falcontrack.snv7mpp.mongodb.net"
        f"/?retryWrites=true&w=majority"
    ),
    tlsCAFile=where()
)
database = client.get_database("falcon-track")

app = Flask(__name__)

# Configure the app
app.config["SECRET_KEY"] = os.getenv("FLASK_HASH")
app.config["SESSION_PERMANENT"] = True
app.config["SESSION_TYPE"] = "mongodb"
app.config["SESSION_COOKIE_SECURE"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "None"
app.config["SESSION_COOKIE_NAME"] = "falcontrack"
app.config["SESSION_MONGODB"] = client
app.config["SESSION_MONGODB_DB"] = "falcon-track"
app.config["SESSION_MONGODB_COLLECTION"] = "sessions"

base = {
    "logged_in": False,
    "is_admin": False,
    "logo": config["logo"],
    "color": config["color"]
}

# Start the session to keep the user logged in
Session(app)


# Utility functions
def _matches(l1: list, l2: list) -> bool:
    """Compares two lists containing slightly differing floats to see if they're a match."""
    return all(round(abs(value1 - value2), 4) <= COLOR_DIFFERENCE_TOLERANCE for value1, value2 in zip(l1, l2))


def get_ttl_hash(seconds=60):
    """Return the same value within `seconds` time period"""
    return round(time.time() / seconds)


def update_base_params() -> dict:
    """Updates the base parameters used by FalconTrack."""
    data = {
        "name": "",
        "logged_in": False,
        "is_admin": False,
        "logo": config["logo"],
        "color": config["color"]
    }

    try:
        data["name"] = session["user"]
    except KeyError:
        data["name"] = ""

    try:
        data["logged_in"] = session["user"] is not None
    except KeyError:
        data["logged_in"] = False

    try:
        data["is_admin"] = session["is_admin"]
    except KeyError:
        data["is_admin"] = False

    return data


@cache
def _meeting_list(ttl_hash=None) -> dict:
    """Returns a dictionary containing the meeting name along with the subteam and order in the list of meetings."""
    spreadsheet_data = service.spreadsheets().get(
        spreadsheetId=SPREADSHEET_ID,
        ranges=SHEET_NAME,
        includeGridData=True
    ).execute()
    meetings_to_subteams = {}

    for idx, value in enumerate(spreadsheet_data["sheets"][0]["data"][0]["rowData"][0]["values"][5:], start=5):
        rgb_values = [round(rgb, 4) for rgb in value["effectiveFormat"]["backgroundColor"].values()]
        subteam = next(
            subteam_name for subteam_name, colors in config["subteam_colors"].items() if _matches(colors, rgb_values)
        )

        meetings_to_subteams[value["formattedValue"]] = {
            "subteam": subteam,
            "index": idx
        }

    return meetings_to_subteams


@cache
def meeting_attendance(name: str, ttl_hash=None) -> tuple[dict, dict]:
    """Returns a dictionary containing the meeting name and whether the student mentioned was present."""
    all_meetings = _meeting_list(ttl_hash)
    spreadsheet_data = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=SHEET_NAME
    ).execute()

    student_attendance = next(row for row in spreadsheet_data["values"] if row[0].lower() == name)
    return (
        all_meetings,
        {
            meeting_name: student_attendance[idx]
            for meeting_name, meeting_info in all_meetings.items()
            if (idx := meeting_info["index"]) < len(student_attendance) and student_attendance[idx]
        }
    )


@cache
def overall_attendance(name: str, ttl_hash=None) -> tuple[dict, dict, tuple[float, float]]:
    """Calculates the attendance of a student and returns their technical and operational attendance %s."""
    all_meetings, attendance_by_meeting = meeting_attendance(name, ttl_hash)
    technical_attendance = []
    operational_attendance = []

    for meeting_name, attendance in attendance_by_meeting.items():
        if meeting_name.startswith("T"):
            technical_attendance.append(ATTENDANCE_WEIGHTS[attendance])
        elif meeting_name.startswith("O"):
            operational_attendance.append(ATTENDANCE_WEIGHTS[attendance])

    return (
        all_meetings,
        attendance_by_meeting,
        (
            sum(technical_attendance) / (len(technical_attendance) or 1),
            sum(operational_attendance) / (len(operational_attendance) or 1),
        )
    )


@app.route("/")
def home() -> str:
    base_params = update_base_params()
    all_meetings, attendance, (tech_attendance, op_attendance) = overall_attendance(base_params["name"], get_ttl_hash())

    # Filter meetings to display meetings that line up with the students' subteams
    student_info = database.get_collection("students").find_one(
        {"name": base_params["name"]}
    )
    tech_subteam, op_subteam = (student_info["tech_subteam"], student_info["op_subteam"])
    filtered_meetings = {
        meeting_name: meeting_info
        for meeting_name, meeting_info in all_meetings.items()
        if (
            meeting_info["subteam"] in {tech_subteam, op_subteam, "Whole Team"}
            or attendance.get(meeting_name, "") == "P"
        )
    }

    # Create a list containing the past meetings the student should have attended
    past_meetings = [
        {
            "name": meeting_name.replace("T -", "").replace("O -", "").strip(),
            "subteam": meeting_info["subteam"],
            "subteam_color": config["subteam_colors_in_hex"][meeting_info["subteam"]],
            "attended": attendance.get(meeting_name, "") == "P",
            "attendance_written": ATTENDANCE_SHORTHAND[attendance.get(meeting_name, "A")]
        }
        for meeting_name, meeting_info in list(filtered_meetings.items())[-4:][::-1]   # Grab last 5 meetings
    ]

    return render_template(
        "index.html",
        title="Home",
        base=update_base_params(),
        past_meetings=past_meetings,
        tech_attendance=round(tech_attendance, 3),
        op_attendance=round(op_attendance, 3),
        attendance_requirement=ATTENDANCE_REQUIREMENT,
    )


@app.route("/login")
def login() -> str:
    return render_template(
        "login.html",
        title="Login",
        base=update_base_params()
    )


@app.route("/process_login", methods=["POST"])
def process_login():
    login_info = request.get_json()

    if login_info[0]["action"] == "init":
        if not login_info[1]["username"]:
            return jsonify({"action": "Enter your username"})
        else:
            name = login_info[1]["username"]
            student = next(student for student in database.students.find() if name in student["name"])

            if student is not None:
                session["verification_number"] = randrange(
                    100000, 999999
                )
                slack_app.send_verification_message(
                    *student["name"].split(),
                    session["verification_number"],
                )
                return jsonify({"action": "verify"})
            else:
                return jsonify({"action": "Incorrect username"})
    elif login_info[0]["action"] == "verification":
        name = login_info[2]["username"].lower()
        student = next(student for student in database.students.find() if name in student["name"])

        if login_info[1]["code"] == str(session["verification_number"]):
            session["user"] = student["name"]
            session["logged_in"] = True
            session["is_admin"] = student["is_admin"]
            return jsonify({"action": "logged"})
        else:
            session["user"] = None
            return jsonify({"action": "Incorrect verification number"})


@app.route("/logout")
def logout():
    session["user"] = None
    session["isLoggedIn"] = False
    session["is_admin"] = False
    return redirect(url_for("home"))


if __name__ == '__main__':
    app.run(debug=True)
