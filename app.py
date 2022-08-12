from flask import Flask, request, flash, url_for, redirect, render_template
from flask_qrcode import QRcode
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Enum
import os
from dotenv import load_dotenv
import json
import enum
from typing import List, Set, Dict, Tuple, Optional
from datetime import datetime

load_dotenv()

with open("config.json", "r") as json_file:
    config = json.load(json_file)

base_url = "localhost:5000/"

location_list = config["locations"]
location_dict = { loc : loc for loc in location_list }
Locations = enum.Enum("Locations", location_dict)

app = Flask(__name__)
QRcode(app)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DB_URL')

db = SQLAlchemy(app)

class Students(db.Model):
    id = db.Column('student_id', db.Integer, primary_key = True)
    username = db.Column(db.String(20))
    cur_location = db.Column(Enum(Locations), nullable=True)
    last_logged_attendance_time = db.Column(db.DateTime(), nullable = True)
    hours_logged = db.Column(db.Integer)

    def __init__(self, username: str, cur_location: Optional[str] = None, last_logged_attendance_time: Optional[datetime] = datetime.now(), hours_logged: int = 0):
        """
            Initialize a student object with their username, current_location (None on initialization), the last time their attendance was logged at any location (none on init), 
            total number of hours logged (0 on init).
            
            @param username: Unique username of a student.
            @param cur_location: Name of the build space/designated workspace location of a student if the student is checked in.
            @param last_logged_attendance_time: Last time a student checked in/out of a location.
            @param hours_logged: Total number of attendance hours logged.
        """
        self.username = username
        if cur_location:
            self.cur_location = Locations(cur_location)
        else:
            self.cur_location = None
        self.last_logged_attendance_time = last_logged_attendance_time
        self.hours_logged = hours_logged

@app.route("/")
def homepage():
    return render_template("index.html", title="Home", cdns=["https://cdnjs.cloudflare.com/ajax/libs/d3/7.6.1/d3.min.js"])

@app.route("/qrcode", methods=["POST"])
def qrcode():
    response = request.args.get("location")
    fields = {"encoded": f"{base_url}?loc={response}"}
    return render_template("qrcode.html", title="QRcode", **fields)

@app.route('/current_students')
def show_all():
   return render_template('show_all.html', students = Students.query.all() )

@app.route('/new', methods = ['GET', 'POST'])
def new():
   if request.method == 'POST':
      if not request.form['username']:
         flash('Please enter all the fields', 'error')
      else:
         student = Students(request.form['username'])
         
         db.session.add(student)
         db.session.commit()
         flash('Record was successfully added')
         return redirect(url_for('show_all'))
   return render_template('new.html')

if __name__ == '__main__':
   db.create_all()
   app.run(debug = True)