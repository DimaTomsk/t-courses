from fastapi import APIRouter, Depends
from prometheus_client import Counter, disable_created_metrics
from typing_extensions import Annotated

from app.engine.auth_storage import AuthStorage
from app.engine.config_loader import ConfigLoader
from app.routers.authenticator import UserSession
from app.storage.user_storage import UserStorage


class ApiAnalytics:
    def __init__(
        self,
        auth_storage: AuthStorage,
        user_storage: UserStorage,
        config_loader: ConfigLoader,
    ):
        self._router = APIRouter(prefix="/analytics", tags=["analytics"])

        self._auth_storage = auth_storage
        self._user_storage = user_storage
        self._config_loader = config_loader

        self._router.add_api_route(
            "/link_clicked",
            self.link_clicked,
            methods=["POST"],
            name="analytics.url_clicked",
        )

        disable_created_metrics()
        self.link_clicks = Counter(
            "link_clicks", "Link clicks", labelnames=["location", "link", "authorized"]
        )

    def get_router(self):
        return self._router

    async def link_clicked(
        self, data: dict, user_session: Annotated[UserSession, Depends()]
    ):
        self.link_clicks.labels(
            location=data["location"],
            link=data["link"],
            authorized=int(user_session.user is not None),
        ).inc()
