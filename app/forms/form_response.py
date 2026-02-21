from pydantic import BaseModel


class FormResponse(BaseModel):
    success: bool
    detail: str = ""
    reload: bool = False
    reset_form: bool = False
