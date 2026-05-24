from flask import Flask, redirect, url_for
from config import Config

from routes.auth      import auth_bp
from routes.dashboard import dashboard_bp
from routes.upload    import upload_bp
from routes.analysis  import analysis_bp
from routes.reports   import reports_bp
from routes.profile   import profile_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(upload_bp)
    app.register_blueprint(analysis_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(profile_bp)

    @app.route('/')
    def root():
        return redirect(url_for('auth.login'))

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5001)   # Using 5001 to avoid conflicts
