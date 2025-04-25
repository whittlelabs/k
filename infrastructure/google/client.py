from typing import List, Dict, Any

from google import genai

from application.agency.protocols.llm_client import LLMClientProtocol


class GoogleClient(LLMClientProtocol):
    model: str = "gemini-1.5-pro"

    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        
    def get_models(self) -> List[Dict[str, Any]]:
        """Get a list of available Google Gemini models."""
        # Use the official API method to list models
        models = self.client.models.list()
        # Format the response to match the expected output format
        return [{"id": model.name, "name": model.display_name} 
                for model in models
                if "gemini" in model.name.lower()]

    def chat(self, model: str, prompt: str) -> str:
        """Send a chat message to the specified model."""
        response = self.client.models.generate_content(
            model=model,
            contents=prompt
        )
        return response.text