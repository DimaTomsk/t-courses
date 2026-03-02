from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from typing_extensions import Annotated

from app.ejudge.web_login import perform_login
from app.engine.auth_storage import AuthStorage
from app.engine.config_loader import ConfigLoader
from app.models.config import GlobalConfig
from app.routers.authenticator import UserSession
from app.storage.user_storage import UserStorage


class ApiEjudge:
    def __init__(
        self,
        auth_storage: AuthStorage,
        user_storage: UserStorage,
        config_loader: ConfigLoader,
    ):
        self._router = APIRouter(prefix="/ejudge", tags=["ejudge"])

        self._auth_storage = auth_storage
        self._user_storage = user_storage
        self._config_loader = config_loader

        self._router.add_api_route(
            "/login/{course_name}/{contest_id}",
            self.login_contest,
            methods=["GET"],
            name="ejudge.login",
        )

    def get_router(self):
        return self._router

    async def login_contest(
        self,
        course_name: str,
        contest_id: int,
        user_session: Annotated[UserSession, Depends()],
    ) -> RedirectResponse:
        if user_session.user is None:
            return RedirectResponse(url="/", status_code=302)
        config = self._config_loader.get_config()
        if course_name not in config.course_config:
            return RedirectResponse(url="/", status_code=302)

        contests_by_tags = config.course_config[course_name].get_contests_by_tags(
            user_session.user.get_tags()
        )
        if contest_id not in contests_by_tags:
            return RedirectResponse(url=f"/courses/{course_name}", status_code=302)

        result = await perform_login(
            str(contest_id),
            user_session.user.get_login(),
        )
        if result is None:
            return RedirectResponse(url=f"/courses/{course_name}", status_code=302)

        response = RedirectResponse(
            url=f"https://ej-3.t-edu.tech/ejudge/redirect?sid={result.SID}&ejsid={result.EJSID}",
            status_code=302,
        )
        return response
