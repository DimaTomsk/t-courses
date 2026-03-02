from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.requests import Request
from loguru import logger
from starlette.responses import HTMLResponse, RedirectResponse
from typing_extensions import Annotated

from app.common import JinjaTemplate
from app.engine.auth_storage import AuthStorage
from app.engine.config_loader import ConfigLoader
from app.engine.renderer import CourseRenderer
from app.forms.form_renderer import FormRenderer
from app.models.config import Course, Page, Contest
from app.routers.authenticator import UserSession
from app.storage.user_storage import UserStorage

UI_VERSION = "20"


class WebHome:
    def __init__(
        self,
        auth_storage: AuthStorage,
        user_storage: UserStorage,
        config_loader: ConfigLoader,
        form_renderer: FormRenderer,
    ):
        self._config_loader = config_loader
        self.course_renderer = CourseRenderer(config_loader)

        self._router = APIRouter(prefix="", tags=["web"])

        self._form_renderer = form_renderer

        self._auth_storage = auth_storage
        self._user_storage = user_storage
        self.templates = JinjaTemplate(directory="resources/templates")
        self._router.add_api_route(
            "/",
            self.web_home,
            methods=["GET"],
            name="web.home",
        )
        self._router.add_api_route(
            "/pages/{page_name}",
            self.web_page,
            methods=["GET"],
            name="web.page",
        )
        self._router.add_api_route(
            "/registration",
            lambda: RedirectResponse(url="/"),
            methods=["GET"],
            name="web.old_register",
            deprecated=True,
        )
        self._router.add_api_route(
            "/courses/{course_name}",
            self.web_course,
            methods=["GET"],
            name="web.course",
        )
        self._router.add_api_route(
            "/courses/{course_name}/contest/{contest_id}",
            self.web_contest,
            methods=["GET"],
            name="web.contest",
        )
        self._router.add_api_route(
            "/courses/{course_name}/standings/{table_name}",
            self.web_standings,
            methods=["GET"],
            name="web.standings",
        )
        # self._router.add_api_route(
        #     "/standings/{name}",
        #     self.web_standings,
        #     methods=["GET"],
        #     name="web.standings",
        # )

    def get_router(self):
        return self._router

    async def web_home(
        self,
        request: Request,
        user_session: Annotated[UserSession, Depends()],
    ) -> HTMLResponse:
        return await self.web_page("home", request, user_session)

    async def web_page(
        self,
        page_name: str,
        request: Request,
        user_session: Annotated[UserSession, Depends()],
    ) -> HTMLResponse:
        config = self._config_loader.get_config()

        if page_name not in config.pages:
            raise HTTPException(status_code=404)

        page: Page = config.pages[page_name]
        #
        # courses = []
        # for course in config.main_page_config.visible_courses:
        #     course_config = config.course_config[course]
        #     courses.append({"name": course_config.title, "url": course})
        #     if user_session.user is not None:
        #         if (
        #             len(
        #                 course_config.get_contests_by_tags(user_session.user.get_tags())
        #             )
        #             > 0
        #         ):
        #             courses[-1]["style"] = "border-left-color: #FFDD2D"

        response = self.templates.TemplateResponse(
            name="course_template.j2",
            request=request,
            context={
                "title": page.title,
                "teachers": [],
                "lessons": [],
                "links": page.links,
                "courses": page.items,
                "location": "/",
                "user": user_session.user,
                "forms": config.forms_config,
                "renderer": self.course_renderer,
                "form_renderer": self._form_renderer,
                "ui_version": UI_VERSION,
            },
        )
        return user_session.update_cookie(response)

    async def web_course(
        self,
        course_name: str,
        request: Request,
        user_session: Annotated[UserSession, Depends()],
    ) -> HTMLResponse:
        logger.info(f"Received request for course {course_name}")

        config = self._config_loader.get_config()

        if course_name not in config.course_config:
            raise HTTPException(status_code=404)

        course: Course = config.course_config[course_name]

        join_buttons = []

        user_tags = []
        if user_session.user is not None:
            user_tags = user_session.user.get_tags()

        if user_session.user is not None:
            for button in course.join_buttons:
                if button.tag not in user_tags:
                    join_buttons.append(button)

        def check_contest_access(contest: Contest) -> bool:
            if user_session.user is None:
                return False
            return contest.tag in user_tags

        # TODO: check user's deadline here
        def deadline_for(contest: Contest) -> Optional[str]:
            if contest.deadline.absolute == datetime.max:
                return None
            return f"Дедлайн: {contest.deadline.absolute.strftime('%d.%m.%Y %H:%M')}"

        response = self.templates.TemplateResponse(
            name="course_template.j2",
            request=request,
            context={
                "title": course.title,
                "course_name": course_name,
                "teachers": course.teachers,
                "check_contest_access": check_contest_access,
                "deadline_for": deadline_for,
                "lessons": course.lessons,
                "links": course.links,
                "location": f"/courses/{course_name}",
                "user": user_session.user,
                "join_buttons": join_buttons,
                "statement_exists": self.course_renderer.statement_path,
                "parse_vk_params": self.course_renderer.parse_vk_params,
                "parse_yt_params": self.course_renderer.parse_yt_params,
                "forms": config.forms_config,
                "renderer": self.course_renderer,
                "form_renderer": self._form_renderer,
                "ui_version": UI_VERSION,
            },
        )

        return user_session.update_cookie(response)

    async def web_standings(
        self,
        course_name: str,
        table_name: str,
        request: Request,
        user_session: Annotated[UserSession, Depends()],
    ) -> HTMLResponse:
        config = self._config_loader.get_config()
        if course_name not in config.course_config:
            raise HTTPException(status_code=404)
        course: Course = config.course_config[course_name]
        if course.get_contests_for_table(table_name) is None:
            raise HTTPException(status_code=404)

        response = self.templates.TemplateResponse(
            name="standings.j2",
            request=request,
            context={
                "title": "Табличка",
                "user": user_session.user,
                "statement_exists": self.course_renderer.statement_path,
                "parse_vk_params": self.course_renderer.parse_vk_params,
                "parse_yt_params": self.course_renderer.parse_yt_params,
                "forms": config.forms_config,
                "renderer": self.course_renderer,
                "form_renderer": self._form_renderer,
                "ui_version": UI_VERSION,
            },
        )
        return user_session.update_cookie(response)

    async def web_contest(
        self,
        course_name: str,
        contest_id: str,
        user_session: Annotated[UserSession, Depends()],
        request: Request,
    ) -> HTMLResponse:
        try:
            contest_id = int(contest_id)
        except ValueError:
            raise HTTPException(status_code=404)
        if user_session.user is None:
            return RedirectResponse(url=f"/courses/{course_name}", status_code=302)
        config = self._config_loader.get_config()
        if course_name not in config.course_config:
            raise HTTPException(status_code=404)

        contests_by_tags = config.course_config[course_name].get_contests_by_tags(
            user_session.user.get_tags()
        )
        if contest_id not in contests_by_tags:
            return RedirectResponse(url=f"/courses/{course_name}", status_code=302)

        response = self.templates.TemplateResponse(
            name="contest.j2",
            request=request,
            context={
                "title": "Контест",
                "user": user_session.user,
                "forms": config.forms_config,
                "form_renderer": self._form_renderer,
                "contest_url": f"/api/ejudge/login/{course_name}/{contest_id}",
                "ui_version": UI_VERSION,
            },
        )
        return user_session.update_cookie(response)

    async def web_notfound(self, request: Request) -> HTMLResponse:
        archive_url = request.url.replace(scheme="https", netloc="old.algocourses.ru")
        return self.templates.TemplateResponse(
            name="notfound.j2",
            context={"archive_url": archive_url},
            request=request,
            status_code=404,
        )
