import os
from flask import Flask
from flask_cors import CORS

from config import Config
from database import init_db


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    CORS(app, resources={r"/api/*": {"origins": "http://localhost:5173"}})

    init_db(app)

    from routes.transactions import bp as transactions_bp
    from routes.upload import bp as upload_bp
    from routes.categories import bp as categories_bp
    from routes.salaries import bp as salaries_bp
    from routes.dashboard import bp as dashboard_bp
    from routes.accounts import bp as accounts_bp

    app.register_blueprint(transactions_bp, url_prefix="/api/transactions")
    app.register_blueprint(upload_bp, url_prefix="/api/upload")
    app.register_blueprint(categories_bp, url_prefix="/api/categories")
    app.register_blueprint(salaries_bp, url_prefix="/api/salaries")
    app.register_blueprint(dashboard_bp, url_prefix="/api/dashboard")
    app.register_blueprint(accounts_bp, url_prefix="/api/accounts")

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5000)
