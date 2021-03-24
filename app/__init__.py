from flask import Flask
from config import Config
import datetime
import db_stg, downloader

def setup_app(app):
	stg = db_stg.Stg()
	stg.clean()
	downloader.Downloader.run_next_queued()

app = Flask(__name__)
app.config.from_object(Config)
app.start_time = datetime.datetime.utcnow()
setup_app(app)

from app import routes
