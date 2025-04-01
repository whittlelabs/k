from application.init.k_template import KTemplateProtocol

class NodeJSTemplate(KTemplateProtocol):
    def get_excludes(self) -> str:
        return (
            "node_modules\n"
            "dist\n"
            "build\n"
            ".env\n"
            ".git\n"
            ".k\n"
        )

    def get_includes(self) -> str:
        return (
            "*\n"
        )

    def get_rules(self) -> str:
        return (
            "- Follow JavaScript best practices.\n"
            "- Use ESLint and Prettier for code quality.\n"
            "- Keep dependencies up to date.\n"
        )
