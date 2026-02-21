from typing import Optional

from markdown_it import MarkdownIt

from app.common import JinjaTemplate
from app.forms.form import Form
from app.storage.user import User, KeyVal


class FormRenderer:
    def __init__(self):
        self.templates = JinjaTemplate("resources/templates")

    def render(self, form: Form) -> str:
        assert isinstance(form, Form)
        return self.templates.get_template("forms/form.j2").render(
            form=form, renderer=self
        )

    def resolve_dependencies(self, forms: dict[str, Form], form: str) -> list[str]:
        result = []
        used = set()

        def dfs(cur):
            assert cur in forms, f"Form '{cur}' not found"
            if cur in used:
                return
            used.add(cur)
            for dep in sorted(forms[cur].depends):
                dfs(dep)
            result.append(cur)

        dfs(form)

        return result

    def get_path_for(
        self, data: Optional[KeyVal], forms: dict[str, Form], form: str
    ) -> list:
        deps = self.resolve_dependencies(forms, form)
        if data is None:
            return deps
        bad_forms = []
        for dep in deps:
            check = forms[dep].check_for(data)
            if check is None:
                bad_forms.append(dep)
        return bad_forms

    def get_data_to_store(
        self, data: KeyVal, deps: list[str], forms: dict[str, Form]
    ) -> Optional[dict]:
        result = {}
        for dep in deps:
            check = forms[dep].check_for(data)
            if check is None:
                return None
            result |= check
        return result

    def button_for(
        self,
        forms: dict[str, Form],
        form: str,
        *,
        title: Optional[str] = None,
        user: Optional[User] = None,
        path: Optional[str] = None,
    ):
        deps = self.get_path_for(user, forms, form)

        head_form = forms[form]

        return self.templates.get_template("forms/button.j2").render(
            forms_list=deps,
            path=path if path is not None else head_form.path,
            title=head_form.title if title is None else title,
            form_name=form,
        )

    @classmethod
    def render_label(cls, text: str) -> str:
        md = MarkdownIt()
        default_render = md.renderer.rules.get("link_open")

        def render_link_open(renderer, tokens, idx, options, env):
            token = tokens[idx]
            token.attrSet("target", "_blank")
            token.attrSet("@click.stop", "")

            # Call default renderer properly
            if default_render:
                return default_render(renderer, tokens, idx, options, env)
            return renderer.renderToken(tokens, idx, options, env)

        # Bind the method properly so "self" works
        md.renderer.rules["link_open"] = render_link_open.__get__(
            md.renderer, type(md.renderer)
        )
        return md.renderInline(text)
