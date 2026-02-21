from fastapi import APIRouter, Depends
from pydantic import BaseModel
from starlette.responses import JSONResponse
from typing_extensions import Annotated

from app.engine.auth_storage import AuthStorage
from app.forms.form_response import FormResponse
from app.routers.authenticator import UserSession
from app.storage.user_storage import UserStorage


class ApiAuth:
    class LoginCreds(BaseModel):
        login: str
        password: str

    def __init__(self, auth_storage: AuthStorage, user_storage: UserStorage):
        self._router = APIRouter(prefix="/auth", tags=["authentication"])

        self._auth_storage = auth_storage
        self._user_storage = user_storage

        self._router.add_api_route(
            "/login", self.login, methods=["POST"], name="auth.login"
        )
        self._router.add_api_route(
            "/logout", self.logout, methods=["POST"], name="auth.logout"
        )

    def get_router(self):
        return self._router

    async def logout(self, user_session: Annotated[UserSession, Depends()]):
        if user_session.session_id is not None:
            self._auth_storage.pop_cookie(user_session.session_id)
        return UserSession.delete_cookie(JSONResponse({"success": True}))

    async def login(self, creds: LoginCreds):
        user = self._user_storage.login(creds.login, creds.password)
        if user is not None:
            user.on_login()
            cookie = self._auth_storage.get_or_create_cookie(creds.login)
            response = JSONResponse(
                FormResponse(success=True, reload=True).model_dump()
            )
            return UserSession(session_id=cookie).update_cookie(response)
        return FormResponse(success=False, detail="Неверный логин или пароль")
