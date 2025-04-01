import os

from application.filesystem.protocols.clipboard import ClipboardProtocol
from application.util.project_root import find_project_root


class CopySchemaUseCase:
    """
    Use case that copies the contents of infrastructure/agency/openapi_changeset_schema.json
    to the clipboard.
    """
    def __init__(self, clipboard_service: ClipboardProtocol) -> None:
        self.clipboard_service = clipboard_service

    def execute(self) -> None:
        """
        Reads the schema file and copies its content to the clipboard.
        """
        K_PATH = os.getenv("K_PATH")
        if not K_PATH:
            print("K_PATH not set.")
            return
        schema_path = os.path.join(K_PATH, "infrastructure", "agency", "openapi_changeset_schema.json")
        if not os.path.exists(schema_path):
            print(f"Schema file not found at {schema_path}.")
            return

        with open(schema_path, "r", encoding="utf-8") as f:
            schema_content = f.read()
        
        self.clipboard_service.set(schema_content)
        print("Schema has been copied to the clipboard.")
