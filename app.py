from flask import Flask, render_template
from dotenv import load_dotenv
import os
from models import db
from flask_migrate import Migrate
from flask_cors import CORS
from transfers import transfers_bp
from capacities import capacities_bp
from stock_snapshot import stock_snapshot_bp
from stores import stores_bp
load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
db.init_app(app)
migrate = Migrate(app, db)
CORS(app)

app.register_blueprint(transfers_bp)
app.register_blueprint(capacities_bp)
app.register_blueprint(stock_snapshot_bp)
app.register_blueprint(stores_bp)



@app.route("/")
def home():
    return "HI"

@app.route("/transfers-page")
def transfers_page():
    return render_template("transfers.html")


if __name__ == "__main__":
    app.run(debug=True)