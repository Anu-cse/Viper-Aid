from flask import Flask, render_template

app = Flask(__name__)

# Home page
@app.route("/")
def home():
    return render_template("index.html")

# Report page
@app.route("/report")
def report():
    return render_template("report.html")

# Rescue dashboard page
@app.route("/rescue")
def rescue():
    return render_template("rescue.html")

# Fund / donation page
@app.route("/fund")
def fund():
    return render_template("fund.html")

# About page
@app.route("/about")
def about():
    return render_template("about.html")

if __name__ == "__main__":
    app.run(debug=True)
