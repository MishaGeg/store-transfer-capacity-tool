from flask import Flask, request, render_template, redirect, flash, url_for, session
import os


app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")

@app.route("/")
def home():
    return "Store Transfer Capacity Visibility Tool is running"




    
if __name__ == "__main__":
    app.run(debug=True)