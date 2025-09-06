from flask import Flask, redirect, url_for, send_from_directory
from flask_login import LoginManager
from config import db, SECRET_KEY, UPLOAD_DIR
from config_db import User
from auth import bp_auth
from view import bp_view

login_manager = LoginManager()


def create_app():
    # Flaskの起動
    app = Flask(__name__)
    # db接続
    db.connect()
    # Secret keyの設定
    app.config["SECRET_KEY"] = SECRET_KEY
    # ログイン管理機能の準備
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.get_by_id(user_id)

    @login_manager.unauthorized_handler
    def unauthorized_handler():
        return redirect(url_for("login"))

    # 画像ファイル配信用ルート
    @app.route("/uploads/<path:filename>")
    def uploaded_file(filename):
        return send_from_directory(UPLOAD_DIR, filename)

    # Blueprintの設定（ルーティングを分かりやすく）
    # api_bp = Blueprint("api", __name__, url_prefix="/api")
    app.register_blueprint(bp_auth)
    app.register_blueprint(bp_view)
    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="127.0.0.1", port=8000, debug=True)

app = create_app()
