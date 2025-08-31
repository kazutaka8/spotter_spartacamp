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

bp_view = Blueprint("view", __name__)


def calculate_distance(lat1, lng1, lat2, lng2):
    # Haversine公式で距離計算（km）
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


@bp_view.route("/api/spots", methods=["POST"])
def get_spots():
    data = request.get_json()
    center_lat = data.get("lat")
    center_lng = data.get("lng")
    radius = data.get("radius", 5.0)  # デフォルト5km

    # 全spotを取得して距離でフィルタリング
    all_spots = Spot.select().where(Spot.deleted_at.is_null()).order_by(Spot.date.desc())

    spot_list = []
    for spot in all_spots:
        distance = calculate_distance(center_lat, center_lng, float(spot.lat), float(spot.lng))
        if distance <= radius:
            spot_list.append(
                {
                    "id": spot.id,
                    "title": spot.title,
                    "lat": float(spot.lat),
                    "lng": float(spot.lng),
                    "category": spot.category,
                }
            )

        # 100件で制限
        if len(spot_list) >= 100:
            break

    return jsonify(spot_list)


@bp_view.route("/api/spots/create", methods=["POST"])
@login_required
def create_spot():
    # フォームデータ取得
    title = request.form.get("title", "").strip()
    comment = request.form.get("comment", "").strip()
    category = request.form.get("category", "観光")
    lat = float(request.form.get("lat"))
    lng = float(request.form.get("lng"))

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
        # 命名規則: spot_{spot_id}_{timestamp}_{元ファイル名}
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_filename = f"spot_{spot.id}_{timestamp}_{filename}"

        # アップロードディレクトリ作成
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        file_path = os.path.join(UPLOAD_DIR, unique_filename)

        # ファイル保存
        uploaded_file.save(file_path)

        # DB画像レコード作成
        SpotImage.create(
            spot=spot,
            path=unique_filename,
        )

    return
