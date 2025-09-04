from flask import Blueprint, redirect, render_template, request, url_for, flash
from flask_login import login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from peewee import IntegrityError
import os
from datetime import datetime
from config_db import User
from config import UPLOAD_DIR

bp_auth = Blueprint("auth", __name__)
# Blueprintでapiファイルを分けて管理


@bp_auth.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        password_confirm = request.form.get("password_confirm", "")

        # バリデーション
        if not name or not email or not password:
            flash("全ての項目を入力してください")
            return redirect(request.url)

        # パスワード一致確認
        if password != password_confirm:
            flash("パスワードが一致しません")
            return redirect(request.url)

        # 既存ユーザー確認
        if User.select().where(User.email == email).exists():
            flash("このメールアドレスは既に登録されています")
            return redirect(request.url)

        # アイコン画像のアップロード処理
        icon_filename = None
        uploaded_file = request.files.get("icon")
        if uploaded_file and uploaded_file.filename:
            filename = secure_filename(uploaded_file.filename)
            file_ext = os.path.splitext(filename)[1]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # iconフォルダを作成
            icon_dir = os.path.join(UPLOAD_DIR, "icon")
            os.makedirs(icon_dir, exist_ok=True)

            # 一時的にuser_idなしでファイル名を作成（後でuser_idで更新）
            # 保存する時にはまだユーザーIDが分からない...
            temp_filename = f"user_temp_{timestamp}{file_ext}"
            file_path = os.path.join(icon_dir, temp_filename)
            uploaded_file.save(file_path)
            icon_filename = temp_filename

        try:
            user = User.create(
                name=name,
                email=email,
                password_hash=generate_password_hash(password),
                icon=icon_filename,
                deleted_at=None,  # 明示的にNoneを入れないと謎の時刻が入る　なぜ？
            )

            # アイコンファイル名をuser_idを含む名前に変更
            if icon_filename:
                new_filename = f"user_{user.id}_{timestamp}{file_ext}"
                old_path = os.path.join(icon_dir, temp_filename)
                new_path = os.path.join(icon_dir, new_filename)

                try:
                    os.rename(old_path, new_path)  # ファイル名変更
                    # DBのicon値を更新
                    user.icon = new_filename
                    user.save()
                except OSError:
                    # ファイル名変更失敗時は元のテンポラリファイルを削除
                    if os.path.exists(old_path):
                        os.remove(old_path)
            flash("登録に成功しました")
            return redirect(url_for("auth.login"))

        except IntegrityError:
            flash("登録に失敗しました")
            return redirect(request.url)

    return render_template("register.html")


@bp_auth.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not email or not password:
            flash("メールアドレスとパスワードを入力してください")
            return redirect(request.url)

        user = User.select().where(User.email == email).first()
        if user is not None and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for("view.index"))

        flash("メールアドレスまたはパスワードが間違っています")
        return redirect(request.url)

    return render_template("login.html")


@bp_auth.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("view.index"))
