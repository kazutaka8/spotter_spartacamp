from flask import Blueprint, render_template, request, jsonify
from flask_login import current_user, login_required
import math
import os
from datetime import datetime
from werkzeug.utils import secure_filename
from config import UPLOAD_DIR
from config_db import (
    # User,
    Spot,
    SpotImage,
    Tag,
    SpotTag,
    Reply,
    ReplyImage,
    Group,
    GroupSpot,
    GroupTag,
    # SpotGood,
    # SpotBad,
    # SpotSolved,
    # GroupGood,
    # GroupBad,
    # Request,
)

bp_view = Blueprint("view", __name__)


def calculate_distance(lat1, lng1, lat2, lng2):
    # Haversine公式で距離計算（km） 引数は二点の緯度経度　出力は距離
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    )
    return 6371 * 2 * math.asin(math.sqrt(a))


@bp_view.route("/")
def index():
    return render_template("index.html")


# URLを指定してアクセスすることでグループを表示できるように。QRコード向け機能
@bp_view.route("/groups/<int:group_id>/view")
def view_group(group_id):
    return render_template("index.html", group_id=group_id)


# スポット表示のapi 現状は中心座標とズームレベルに応じた半径を受け取り対象スポットを返す
@bp_view.route("/spots", methods=["POST"])
def get_spots():
    data = request.get_json()
    center_lat = data.get("lat")
    center_lng = data.get("lng")
    radius = data.get("radius", 5.0)  # デフォルト5km

    # 【追加】必須パラメータのバリデーション
    if center_lat is None or center_lng is None:
        return jsonify({"error": "緯度経度は必須パラメータです"}), 400

    # 全spotを取得して距離でフィルタリング
    all_spots = Spot.select().where(Spot.deleted_at.is_null()).order_by(Spot.date.desc())

    spot_list = []
    for spot in all_spots:
        distance = calculate_distance(center_lat, center_lng, float(spot.lat), float(spot.lng))
        if distance <= radius:
            # タグ取得
            tags = [tag.name for tag in Tag.select().join(SpotTag).where(SpotTag.spot == spot)]

            # 【追加】スポット画像取得（最初の1枚のみ）
            images = [img.path for img in spot.images]  # SpotImageテーブルから画像パス取得

            spot_list.append(
                {
                    "id": spot.id,
                    "title": spot.title,
                    "lat": float(spot.lat),
                    "lng": float(spot.lng),
                    "category": spot.category,
                    "user_name": spot.user.name,
                    "user_icon": spot.user.icon,
                    "date": spot.date.strftime("%Y-%m-%d %H:%M"),
                    "comment": spot.comment,
                    "tags": tags,
                    "images": images,  # 【追加】画像パス配列をレスポンスに含める
                }
            )

        # 100件で制限
        if len(spot_list) >= 100:
            break

    return jsonify(spot_list)


# スポット登録api 緯度経度、画像、タイトル、コメント、カテゴリー、タグを取得する
@bp_view.route("/spots/create", methods=["POST"])
@login_required
def create_spot():
    # フォームデータ取得
    title = request.form.get("title", "").strip()
    comment = request.form.get("comment", "").strip()
    category = request.form.get("category", "観光")
    lat = float(request.form.get("lat"))
    lng = float(request.form.get("lng"))

    # タグデータ取得
    tags = []
    for i in range(1, 6):  # tag1〜tag5
        tag_name = request.form.get(f"tag{i}", "").strip()
        if tag_name:
            tags.append(tag_name)

    # バリデーション
    if not title:
        return jsonify({"error": "タイトルは必須です"}), 400

    # spot作成
    spot = Spot.create(
        title=title,
        comment=comment,
        category=category,
        lat=lat,
        lng=lng,
        start_date=None,
        end_date=None,
        deleted_at=None,
        user=current_user.id,
    )

    # 画像アップロード処理
    uploaded_file = request.files.get("image")
    if uploaded_file and uploaded_file.filename:
        filename = secure_filename(uploaded_file.filename)
        # 拡張子を取得
        file_ext = os.path.splitext(filename)[1]
        # 命名規則: spot_{spot_id}_{timestamp}
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_filename = f"spot_{spot.id}_{timestamp}{file_ext}"

        # spotフォルダを作成
        spot_dir = os.path.join(UPLOAD_DIR, "spot")
        os.makedirs(spot_dir, exist_ok=True)
        file_path = os.path.join(spot_dir, unique_filename)

        # ファイル保存
        uploaded_file.save(file_path)

        # DB画像レコード作成
        SpotImage.create(
            spot=spot,
            path=unique_filename,
        )

    # タグ登録
    for tag_name in tags:
        # タグを取得または作成　　タプルでtag,createの成否を受け取るが使わない後者はアンダースコアで捨てられるらしい。
        tag, _ = Tag.get_or_create(name=tag_name)
        # SpotTagで関連付け
        SpotTag.create(spot=spot, tag=tag)

    return jsonify(
        {
            "success": True,
            "spot": {
                "id": spot.id,
                "title": spot.title,
                "lat": float(spot.lat),
                "lng": float(spot.lng),
                "category": spot.category,
            },
        }
    )


@bp_view.route("/spots/<int:spot_id>/replies", methods=["GET"])
def get_replies(spot_id):
    replies = (
        Reply.select().where(Reply.spot == spot_id, Reply.deleted_at.is_null()).order_by(Reply.date.desc())
    )

    reply_list = []
    for reply in replies:
        # 【追加】返信画像URL構成（最初の1枚のみ）
        reply_images = [img.path for img in reply.images]
        image_url = f"/uploads/reply/{reply_images[0]}" if reply_images else None

        reply_list.append(
            {
                "id": reply.id,
                "comment": reply.comment,
                "user_name": reply.user.name,
                "user_icon": reply.user.icon,
                "date": reply.date.strftime("%Y-%m-%d %H:%M"),
                "imageUrl": image_url,  # 【追加】画像URLをレスポンスに含める
            }
        )

    return jsonify(reply_list)

