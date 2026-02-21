#
# if hasattr(jinja2, "pass_context"):
#     pass_context = jinja2.pass_context
# else:
#     pass_context = jinja2.contextfunction
#
#
# @pass_context
# def https_url_for(context: dict, name: str, **path_params) -> str:
#     request = context["request"]
#     http_url = request.url_for(name, **path_params)
#     return str(http_url).replace("http", "https", 1)
#
# templates.env.globals["url_for"] = https_url_for


from fastapi.templating import Jinja2Templates
from jinja2 import pass_context
from starlette.requests import Request


@pass_context
def url_for_path(ctx, name: str, **params) -> str:
    request: Request = ctx["request"]
    return request.app.url_path_for(name, **params)


class JinjaTemplate(Jinja2Templates):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.env.globals["url_for"] = url_for_path

