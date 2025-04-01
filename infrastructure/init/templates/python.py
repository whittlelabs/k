from application.init.k_template import KTemplateProtocol

class PythonTemplate(KTemplateProtocol):
    def get_excludes(self) -> str:
        return (
            "venv\n"
            "__pycache__\n"
            "*.pyc\n"
            ".env\n"
            ".git\n"
        )

    def get_includes(self) -> str:
        return (
            "*\n"
        )

    def get_rules(self) -> str:
        return (
            "- Write production-ready code.\n"
            "- Follow PEP8 guidelines.\n"
            "- Apply SOLID and Open/Closed principles.\n"
        )
