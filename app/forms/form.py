from typing import Union, Optional

from pydantic import BaseModel, field_validator, Field, model_validator
from typing_extensions import Literal, Annotated

from app.storage.user import User, KeyVal


class BaseFormItem(BaseModel):
    label: str
    condition: str = "true"


class UserInputItem(BaseFormItem):
    required: bool = False

    def process_val(self, val):
        if (
            self.required and self.condition == "true"
        ):  # I have no idea how to calculate condition...
            if val is None:
                raise ValueError("Required field is missing")
            if isinstance(val, str) and len(val) == 0:
                raise ValueError("Required field is missing")
        return val


class DateItem(UserInputItem):
    type: Literal["date"] = "date"

    def process_val(self, val):
        val = super().process_val(val)
        if val is None:
            return None
        if not isinstance(val, str):
            raise ValueError("Date item not a string")
        return val


class NumberItem(UserInputItem):
    type: Literal["number"] = "number"

    def process_val(self, val):
        val = super().process_val(val)
        if val is None:
            return None
        if not isinstance(val, str) and not isinstance(val, int):
            raise ValueError("Number item not a int")
        return val


class TextItem(UserInputItem):
    type: Literal["text"] = "text"
    placeholder: str = " "

    def process_val(self, val):
        val = super().process_val(val)
        if val is None:
            return None
        if not isinstance(val, str):
            raise ValueError("Text item not a string")
        return val.strip()


class PasswordItem(UserInputItem):
    type: Literal["password"] = "password"

    def process_val(self, val):
        val = super().process_val(val)
        if val is None:
            return None
        if not isinstance(val, str):
            raise ValueError("Password item not a string")
        return val


class EmailItem(TextItem):
    type: Literal["email"] = "email"

    def process_val(self, val):
        val = super().process_val(val)
        if val is None:
            return None
        if not isinstance(val, str):
            raise ValueError("Email item not a string")
        return val.lower().strip()


class PhoneItem(TextItem):
    type: Literal["phone"] = "phone"

    def process_val(self, val):
        val = super().process_val(val)
        if val is None:
            return None
        if not isinstance(val, str):
            raise ValueError("Phone item not a string")
        return val.lower().strip()


class CheckboxItem(UserInputItem):
    type: Literal["checkbox"] = "checkbox"

    def process_val(self, val):
        val = super().process_val(val)
        if val is None:
            return None
        if not isinstance(val, bool):
            raise ValueError("Checkbox item not a bool")
        return val


class SelectorItem(UserInputItem):
    type: Literal["selector"] = "selector"
    options: list[str]

    def process_val(self, val):
        val = super().process_val(val)
        if val is None:
            return None
        if not isinstance(val, str):
            raise ValueError("Selector item not a str")
        if not val in self.options:
            raise ValueError("Selector item not a option!")
        return val


class InfoItem(BaseFormItem):
    type: Literal["info"] = "info"


FormItem = Annotated[
    Union[
        DateItem,
        TextItem,
        PasswordItem,
        EmailItem,
        PhoneItem,
        CheckboxItem,
        SelectorItem,
        NumberItem,
        InfoItem,
    ],
    Field(discriminator="type"),
]


class Form(BaseModel):
    rows: list[list[str]]
    items: dict[str, FormItem]
    icons: bool
    captcha: bool
    action: str
    depends: list[str]
    path: str
    title: str

    @field_validator("rows", mode="before")
    def normalize_rows(cls, v):
        assert isinstance(v, list)
        out = []
        for item in v:
            if isinstance(item, str):
                out.append([item])
            else:
                out.append(item)
        return out

    @model_validator(mode="after")
    def check_model(self):
        keys = []
        for item in self.rows:
            keys.extend(item)
        if len(keys) != len(self.items):
            raise ValueError("Unused form items detected!")
        if set(keys) != set(self.items.keys()):
            raise ValueError("Missing/extra keys detected!")
        return self

    def check_for(self, data: KeyVal) -> Optional[dict]:
        result = {}
        for key, item in self.items.items():
            if not isinstance(item, UserInputItem):
                continue
            try:
                val = item.process_val(data.get_field(key))
                result[key] = val
            except ValueError as err:
                return None
        return result
