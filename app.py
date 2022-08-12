from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
def homepage():
    return render_template("index.html", title="Home", cdns=["https://cdnjs.cloudflare.com/ajax/libs/d3/7.6.1/d3.min.js"])

if __name__ == "__main__":
    app.run(debug=True)