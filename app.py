from flask import Flask, render_template, request
from flask_qrcode import QRcode

app = Flask(__name__)
QRcode(app)

base_url = "localhost:5000/"

@app.route("/")
def homepage():
    return render_template("index.html", title="Home", cdns=["https://cdnjs.cloudflare.com/ajax/libs/d3/7.6.1/d3.min.js"])

@app.route("/qrcode", methods=["POST"])
def qrcode():
    response = request.args.get("location")
    fields = {"encoded": f"{base_url}?loc={response}"}
    return render_template("qrcode.html", title="QRcode", **fields)


if __name__ == "__main__":
    app.run(debug=True)