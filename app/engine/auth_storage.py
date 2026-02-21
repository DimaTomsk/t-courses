import secrets
from typing import Optional

from cachetools import TTLCache

from app.engine.singleton import Singleton

COOKIE_TTL = 60 * 60 * 24


def gen_secret() -> str:
    return secrets.token_urlsafe(32)


class AuthStorage(metaclass=Singleton):
    def __init__(self):
        self._login_by_cookie: TTLCache[str, str] = TTLCache(
            maxsize=10000, ttl=COOKIE_TTL
        )

    def check_cookie(self, cookie: Optional[str]) -> Optional[str]:
        if cookie is None:
            return None
        result = self._login_by_cookie.get(cookie, None)
        if result is not None:
            self._login_by_cookie[cookie] = result  # do not forget to refresh
        return result

    def pop_cookie(self, cookie: str):
        self._login_by_cookie.pop(cookie, None)

    def get_or_create_cookie(self, login: str) -> str:
        cookie = gen_secret()
        self._login_by_cookie[cookie] = login
        return cookie
