import asyncio
from typing import Any, Dict, Optional

from google import genai
from google.genai import types

from delta import config

# Define system instruction as a global constant
SYSTEM_INSTRUCTION = """You are a friendly and helpful assistant.
Ensure your answers are complete, unless the user requests a more concise approach.
When generating code, offer explanations for code segments as necessary and maintain good coding practices.
When presented with inquiries seeking information, provide answers that reflect a deep understanding of the field, guaranteeing their correctness.
For simple queries make an simple answer too.
For any non-english queries, respond in the same language as the prompt unless otherwise specified by the user.
For prompts involving reasoning, provide a clear explanation of each step in the reasoning process before presenting the final answer."""


class GeminiAIChat:
    """
    Asynchronous client for interacting with Google's Gemini models.

    Provides a simple interface for sending messages to Gemini models
    with support for both API key authentication and Vertex AI integration.
    """

    def __init__(
        self,
        model: str,
        instruction: Optional[str] = None,
        api_key: Optional[str] = None,
        vertexai: bool = False,
        project: Optional[str] = None,
        location: Optional[str] = None,
        http_options: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize an asynchronous Gemini chat client.

        Args:
            model: The Gemini model identifier to use (e.g., "gemini-1.5-flash")
            instruction: Optional system instruction to guide model behavior
            api_key: Google API key for direct Gemini API access
            vertexai: Whether to use Vertex AI (True) or direct API access (False)
            project: Google Cloud project ID (required if vertexai=True)
            location: Google Cloud region (required if vertexai=True)
            http_options: Additional HTTP options for the client

        Raises:
            ValueError: If vertexai is True but project or location is missing
        """
        if vertexai and (not project or not location):
            raise ValueError("Project and location are required when using Vertex AI")

        if not vertexai and not api_key:
            raise ValueError("API key is required when not using Vertex AI")

        if vertexai:
            self.client = genai.Client(
                vertexai=True,
                project=project,
                location=location,
                http_options=http_options,
            )
        else:
            self.client = genai.Client(api_key=api_key, http_options=http_options)

        self.model = model
        self.instruction = instruction
        self.chat = None
        # Create the chat session synchronously during initialization
        self._create_chat()

    def _create_chat(self) -> None:
        """
        Create a new chat session with the specified configuration synchronously.

        Raises:
            Exception: If chat initialization fails
        """
        try:
            cfg = (
                types.GenerateContentConfig(system_instruction=self.instruction)
                if self.instruction
                else None
            )
            # Use the synchronous API instead of the async one
            self.chat = self.client.chats.create(model=self.model, config=cfg)
        except Exception as e:
            raise Exception(f"Failed to initialize chat: {str(e)}")

    async def send(self, message: str) -> str:
        """
        Send a message and return the model's response.

        Args:
            message: The text message to send to the model

        Returns:
            The text response from the model

        Raises:
            Exception: If sending the message fails
        """
        try:
            if not self.chat:
                self._create_chat()

            # Use loop.run_in_executor to run the blocking send_message in a thread pool
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, lambda: self.chat.send_message(message)
            )
            return response.text
        except Exception as e:
            raise Exception(f"Failed to send message: {str(e)}")

    async def set_instruction(self, instruction: str) -> None:
        """
        Update the system instruction and reinitialize the chat session.

        Args:
            instruction: The new system instruction to use

        Raises:
            Exception: If updating the instruction fails
        """
        try:
            self.instruction = instruction
            self._create_chat()
        except Exception as e:
            raise Exception(f"Failed to update instruction: {str(e)}")


class ChatManager:
    """
    Manager for handling multiple user chat sessions.
    """

    def __init__(self):
        """Initialize an empty dictionary of user chat sessions."""
        self.user_chats: Dict[int, GeminiAIChat] = {}

    async def get_chat(
        self,
        user_id: int,
        model: str = "gemini-1.5-flash",
        instruction: str = SYSTEM_INSTRUCTION,
        api_key: Optional[str] = None,
        vertexai: bool = False,
        project: Optional[str] = None,
        location: Optional[str] = None,
    ) -> GeminiAIChat:
        """
        Get or create a chat session for a specific user.

        Args:
            user_id: Unique identifier for the user
            model: The Gemini model to use
            instruction: Default system instruction
            api_key: Google API key
            vertexai: Whether to use Vertex AI
            project: Google Cloud project ID
            location: Google Cloud region

        Returns:
            An GeminiAIChat instance for the specified user

        Raises:
            ValueError: If required authentication parameters are missing
        """
        if user_id not in self.user_chats:
            # Use config.gemini_api_key if api_key is not provided
            if api_key is None:
                api_key = config.gemini_api_key

            if not api_key and not (vertexai and project and location):
                raise ValueError(
                    "Either API key or Vertex AI credentials must be provided"
                )

            self.user_chats[user_id] = GeminiAIChat(
                model=model,
                instruction=instruction,
                api_key=api_key,
                vertexai=vertexai,
                project=project,
                location=location,
            )

        return self.user_chats[user_id]

    async def remove_chat(self, user_id: int) -> bool:
        """
        Remove a user's chat session.

        Args:
            user_id: Unique identifier for the user

        Returns:
            True if the session was removed, False if it didn't exist
        """
        if user_id in self.user_chats:
            del self.user_chats[user_id]
            return True
        return False


gemini_chat = ChatManager()
