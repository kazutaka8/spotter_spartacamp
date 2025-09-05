from flask import Blueprint, render_template, request, jsonify
from flask_login import current_user, login_required
from peewee import JOIN
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

# blueprintでapiファイルを分割
bp_view = Blueprint("view", __name__)


def calculate_distance(lat1, lng1, lat2, lng2):
    # Haversine公式で距離計算（km） 引数は二点の緯度経度　出力は距離
    # spotの読み込み範囲を決めるための関数
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    )
    dist = 6371 * 2 * math.asin(math.sqrt(a))
    return dist


# 初期ページ
@bp_view.route("/")
def index():
    return render_template("index.html")


# URLを指定してアクセスすることでグループを表示できるように。QRコード向け機能
@bp_view.route("/groups/<int:group_id>/view")
def view_group(group_id):
    return render_template("index.html", group_id=group_id)


# スポット表示のapi 現状は中心座標とズームレベルに応じた半径を受け取り対象スポットを返す
# fetch('/spots', {
#     method: 'POST',
#     headers: { 'Content-Type': 'application/json' }, //json形式で送る場合は必要
#     body: JSON.stringify({ lat: center.lat, lng: center.lng, radius })
# })
@bp_view.route("/spots", methods=["POST"])
def get_spots():
    data = request.get_json()
    center_lat = data.get("lat")
    center_lng = data.get("lng")
    radius = data.get("radius", 5.0)  # デフォルト5km

    # 必須パラメータのバリデーション
    if center_lat is None or center_lng is None:
        return jsonify({"error": "緯度経度は必須パラメータです"}), 400

    # 全spotを取得して距離でフィルタリング
    all_spots = Spot.select().where(Spot.deleted_at.is_null()).order_by(Spot.date.desc())

    spot_list = []
    for spot in all_spots:
        distance = calculate_distance(center_lat, center_lng, float(spot.lat), float(spot.lng))
        # spot.latは文字列だから注意
        if distance <= radius:
            # タグ取得
            tags = [tag.name for tag in Tag.select().join(SpotTag).where(SpotTag.spot == spot)]

            # スポット画像取得（HTML側の対応が間に合わないので最初の1枚のみ）
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
                    "images": images,
                }
            )

        # 100件で制限
        if len(spot_list) >= 100:
            break

    return jsonify(spot_list)


# スポット登録api 緯度経度、画像、タイトル、コメント、カテゴリー、タグを取得する
# ここでjsonにしないのは画像をやり取りするから（jsonでは画像を扱えない)
# formData.append('title', document.getElementById('spotTitle').value);
# formData.append('comment', document.getElementById('spotComment').value);
# formData.append('category', document.getElementById('spotCategory').value);
# formData.append('tag1', document.getElementById('spotTag1').value);
# formData.append('tag2', document.getElementById('spotTag2').value);
# formData.append('tag3', document.getElementById('spotTag3').value);
# formData.append('tag4', document.getElementById('spotTag4').value);
# formData.append('tag5', document.getElementById('spotTag5').value);
# formData.append('lat', lat); formData.append('lng', lng);
# // 画像
# const imageFile = document.getElementById('spotImage').files[0];
# if (imageFile) formData.append('image', imageFile);
@bp_view.route("/spots/create", methods=["POST"])
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

    # タグデータ取得
    tags = []
    for i in range(1, 6):  # tag1〜tag5
        tag_name = request.form.get(f"tag{i}", "").strip()
        if tag_name:
            tags.append(tag_name)

    # spot作成　noneがないとタイムスタンプフィールドに値が入ってしまう　なぜ...
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
    if uploaded_file:
        # 悪意あるファイル名をブロック
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

        # DB画像レコード作成　これは別テーブルだから別途
        SpotImage.create(
            spot=spot,
            path=unique_filename,
        )

    # タグ登録　これも別テーブル
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


# スポットへの返信取得
# fd.append('comment', text);
# if (file) fd.append('image', file);
# fetch(`/spots/${spot.id}/replies`, { method: 'POST', body: fd });
@bp_view.route("/spots/<int:spot_id>/replies", methods=["GET"])
def get_replies(spot_id):
    replies = (
        Reply.select()
        .where(Reply.spot == spot_id, Reply.deleted_at.is_null())
        .order_by(Reply.date.desc())
    )

    reply_list = []
    for reply in replies:
        # backrefを使って画像パスを取得
        # backrefの使い方はreply.imagesでクエリをセット　その後listやfirstなどでクエリを実行となる
        # img = reply.imagesなどではTrueが入るだけ
        reply_images = list(reply.images)
        image_url = f"/uploads/reply/{reply_images[0].path}" if reply_images else None

        reply_list.append({
            "id": reply.id,
            "comment": reply.comment,
            "user_name": reply.user.name,
            "user_icon": reply.user.icon,
            "date": reply.date.strftime("%Y-%m-%d %H:%M"),
            "imageUrl": image_url,
        })

    return jsonify(reply_list)


