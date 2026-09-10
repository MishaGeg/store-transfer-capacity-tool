from flask import Flask
from dotenv import load_dotenv
import os
from models import db
from flask_migrate import Migrate
from flask_cors import CORS
from transfers import transfers_bp
from store_capacities import capacities_bp
from stock_snapshot_import import snapshot_import_bp
load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")

app.register_blueprint(transfers_bp)
app.register_blueprint(capacities_bp)
app.register_blueprint(snapshot_import_bp)

CORS(app)

db.init_app(app)
migrate = Migrate(app, db)

@app.route("/")
def home():
    return "HI"


if __name__ == "__main__":
    app.run(debug=True)