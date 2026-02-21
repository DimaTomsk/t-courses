import asyncio
import os
from typing import Optional

import aiohttp
from fastapi import Cookie, HTTPException
from fastapi.responses import Response
from loguru import logger
from starlette.requests import Request

from app.engine.auth_storage import AuthStorage, COOKIE_TTL
from app.storage.user import User
from app.storage.user_storage import UserStorage

SMARTCAPTCHA_SERVER_KEY = os.environ["SMARTCAPTCHA_SERVER_KEY"]

SESSION_COOKIE = "session_id"

auth_storage = AuthStorage()
user_storage = UserStorage()


class UserSession:
    def __init__(self, session_id: Optional[str] = Cookie(None)):
        self.user: Optional[User] = None
        self.session_id: Optional[str] = None

        login = auth_storage.check_cookie(session_id)
        user: Optional[User] = user_storage.get_user_by_login(login)
        if user is not None and session_id is not None:
            self.user = user
            self.session_id = session_id

    @staticmethod
    def delete_cookie(response: Response) -> Response:
        response.delete_cookie(key=SESSION_COOKIE)
        return response

    def update_cookie(self, response: Response) -> Response:
        if self.user is None or self.session_id is None:
            UserSession.delete_cookie(response)
        else:
            response.set_cookie(
                key=SESSION_COOKIE,
                value=self.session_id,
                httponly=True,
                max_age=COOKIE_TTL,
                samesite="strict",
            )
        return response


async def verify_captcha(request: Request):
    data = await request.json()

    # if data["captcha"] == "test-captcha":
    #     return True

    # raise HTTPException(
    #     status_code=400,
    #     detail="Капча не прошла проверку, попробуйте еще раз",
    # )

    url = "https://smartcaptcha.yandexcloud.net/validate"

    try:
        params = {
            "secret": SMARTCAPTCHA_SERVER_KEY,
            "token": data["captcha"],
            "ip": request.client.host,
        }
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=2)
        ) as session:
            async with session.get(url, params=params) as resp:
                data = await resp.json()
                if resp.status != 200 or data.get("status") != "ok":
                    raise HTTPException(
                        status_code=400,
                        detail="Капча не прошла проверку, попробуйте еще раз",
                    )
                return
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=400,
            detail="Капча не прошла проверку, попробуйте еще раз",
        )
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Капча не прошла проверку, попробуйте еще раз",
        )
    raise HTTPException(
        status_code=400,
        detail="Капча не прошла проверку, попробуйте еще раз",
    )