# リプライの登録
# fd.append('comment', text);
# if (file) fd.append('image', file);
@bp_view.route("/spots/<int:spot_id>/replies", methods=["POST"])
@login_required
def create_reply(spot_id):
    comment = request.form.get("comment", "").strip()

    if not comment:
        return jsonify({"error": "コメントは必須です"}), 400

    # deleted_at=Noneに注意　返信が表示されない原因解明に時間かかった
    reply = Reply.create(spot=spot_id, user=current_user.id, comment=comment, deleted_at=None)

    # 画像アップロード処理
    uploaded_file = request.files.get("image")
    # バリデーション　uplaoded_fileは存在しても中身が空という状況があるらしい ファイル名も確認
    if uploaded_file and uploaded_file.filename:
        filename = secure_filename(uploaded_file.filename)
        file_ext = os.path.splitext(filename)[1]  # 拡張子取得
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_filename = f"reply_{reply.id}_{timestamp}{file_ext}"

        # replyフォルダを作成
        reply_dir = os.path.join(UPLOAD_DIR, "reply")
        os.makedirs(reply_dir, exist_ok=True)
        file_path = os.path.join(reply_dir, unique_filename)

        # ファイル保存
        uploaded_file.save(file_path)

        # DB画像レコード作成
        # 保存するパスにはファイル名だけの方が後から手を加えやすい
        ReplyImage.create(
            reply=reply,
            path=unique_filename,
        )

    return jsonify({"success": True})


# グループの表示（今はURLからのみ）
@bp_view.route("/groups/<int:group_id>", methods=["GET"])
def get_group(group_id):
    try:
        group = Group.select().where(Group.id == group_id, Group.deleted_at.is_null()).get()
    except Group.DoesNotExist:
        return jsonify({"error": "グループが見つかりません"}), 404

    # グループ内のスポットを取得
    # joinでgroupspotとspotを関連付け
    group_spots = (
        Spot.select()
        .join(GroupSpot)
        .where(GroupSpot.group == group_id, Spot.deleted_at.is_null())
        .order_by(Spot.date.desc())
    )

    spots = []
    for spot in group_spots:
        # 中間テーブルからタグを取得
        tags = [tag.name for tag in Tag.select().join(SpotTag).where(SpotTag.spot == spot)]
        spots.append(
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
            }
        )

    # グループのタグ取得
    group_tags = [tag.name for tag in Tag.select().join(GroupTag).where(GroupTag.group == group)]

    # グループ画像取得（今は最初の1枚のみ）
    group_images = [img.path for img in group.images]

    return jsonify(
        {
            "group": {
                "id": group.id,
                "title": group.title,
                "description": group.description,
                "user_name": group.user.name,
                "user_icon": group.user.icon,
                "date": group.date.strftime("%Y-%m-%d %H:%M"),
                "tags": group_tags,
                "is_public": group.is_public,
                "images": group_images,
            },
            "spots": spots,
        }
    )


# グループへの返信表示
@bp_view.route("/groups/<int:group_id>/replies", methods=["GET"])
def get_group_replies(group_id):
    replies = (
        Reply.select().where(Reply.group == group_id, Reply.deleted_at.is_null()).order_by(Reply.date.desc())
    )

    reply_list = []
    for reply in replies:
        # グループ返信画像URL構成（今は最初の1枚のみ）
        reply_images = [img.path for img in reply.images]
        image_url = f"/uploads/reply/{reply_images[0]}" if reply_images else None

        reply_list.append(
            {
                "id": reply.id,
                "comment": reply.comment,
                "user_name": reply.user.name,
                "user_icon": reply.user.icon,
                "date": reply.date.strftime("%Y-%m-%d %H:%M"),
                "imageUrl": image_url,
            }
        )

    return jsonify(reply_list)


# グループへの返信登録（基本的にspotと同じように）
# fd.append('comment', text);
# if (file) fd.append('image', file);
@bp_view.route("/groups/<int:group_id>/replies", methods=["POST"])
@login_required
def create_group_reply(group_id):
    comment = request.form.get("comment", "").strip()

    if not comment:
        return jsonify({"error": "コメントは必須です"}), 400

    reply = Reply.create(group=group_id, user=current_user.id, comment=comment, deleted_at=None)

    # 画像アップロード処理
    uploaded_file = request.files.get("image")
    if uploaded_file and uploaded_file.filename:
        filename = secure_filename(uploaded_file.filename)
        file_ext = os.path.splitext(filename)[1]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_filename = f"reply_group_{reply.id}_{timestamp}{file_ext}"

        # replyフォルダを作成（グループ返信も同じフォルダに保存）
        reply_dir = os.path.join(UPLOAD_DIR, "reply")
        os.makedirs(reply_dir, exist_ok=True)
        file_path = os.path.join(reply_dir, unique_filename)

        # ファイル保存
        uploaded_file.save(file_path)

        # DB画像レコード作成
        ReplyImage.create(
            reply=reply,
            path=unique_filename,
        )

    return jsonify({"success": True})
