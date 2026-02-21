from typing import Literal

from pydantic import BaseModel, Field, field_validator


class BaseAccountInfo(BaseModel):
    name: str = Field(min_length=1)
    surname: str = Field(min_length=1)
    email: str = Field(min_length=1)
    agreement: Literal[True]
    ads_agreement: bool = False

    @field_validator("*", mode="before")
    def strip_strings(cls, v):
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator("email", mode="before")
    def email_stripper(cls, v):
        return v.strip().lower()


class ResetAccountData(BaseModel):
    email: str = Field(min_length=1)

    @field_validator("email", mode="before")
    def email_stripper(cls, v):
        return v.strip().lower()
