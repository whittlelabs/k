from application.init.k_template import KTemplateProtocol

class WikiTemplate(KTemplateProtocol):
    def get_excludes(self) -> str:
        return (
            ".git\n"
            ".k\n"
        )

    def get_includes(self) -> str:
        return (
            "*\n"
        )

    def get_rules(self) -> str:
        return (
            "- Pay attention to existing style conventions and try to keep it consistent.\n"
        )
