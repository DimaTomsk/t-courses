from typing import Any, Optional

from loguru import logger
from prometheus_client import Gauge
from pymongo.database import Database

from app.storage.keyval import KeyVal, MongoKeyVal, data_records

tag_metric = Gauge("user_by_tag", "Users by tags", labelnames=["tag"])


class User(KeyVal):
    def __init__(self, login: str, email: str, password: str, database: Database):
        super().__init__()
        assert (
            login.lower().strip() == login
        ), f"Login '{login}' must be lowercase & stripped!"

        self.login = login
        self.email = email
        self.password = password
        self.data_keyval = MongoKeyVal(login, database["data"])
        self.tags_keyval = MongoKeyVal(login, database["tags"])

    @staticmethod
    def read_all(database: Database):
        docs = list(database["data"].find({}, {"_id": 1, "email": 1, "password": 1}))
        logger.info(f"Found {len(docs)} users")
        users = []
        for item in docs:
            users.append(User(item["_id"], item["email"], item["password"], database))

        pipeline = [
            {
                "$project": {
                    "paramsArray": {"$objectToArray": {"$ifNull": ["$values", {}]}}
                }
            },
            {"$unwind": "$paramsArray"},
            {"$group": {"_id": "$paramsArray.k", "count": {"$sum": 1}}},
        ]
        for item in database["tags"].aggregate(pipeline):
            tag_metric.labels(item["_id"]).set(item["count"])
            data_records.labels(item["_id"]).set(item["count"])
        for item in database["data"].aggregate(pipeline):
            data_records.labels(item["_id"]).set(item["count"])

        return users

    @staticmethod
    def create_new(login: str, email: str, password: str, database: Database):
        database["data"].update_one(
            {"_id": login},
            {
                "$set": {
                    "email": email,
                    "password": password,
                }
            },
            upsert=True,
        )
        return User(login, email, password, database)

    def get_tags(self):
        return [key for key, value in self.tags_keyval.get_items() if value]

    def on_login(self):
        pass

    def get_password(self) -> str:
        return self.password

    def get_login(self) -> str:
        return self.login

    def get_email(self) -> str:
        return self.email

    def get_field(self, field: str) -> Optional[Any]:
        assert field.lower().strip() == field, "Field must be lowercase & stripped!"
        return self.data_keyval.get_field(field)

    def push_tag(self, tag: str) -> None:
        if tag not in self.get_tags():
            self.tags_keyval.push_fields({tag: True})
            tag_metric.labels(tag).inc(1)

    def pop_tag(self, tag: str) -> None:
        if tag in self.get_tags():
            self.tags_keyval.push_fields({tag: False})
            tag_metric.labels(tag).inc(-1)

    def push_fields(self, data: dict[str, Any]) -> None:
        self.data_keyval.push_fields(data)
