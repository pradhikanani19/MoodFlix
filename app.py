import os
from flask import Flask
from extensions import db, login_manager, bcrypt
from dotenv import load_dotenv

load_dotenv()


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'moodflix-secret-2024')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///moodflix.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['TMDB_API_KEY'] = os.getenv('TMDB_API_KEY', '')
    app.config['TMDB_BASE_URL'] = 'https://api.themoviedb.org/3'
    app.config['TMDB_IMG_BASE'] = 'https://image.tmdb.org/t/p/w500'

    # Init extensions
    db.init_app(app)
    login_manager.init_app(app)
    bcrypt.init_app(app)

    # Register blueprints
    from routes.auth import auth_bp
    from routes.main import main_bp
    from routes.api import api_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')

    # Create tables
    with app.app_context():
        import models  # noqa - registers user_loader
        db.create_all()

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5000)
