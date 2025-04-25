import os
from typing import List, Optional
from pydantic import BaseModel, Field
from langchain.chat_models import init_chat_model
from langchain.schema import SystemMessage, HumanMessage
from langchain_community.chat_message_histories import FileChatMessageHistory
from langchain.memory import ConversationBufferMemory

from application.agency.protocols.workflow_node import WorkflowNodeProtocol
from application.filesystem.protocols.clipboard import ClipboardProtocol


class FileChange(BaseModel):
    path: str = Field(description="Relative path to the file within the project.")
    content: str = Field(description="Content of the file. Include the ENTIRE file content, not just the changes. Don't forget imports, etc.")


class Changeset(BaseModel):
    summary: str = Field(description="Descriptive summary of files added, removed, or modified. Explain what was done and why in one sentence for each file.")
    additions: List[FileChange] = Field(description="List of files added.")
    removals: List[FileChange] = Field(description="List of files removed.")
    modifications: List[FileChange] = Field(description="List of files modified.")


class GenerateChangeset(WorkflowNodeProtocol):
    """
    Workflow node that generates a pull request changeset using langchain's chat model
    with file-based chat history and conversation buffer memory.
    Always records conversation memory; retrieves prior messages only when followup mode is enabled.
    """
    def __init__(self, clipboard: ClipboardProtocol, model_id: str, model_config: dict = None) -> None:
        self.chat_model = init_chat_model(model_id, **(model_config or {}))
        self.clipboard = clipboard

    def __call__(self, state: dict) -> dict:
        if "prompt" not in state:
            raise ValueError("Goal not found in state.")
        
        project_path = state.get("project_path")
        followup = state.get("followup", False)

        memory: Optional[ConversationBufferMemory] = None
        prior_messages: List = []

        # Setup file-based chat history and memory
        if project_path:
            history_path = os.path.join(project_path, ".k", "changeset_history.json")
            # Clear existing history if not followup to start fresh
            if not followup and os.path.exists(history_path):
                try:
                    os.remove(history_path)
                except Exception:
                    pass
            file_history = FileChatMessageHistory(file_path=history_path)
            memory = ConversationBufferMemory(
                chat_memory=file_history,
                return_messages=False
            )
            # Only retrieve prior messages when followup mode is enabled
            if followup:
                prior_messages = file_history.messages

        # Build the message sequence
        messages: List = []
        if not prior_messages:
            messages.append(SystemMessage(content=self._system_message()))
        else:
            messages.extend(prior_messages)

        # Human message with goal and context
        human_content = self._human_message(state)
        messages.append(HumanMessage(content=human_content))

        # Handle prompt copying mode
        if state.get("copy_prompt", False):
            combined_prompt = self._system_message() + "\n\n" + human_content
            try:
                self.clipboard.set(combined_prompt)
                print("\nPR prompt copied to clipboard. No LLM invocation performed.\n")
            except Exception as e:
                print(f"Failed to copy prompt to clipboard: {e}")
            return {"changeset": None, "progress": "PR prompt copied to clipboard."}

        # Invoke the chat model with structured output
        structured_llm = self.chat_model.with_structured_output(Changeset)
        print("\nGenerating changeset. This may take a minute...\n")
        response = structured_llm.invoke(messages)

        # Display summary
        print(f"{response.summary}\n")

        # Persist conversation memory
        if memory:
            memory.save_context({"input": human_content}, {"output": response.json()})

        return {"changeset": response, "progress": "Changeset generated."}

    def _system_message(self) -> str:
        """
        Returns the fixed system instruction for changeset generation.
        """
        return (
            "You are a highly skilled software engineering agent assisting with generating pull requests "
            "for a project. Respond using the structured response to indicate which files should be added, removed, "
            "or modified in order to accomplish the stated goal. Include the FULL CONTENT of every file to be created "
            "or modified. DO NOT RETURN PARTIAL FILE CONTENT. This content will be used to fully replace existing content, "
            "overwriting it entirely. Favor completeness over simplicity in your responses. The changes are expected to "
            "work out of the box without further modification."
        )

    def _human_message(self, state: dict) -> str:
        """
        Formats the human message with goal, rules, directory tree, and source code.
        """
        parts = [f"GOAL: {state['prompt']}"]
        if "project_rules" in state and state["project_rules"]:
            parts.append(f"Project Rules:\n{state['project_rules']}")
        if "directory_tree" in state:
            parts.append(f"Directory Tree:\n{state['directory_tree']}")
        if "source_code" in state:
            parts.append(f"Source Code:\n{state['source_code']}")
        return "\n\n".join(parts)
