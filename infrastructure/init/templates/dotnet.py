from application.init.k_template import KTemplateProtocol

class DotNetTemplate(KTemplateProtocol):
    def get_excludes(self) -> str:
        return (
            "bin\n"
            "obj\n"
            ".vs\n"
            "packages\n"
            ".git\n"
            ".k\n"
        )

    def get_includes(self) -> str:
        return (
            "*"
        )

    def get_rules(self) -> str:
        return (
            "- Write production-ready code.\n"
            "- Follow established coding conventions.\n"
            "- Maintain proper project structure.\n"
            "- Apply SOLID and Open/Closed principles.\n"
        )
