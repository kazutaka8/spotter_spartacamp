from flask import Blueprint, redirect, render_template, request, url_for, flash
from flask_login import login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from peewee import IntegrityError
from config_db import (
    User,
    # Spot,
    # SpotImage,
    # Tag,
    # SpotTag,
    # SpotGood,
    # SpotBad,
    # SpotSolved,
    # Group,
    # GroupSpot,
    # GroupTag,
    # GroupGood,
    # GroupBad,
    # Reply,
    # ReplyImage,
    # Request,
)

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

        try:
            User.create(
                name=name,
                email=email,
                password_hash=generate_password_hash(password),
                icon=None,  # あとでかプロフィールアイコン実装時に考える
                deleted_at=None,  # 明示的にNoneを入れないと謎の時刻が入る　なぜ？
            )
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
