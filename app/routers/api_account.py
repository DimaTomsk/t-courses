from typing import Annotated, Any

from fastapi import APIRouter, Depends
from starlette.requests import Request

from app.engine.auth_storage import AuthStorage
from app.engine.config_loader import ConfigLoader
from app.engine.mail_sender import send_email
from app.forms.form_renderer import FormRenderer
from app.forms.form_response import FormResponse
from app.models.account import BaseAccountInfo, ResetAccountData
from app.routers.authenticator import verify_captcha, UserSession
from app.storage.keyval import JoinKeyVal, DictKeyVal
from app.storage.user_storage import UserStorage


class ApiAccount:
    def __init__(
        self,
        auth_storage: AuthStorage,
        user_storage: UserStorage,
        config_loader: ConfigLoader,
        form_renderer: FormRenderer,
    ):
        self._router = APIRouter(prefix="/account", tags=["account"])

        self._auth_storage = auth_storage
        self._user_storage = user_storage
        self._config_loader = config_loader
        self._form_renderer = form_renderer

        self._router.add_api_route(
            "/register",
            self.register,
            methods=["POST"],
            name="account.register",
            dependencies=[Depends(verify_captcha)],
        )
        self._router.add_api_route(
            "/reset",
            self.reset,
            methods=["POST"],
            name="account.reset",
            dependencies=[Depends(verify_captcha)],
        )

        self._router.add_api_route(
            "/join/{tag}",
            self.join_tag,
            methods=["POST"],
            name="account.join_tag",
        )

    def get_router(self):
        return self._router

    async def join_tag(
        self,
        data: dict[str, Any],
        user_session: Annotated[UserSession, Depends()],
        tag: str,
    ):
        if user_session.user is None:
            return FormResponse(success=False, detail="Вы не авторизованы", reload=True)

        forms = self._config_loader.get_config().forms_config
        new_user = JoinKeyVal([DictKeyVal(data), user_session.user])

        deps = self._form_renderer.get_path_for(user_session.user, forms, f"tags/{tag}")
        new_fields = self._form_renderer.get_data_to_store(new_user, deps, forms)
        if new_fields is None:
            return FormResponse(
                success=False,
                detail="Что-то пошло не так. Попробуйте перезагрузить страницу или напишите в поддержку",
            )
        if len(new_fields) > 0:
            user_session.user.push_fields(new_fields)
        user_session.user.push_tag(tag)
        return FormResponse(success=True, reload=True)

    async def register(
        self,
        data: BaseAccountInfo,
        request: Request,
    ) -> FormResponse:
        if data.email in self._user_storage.user_by_email:
            return FormResponse(
                success=False,
                detail='Пользователь с таким email уже зарегистрирован. Если вы забыли логин или пароль, восстановите их, нажав "Забыли пароль?"',
            )

        user = await self._user_storage.create_new_user(
            data, request.app.state.mysql_pool
        )
        await send_email(user.get_email(), user.get_login(), user.get_password())
        return FormResponse(
            success=True,
            reload=False,
            reset_form=False,
            detail=f'Логин и пароль были отправлены на почту {data.email}. Если не можете найти письмо, проверьте спам или запросите данные для входа ещё раз, нажав "Забыли пароль?"',
        )

    async def reset(
        self,
        data: ResetAccountData,
    ) -> FormResponse:
        user = self._user_storage.get_user_by_email(data.email)

        if user is None:
            return FormResponse(
                success=False, detail="Пользователь с таким email не найден"
            )

        await send_email(user.get_email(), user.get_login(), user.get_password())
        return FormResponse(
            success=True,
            detail=f"Логин и пароль были отправлены на почту {data.email}. Если не можете найти письмо, проверьте спам",
        )
