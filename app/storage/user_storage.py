import os
import time
from typing import Optional

from aiomysql import Pool
from loguru import logger
from pymongo import MongoClient

from app.ejudge.registration import create_new_user
from app.engine.lang import LoginGenerator
from app.engine.singleton import Singleton
from app.models.account import BaseAccountInfo
from app.storage.user import User

MONGO_URI = os.environ["MONGO_URI"]


class UserStorage(metaclass=Singleton):
    def __init__(self):
        self.client = MongoClient(MONGO_URI)
        self.database = self.client["t-courses-v1_0"]

        self.user_by_login: dict[str, User] = {}
        self.user_by_email: dict[str, User] = {}
        self.login_by_user_id: dict[int, str] = {}

    async def load_users(self):
        logger.info("Loading users...")
        start = time.time()

        self.user_by_login: dict[str, User] = {}
        self.user_by_email: dict[str, User] = {}

        for user in User.read_all(self.database):
            await self._push(user)

        end = time.time()
        logger.info(f"Loading completed in {end - start:.2f} seconds.")

    async def _push(self, user: User) -> None:
        assert user.get_login() not in self.user_by_login, f"{user.get_login()}"
        assert user.get_email() not in self.user_by_email, f"{user.get_login()}"

        self.user_by_login[user.get_login()] = user
        self.user_by_email[user.get_email()] = user

    async def _push_ejudge(self, user: User, pool: Pool) -> None:
        name = f"{user.get_field('surname')} {user.get_field('name')}"
        user_id = await create_new_user(user.get_login(), name, pool)
        assert (
            user_id not in self.user_by_login
        ), f"{user.get_login()} got same id={user_id} as {self.login_by_user_id[user_id]}"
        self.login_by_user_id[user_id] = user.get_login()

    async def create_new_user(self, account_info: BaseAccountInfo, pool: Pool) -> User:
        login = LoginGenerator(account_info.surname)
        while str(login) in self.user_by_login:
            login = login.next()

        password = login.gen_password()
        login = str(login)

        data = account_info.model_dump()
        data["login"] = login
        data["password"] = password

        user = User.create_new(login, account_info.email, password, self.database)
        user.push_fields(data)
        user.push_tag("user")

        await self._push(user)
        await self._push_ejudge(user, pool)

        return user

    def login(self, login: str, password: str) -> Optional[User]:
        if login in self.user_by_login:
            user = self.user_by_login[login]
            if user.get_password() == password:
                return user
        return None

    def get_user_by_login(self, login: Optional[str]) -> Optional[User]:
        if login is None or login not in self.user_by_login:
            return None
        return self.user_by_login[login]

    def get_user_by_email(self, email: str) -> Optional[User]:
        return self.user_by_email.get(email, None)
