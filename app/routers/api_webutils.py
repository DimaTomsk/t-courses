from fastapi import APIRouter
from starlette.responses import Response

from app.engine.auth_storage import AuthStorage
from app.engine.config_loader import ConfigLoader
from app.storage.user_storage import UserStorage

DOMAIN = "https://algocourses.ru"


class ApiWebutils:
    def __init__(
        self,
        auth_storage: AuthStorage,
        user_storage: UserStorage,
        config_loader: ConfigLoader,
    ):
        self._router = APIRouter(prefix="/webutils", tags=["webutils"])

        self._auth_storage = auth_storage
        self._user_storage = user_storage
        self._config_loader = config_loader

        self._router.add_api_route(
            "/sitemap.xml",
            self.sitemap,
            methods=["GET"],
            name="webutils.sitemap",
        )

    def get_router(self):
        return self._router

    async def sitemap(self):
        config = self._config_loader.get_config()

        items = []

        def add_url(url: str):
            items.append(
                f"""<url>
                    <loc>{DOMAIN}/{url}</loc>
                </url>"""
            )

        add_url("")
        for item in config.pages.keys():
            if item != "home":
                add_url(f"pages/{item}")
        for item in config.course_config.keys():
            add_url(f"courses/{item}")

        response_text = f"""<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            {'\n'.join(items)}
        </urlset>"""
        return Response(content=response_text, media_type="application/xml")
