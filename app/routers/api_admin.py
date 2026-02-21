import os

from fastapi import APIRouter, HTTPException
from loguru import logger

from app.engine.auth_storage import AuthStorage
from app.engine.config_loader import ConfigLoader
from app.storage.user_storage import UserStorage

ADMIN_SECRET: str = os.environ["ADMIN_SECRET"]
logger.info(f"Admin secret: {ADMIN_SECRET[:5]}...")


class ApiAdmin:
    def __init__(
        self,
        auth_storage: AuthStorage,
        user_storage: UserStorage,
        config_loader: ConfigLoader,
    ):
        self._router = APIRouter(prefix="/admin", tags=["admin"])

        self._auth_storage = auth_storage
        self._user_storage = user_storage
        self._config_loader = config_loader

        self._router.add_api_route(
            "/add_tag", self.add_tag, methods=["post"], name="admin.add_tag"
        )
        self._router.add_api_route(
            "/upload_users",
            self.upload_users,
            methods=["get"],
            name="admin.upload_users",
        )
        self._router.add_api_route(
            "/remove_tag", self.remove_tag, methods=["post"], name="admin.remove_tag"
        )
        self._router.add_api_route(
            "/update_config",
            self.update_config,
            methods=["post"],
            name="admin.update_config",
        )

    def get_router(self):
        return self._router

    async def add_tag(self, token: str, login: str, tag: str):
        if token != ADMIN_SECRET:
            return {"success": False}
        user = self._user_storage.get_user_by_login(login)
        if user is None:
            return {"success": False}

        if tag not in user.get_tags():
            user.push_tag(tag)
        return {"success": True}

    async def upload_users(self, token: str, fields: str, tag: str = None):
        if token != ADMIN_SECRET:
            return {"success": False}

        fields = fields.split(",")

        result = {}
        for key, value in self._user_storage.user_by_login.items():
            if tag is not None and tag not in value.get_tags():
                continue
            result[key] = [value.get_field(field) for field in fields]

        return {"success": True, "values": result}

    async def remove_tag(self, token: str, login: str, tag: str):
        if token != ADMIN_SECRET:
            return {"success": False}
        user = self._user_storage.get_user_by_login(login)
        if user is None or tag not in user.get_tags():
            return {"success": False}

        user.pop_tag(tag)
        return {"success": True}

    async def update_config(self, token: str):
        if token != ADMIN_SECRET:
            return {"success": False}
        try:
            self._config_loader.update()
            return {"success": True}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
