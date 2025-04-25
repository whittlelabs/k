import os
from typing import List, Optional
from langchain.chat_models import init_chat_model
from langchain.schema import SystemMessage, HumanMessage
from langchain_community.chat_message_histories import FileChatMessageHistory
from langchain.memory import ConversationBufferMemory

from application.agency.protocols.workflow_node import WorkflowNodeProtocol
from application.filesystem.protocols.clipboard import ClipboardProtocol


class GenerateCodeAdvice(WorkflowNodeProtocol):
    """
    Workflow node that generates code advice using langchain's chat model
    with file-based chat history and conversation buffer memory.
    Always records conversation memory; retrieves prior messages only when followup mode is enabled.
    """
    def __init__(self, clipboard: ClipboardProtocol, model_id: str, model_config: dict = None) -> None:
        self.chat_model = init_chat_model(model_id, **(model_config or {}))
        self.clipboard = clipboard

    def __call__(self, state: dict) -> dict:
        if "prompt" not in state:
            raise ValueError("Prompt not found in state.")

        project_path = state.get("project_path")
        followup = state.get("followup", False)

        memory: Optional[ConversationBufferMemory] = None
        prior_messages: List = []

        # Setup file-based chat history and memory
        if project_path:
            history_path = os.path.join(project_path, ".k", "advice_history.json")
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

        # Human message with prompt and context
        human_content = self._human_message(state)
        messages.append(HumanMessage(content=human_content))

        # Handle prompt copying mode
        if state.get("copy_prompt", False):
            combined_prompt = self._system_message() + "\n\n" + human_content
            try:
                self.clipboard.set(combined_prompt)
                print("Code Advice prompt copied to clipboard. No LLM invocation performed.")
            except Exception as e:
                print(f"Failed to copy prompt to clipboard: {e}")
            return {"advice": None, "progress": "Prompt copied to clipboard."}

        print("\nGenerating advice. This may take a minute...\n")
        # Invoke the chat model
        response = self.chat_model.invoke(messages)
        advice = response.content
        print(f"{advice}\n")

        # Persist conversation memory
        if memory:
            memory.save_context({"input": human_content}, {"output": advice})

        return {"advice": advice, "progress": "Advice generated."}

    def _system_message(self) -> str:
        """
        Returns the fixed system instruction for code advice generation.
        """
        return (
            "You are a highly skilled software architect who excels at advising and growing expert engineers. "
            "Provide detailed advice in response to the prompt. If this is a followup to a previous prompt, "
            "you will find additional context in the chat history."
        )

    def _human_message(self, state: dict) -> str:
        """
        Formats the human message with prompt, directory tree, and source code.
        """
        parts = [f"PROMPT: {state['prompt']}"]
        if "directory_tree" in state:
            parts.append(f"\nDirectory Tree:\n{state['directory_tree']}")
        if "source_code" in state:
            parts.append(f"\nSource Code:\n{state['source_code']}")
        return "\n".join(parts)
