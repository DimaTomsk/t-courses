import datetime
from datetime import datetime
from typing import Optional, Any

from prometheus_client import Gauge
from pymongo.collection import Collection


class KeyVal:
    def __init__(self):
        pass

    def get_field(self, field: str) -> Optional[Any]:
        raise NotImplementedError()


class DictKeyVal(KeyVal):
    def __init__(self, data: dict):
        super().__init__()
        self.data = data

    def get_field(self, field: str) -> Optional[Any]:
        return self.data.get(field, None)


class JoinKeyVal(KeyVal):
    def __init__(self, items: list[KeyVal]):
        super().__init__()
        self.items = items

    def get_field(self, field: str) -> Optional[Any]:
        for item in self.items:
            result = item.get_field(field)
            if result is not None:
                return result
        return None


data_records = Gauge("data_records", "Records in db", labelnames=["name"])


class MongoKeyVal(KeyVal):
    def __init__(self, _id: str, collection: Collection):
        if len(_id) > 300:
            raise ValueError("_id must be less than 300!")
        if len(_id) < 1:
            raise ValueError("_id must be greater than 1!")

        super().__init__()
        self.collection = collection
        self._id = _id

    def _get_doc(self) -> dict:
        result = (
            self.collection.find_one({"_id": self._id}, {"values": 1, "_id": 0}) or {}
        )
        return result.get("values", {})

    def get_items(self):
        return self._get_doc().items()

    def push_fields(self, data: dict[str, Any]) -> None:
        for key in data.keys():
            assert key.lower().strip() == key, "Key must be lowercase & stripped!"

        doc = self._get_doc()
        data_to_set = {}
        for key, value in data.items():
            if key not in doc:
                data_records.labels(key).inc(1)
            if isinstance(value, str) and len(value) > 300:
                raise ValueError(f"Value must be less than 300: {value}")
            data_to_set[f"values.{key}"] = value
        data_to_set["update"] = datetime.now()
        self.collection.update_one(
            {"_id": self._id}, {"$set": data_to_set}, upsert=True
        )

    def get_field(self, field: str) -> Optional[Any]:
        assert field.lower().strip() == field, "Field must be lowercase & stripped!"
        return self._get_doc().get(field)
