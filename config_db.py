from datetime import datetime, timezone
from flask_login import UserMixin
from config import db
from peewee import (
    Model,
    IntegerField,
    CharField,
    TextField,
    TimestampField,
    ForeignKeyField,
    DoubleField,
    BooleanField,
)


# JWT標準がUTC基準なので関数化
def _now():
    return datetime.now(timezone.utc)


class User(UserMixin, Model):
    id = IntegerField(primary_key=True)
    name = CharField(max_length=128)
    email = CharField(max_length=254, unique=True)
    password_hash = CharField(max_length=255)
    icon = CharField(max_length=512, null=True)
    date = TimestampField(default=_now)
    deleted_at = TimestampField(null=True)

    class Meta:
        database = db
        table_name = "users"


class Spot(Model):
    id = IntegerField(primary_key=True)
    title = CharField(max_length=128)
    lat = DoubleField()
    lng = DoubleField()
    user = ForeignKeyField(User, backref="spots", on_delete="RESTRICT")
    comment = TextField()
    start_date = TimestampField(null=True)
    end_date = TimestampField(null=True)
    category = CharField(max_length=32)
    date = TimestampField(default=_now)
    deleted_at = TimestampField(null=True)

    class Meta:
        database = db
        table_name = "spots"


class SpotImage(Model):
    spot = ForeignKeyField(Spot, backref="images", on_delete="CASCADE")
    path = CharField(max_length=512)

    class Meta:
        database = db
        table_name = "spot_images"


class Tag(Model):
    id = IntegerField(primary_key=True)
    name = CharField(max_length=64, unique=True)

    class Meta:
        database = db
        table_name = "tags"


class SpotTag(Model):
    spot = ForeignKeyField(Spot, backref="spot_tags", on_delete="CASCADE")
    tag = ForeignKeyField(Tag, backref="tag_spots", on_delete="CASCADE")

    class Meta:
        database = db
        table_name = "spot_tags"
        indexes = ((("spot", "tag"), True),)


class SpotGood(Model):
    spot = ForeignKeyField(Spot, backref="goods", on_delete="CASCADE")
    user = ForeignKeyField(User, backref="good_spots", on_delete="CASCADE")

    class Meta:
        database = db
        table_name = "spot_goods"
        indexes = ((("spot", "user"), True),)


class SpotBad(Model):
    spot = ForeignKeyField(Spot, backref="bads", on_delete="CASCADE")
    user = ForeignKeyField(User, backref="bad_spots", on_delete="CASCADE")

    class Meta:
        database = db
        table_name = "spot_bads"
        indexes = ((("spot", "user"), True),)


class SpotSolved(Model):
    spot = ForeignKeyField(Spot, backref="solved_by", on_delete="CASCADE")
    user = ForeignKeyField(User, backref="solved_spots", on_delete="CASCADE")

    class Meta:
        database = db
        table_name = "spot_solved"
        indexes = ((("spot", "user"), True),)


class Group(Model):
    id = IntegerField(primary_key=True)
    user = ForeignKeyField(User, backref="groups", on_delete="RESTRICT")
    lat = DoubleField()
    lon = DoubleField()
    comment = TextField(null=True)
    category = CharField(max_length=32, null=True)
    date = TimestampField(default=_now)
    is_public = BooleanField()
    deleted_at = TimestampField(null=True)

    class Meta:
        database = db
        table_name = "groups"


class GroupImage(Model):
    reply = ForeignKeyField(Group, backref="images", on_delete="CASCADE")
    path = CharField(max_length=512)

    class Meta:
        database = db
        table_name = "group_images"


class GroupSpot(Model):
    group = ForeignKeyField(Group, backref="group_spots", on_delete="CASCADE")
    spot = ForeignKeyField(Spot, backref="spot_groups", on_delete="CASCADE")

    class Meta:
        database = db
        table_name = "group_spots"
        indexes = ((("group", "spot"), True),)


class GroupTag(Model):
    group = ForeignKeyField(Group, backref="group_tags", on_delete="CASCADE")
    tag = ForeignKeyField(Tag, backref="tag_groups", on_delete="CASCADE")

    class Meta:
        database = db
        table_name = "group_tags"
        indexes = ((("group", "tag"), True),)


class GroupGood(Model):
    group = ForeignKeyField(Group, backref="goods", on_delete="CASCADE")
    user = ForeignKeyField(User, backref="good_groups", on_delete="CASCADE")

    class Meta:
        database = db
        table_name = "group_goods"
        indexes = ((("group", "user"), True),)


class GroupBad(Model):
    group = ForeignKeyField(Group, backref="bads", on_delete="CASCADE")
    user = ForeignKeyField(User, backref="bad_groups", on_delete="CASCADE")

    class Meta:
        database = db
        table_name = "group_bads"
        indexes = ((("group", "user"), True),)


class Reply(Model):
    id = IntegerField(primary_key=True)
    spot = ForeignKeyField(Spot, backref="replies", null=True, on_delete="SET NULL")
    group = ForeignKeyField(Group, backref="replies", null=True, on_delete="SET NULL")
    comment = TextField()
    date = TimestampField(default=_now)
    deleted_at = TimestampField(null=True)

    class Meta:
        database = db
        table_name = "replies"


class ReplyImage(Model):
    reply = ForeignKeyField(Reply, backref="images", on_delete="CASCADE")
    path = CharField(max_length=512)

    class Meta:
        database = db
        table_name = "reply_images"


class Request(Model):
    id = IntegerField(primary_key=True)
    table = CharField(max_length=16)
    target_id = IntegerField()
    comment = TextField(null=True)
    necessity = BooleanField(null=True)
    solved = BooleanField(default=False)

    class Meta:
        database = db
        table_name = "requests"


def create_tables():
    db.create_tables(
        [
            User,
            Spot,
            SpotImage,
            Tag,
            SpotTag,
            SpotGood,
            SpotBad,
            SpotSolved,
            Group,
            GroupSpot,
            GroupTag,
            GroupGood,
            GroupBad,
            Reply,
            ReplyImage,
            Request,
        ]
    )
    db.pragma("foreign_keys", 1, permanent=True)


# モジュールが直接実行された場合にテーブルを作成
if __name__ == "__main__":
    create_tables()
