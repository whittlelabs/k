import json
import os

from langchain_community.chat_message_histories import FileChatMessageHistory
from langchain.memory import ConversationBufferMemory

from application.agency.protocols.workflow_node import WorkflowNodeProtocol


class RecordChangeset(WorkflowNodeProtocol):
    """
    Workflow node that records the prompt and changeset response to a chat history JSON file specific to changesets.
    It writes to 'changeset_history.json' in the .k directory, overwriting on fresh runs and appending on follow-ups.
    """
    def __call__(self, state: dict) -> dict:
        # Skip recording when the prompt is copied rather than sent to the LLM
        if state.get("copy_prompt"):
            return {"progress": "Changeset memory recording skipped."}

        project_path = state.get("project_path")
        if not project_path:
            raise ValueError("project_path is required in state to record changeset memory")

        prompt = state.get("prompt")
        if prompt is None:
            raise ValueError("Changeset memory requires 'prompt' in state to record changeset memory")

        response = state.get("changeset")
        if response is None:
            raise ValueError("Changeset memory requires 'changeset' in state to record changeset memory")

        history_filename = "changeset_history.json"
        history_path = os.path.join(project_path, ".k", history_filename)

        # Serialize the changeset response to JSON if possible
        try:
            output = response.json()
        except Exception:
            output = json.dumps(response, default=str)

        followup = state.get("followup", False)
        # On fresh runs (no follow-up), clear existing history
        if not followup and os.path.exists(history_path):
            try:
                os.remove(history_path)
            except Exception:
                pass

        # Record the new prompt/response pair
        file_history = FileChatMessageHistory(file_path=history_path)
        memory = ConversationBufferMemory(chat_memory=file_history, return_messages=False)
        memory.save_context({"input": prompt}, {"output": output})

        return {"progress": "Changeset memory recorded."}
