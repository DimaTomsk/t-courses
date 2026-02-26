import os
import time
from datetime import datetime

import dotenv
from aiomysql import Pool
from loguru import logger
from pymongo import MongoClient

dotenv.load_dotenv("secrets/.env")
from asyncio import Task
from app.ejudge.registration import EJUDGE_USER, EJUDGE_PASSWORD
from contextlib import asynccontextmanager
import aiomysql
import asyncio
from app.routers.api_standings import ApiStandings
from app.ejudge.table_component import TableComponent
from starlette.requests import Request

from app.forms.form_renderer import FormRenderer
from app.routers.api_webutils import ApiWebutils

from app.storage.user_storage import UserStorage
from app.routers.api_analytics import ApiAnalytics


from app.engine.config_loader import ConfigLoader


from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.staticfiles import StaticFiles
from prometheus_client import make_asgi_app

from app.engine.auth_storage import AuthStorage
from app.routers.api_account import ApiAccount
from app.routers.api_admin import ApiAdmin
from app.routers.api_auth import ApiAuth
from app.routers.api_ejudge import ApiEjudge
from app.routers.web_home import WebHome

MONGO_URI = os.environ["MONGO_URI"]

mongo_client = MongoClient(MONGO_URI)
database = mongo_client["t-courses-v1_0"]

auth_storage = AuthStorage(database["cookies"])
user_storage = UserStorage(database)


async def start_load(pool: Pool):
    try:
        start = time.time()
        for user in list(user_storage.user_by_login.values()):
            await user_storage._push_ejudge(user, pool)
        end = time.time()
        logger.info(f"Loaded users to ejudge in {end - start:.2f} seconds!")

        await table_component.run_update_loop(pool)
    except Exception as e:
        logger.exception(e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await user_storage.load_users()

    try:
        app.state.mysql_pool = await aiomysql.create_pool(
            host="localhost",
            autocommit=True,
            user=EJUDGE_USER,
            password=EJUDGE_PASSWORD,
            db="ejudge",
        )
        tasks.add(asyncio.create_task(start_load(app.state.mysql_pool)))
    except Exception as e:
        app.state.mysql_pool = None
        logger.warning(f"Mysql initialization failed! {e}")

    app.state.auth_storage = auth_storage
    app.state.user_storage = user_storage

    try:
        yield
    finally:
        for item in tasks:
            item.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

        if app.state.mysql_pool is not None:
            app.state.mysql_pool.close()
            await app.state.mysql_pool.wait_closed()


app = FastAPI(
    lifespan=lifespan,
    # docs_url=None,  # Disables Swagger UI
    # redoc_url=None,  # Disables ReDoc
    # openapi_url=None,  # Disables OpenAPI schema entirely
)

config_loader = ConfigLoader()

app.mount("/styles", StaticFiles(directory="resources/styles"), name="styles")
app.mount("/scripts", StaticFiles(directory="resources/scripts"), name="scripts")
app.mount(
    "/images",
    StaticFiles(directory=config_loader.config_path / "teachers"),
    name="images",
)

app.mount(
    "/files", StaticFiles(directory=config_loader.config_path / "files"), name="files"
)

form_renderer = FormRenderer()

table_component = TableComponent(user_storage, config_loader)

api_auth = ApiAuth(auth_storage, user_storage)
api_ejudge = ApiEjudge(auth_storage, user_storage, config_loader)
api_account = ApiAccount(auth_storage, user_storage, config_loader, form_renderer)
api_admin = ApiAdmin(auth_storage, user_storage, config_loader)
api_analytics = ApiAnalytics(auth_storage, user_storage, config_loader)
api_webutils = ApiWebutils(auth_storage, user_storage, config_loader)
api_standings = ApiStandings(user_storage, config_loader, table_component)

web_home = WebHome(auth_storage, user_storage, config_loader, form_renderer)

app.include_router(api_auth.get_router(), prefix="/api")
app.include_router(api_ejudge.get_router(), prefix="/api")
app.include_router(api_account.get_router(), prefix="/api")
app.include_router(api_admin.get_router(), prefix="/api")
app.include_router(api_analytics.get_router(), prefix="/api")
app.include_router(api_webutils.get_router(), prefix="/api")
app.include_router(api_standings.get_router(), prefix="/api")

app.include_router(web_home.get_router(), prefix="")

metrics_app = make_asgi_app()
app.mount("/api/metrics", metrics_app)

# TODO(d.a.rempel): maybe remove?
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="T-Courses",
        version="1.0.0",
        routes=app.routes,
    )
    openapi_schema["servers"] = [
        {"url": "https://t-edu.tech"},
        {"url": "http://127.0.0.1:8000"},
    ]  # 👈 custom domain here
    app.openapi_schema = openapi_schema
    return app.openapi_schema


@app.exception_handler(404)
async def custom_404_handler(request: Request, exc):
    return await web_home.web_notfound(request)


app.openapi = custom_openapi

tasks: set[Task] = set()

logger.info(f"Current time: {datetime.now()}")
