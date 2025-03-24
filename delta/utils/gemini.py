import asyncio
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union, cast

from google import genai
from google.genai import types
from PIL import Image

from delta import config

# Define types for better type hinting
T = TypeVar("T")
ImageType = Union[str, Image.Image]

# Define system instruction as a global constant
SYSTEM_INSTRUCTION = """You are a friendly and helpful assistant.
Provide complete answers unless the user requests a concise response. Keep simple answers short.
When generating code, follow best practices and include explanations when necessary.
Ensure all responses are factually correct and well-structured.
Respond to all non-English queries in the same language as the user's query unless instructed otherwise.
For reasoning tasks, explain the thought process before giving the final answer.
Maintain a professional yet approachable tone."""

IMAGE_PROMPT = """Analyze the given image and provide a brief summary of its key elements.
Identify the main objects, colors, and any visible text.
If people are present, mention their actions or expressions.
Keep the response short and clear.
Respond to all non-English queries in the same language as the user's query unless instructed otherwise."""


def error_handler(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator to handle exceptions in async functions with consistent error messages.

    Args:
        func: The async function to wrap with error handling.

    Returns:
        Wrapped function with error handling.
    """

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> T:
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            operation = func.__name__.replace("_", " ")
            raise Exception(f"Failed to {operation}: {str(e)}") from e

    return cast(Callable[..., T], wrapper)


class GeminiAIChat:
    """
    Asynchronous client for interacting with Google's Gemini models.

    Provides a simple interface for sending messages to Gemini models
    with support for both API key authentication and Vertex AI integration.

    Attributes:
        model (str): The Gemini model name to use for generating content.
        instruction (Optional[str]): The system instruction to guide model behavior.
        client (genai.Client): The Google GenAI client instance.
        chat (Optional[Any]): The active chat session.
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
        Initialize the Gemini AI chat client.

        Args:
            model: The Gemini model name to use.
            instruction: Optional system instruction to guide model behavior.
            api_key: Google API key for authentication.
            vertexai: Whether to use Vertex AI instead of direct API access.
            project: Google Cloud project ID (required for Vertex AI).
            location: Google Cloud region (required for Vertex AI).
            http_options: Additional HTTP options for the client.

        Raises:
            ValueError: If authentication parameters are incomplete.
        """
        # Validate authentication parameters
        if vertexai and (not project or not location):
            raise ValueError("Project and location are required when using Vertex AI")
        if not vertexai and not api_key:
            raise ValueError("API key is required when not using Vertex AI")

        # Initialize client based on authentication method
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

    @error_handler
    async def _create_chat(self) -> None:
        """
        Create a new chat session asynchronously with the specified configuration.
        """
        cfg = (
            types.GenerateContentConfig(
                system_instruction=self.instruction,
                max_output_tokens=500,
                temperature=0.1,
            )
            if self.instruction
            else None
        )
        self.chat = self.client.aio.chats.create(model=self.model, config=cfg)

    @error_handler
    async def send(self, message: str) -> str:
        """
        Send a message and return the model's response asynchronously.

        Args:
            message: Text message to send to the model.

        Returns:
            Text response from the model.
        """
        if not self.chat:
            await self._create_chat()
        response = await self.chat.send_message(message)
        return response.text

    @error_handler
    async def set_instruction(self, instruction: str) -> None:
        """
        Update the system instruction and recreate the chat session asynchronously.

        Args:
            instruction: The new system instruction.
        """
        self.instruction = instruction
        await self._create_chat()

    @error_handler
    async def vision(
        self,
        image: ImageType,
        prompt: str = IMAGE_PROMPT,
        tools: Optional[List[Callable]] = None,
    ) -> str:
        """
        Generate content using the Gemini Vision model with an image input.

        Args:
            image: Either a path to an image file or a PIL Image object.
            prompt: The text prompt to accompany the image (defaults to IMAGE_PROMPT).
            tools: Optional list of tools to use with the model.

        Returns:
            Text response from the model based on the image analysis.
        """
        loop = asyncio.get_running_loop()

        # Handle different image input types
        image_obj = image
        if isinstance(image, str):
            image_obj = await loop.run_in_executor(None, self._open_image, image)

        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=[prompt, image_obj],
        )
        return response.text

    def _open_image(self, image_path: str) -> Image.Image:
        """
        Open an image using Pillow and return a copy of the image instance.

        Args:
            image_path: Path to the image file.

        Returns:
            A PIL Image object.

        Raises:
            FileNotFoundError: If the image file doesn't exist.
            PIL.UnidentifiedImageError: If the file is not a valid image.
        """
        try:
            with Image.open(image_path) as img:
                return img.copy()
        except FileNotFoundError:
            raise FileNotFoundError(f"Image file not found: {image_path}")
        except Exception as e:
            raise ValueError(f"Failed to open image: {str(e)}")


class ChatManager:
    """
    Manager for handling user chat sessions.

    Maintains a dictionary of chat sessions indexed by user ID and provides
    methods to create, retrieve, and remove chat sessions.

    Attributes:
        user_chats (Dict[int, GeminiAIChat]): Dictionary mapping user IDs to chat sessions.
    """

    def __init__(self):
        """Initialize an empty dictionary for user chat sessions."""
        self.user_chats: Dict[int, GeminiAIChat] = {}

    @error_handler
    async def get_chat(
        self,
        user_id: int,
        model: str = "gemini-2.0-flash",
        instruction: str = SYSTEM_INSTRUCTION,
        api_key: Optional[str] = None,
        vertexai: bool = False,
        project: Optional[str] = None,
        location: Optional[str] = None,
        http_options: Optional[Dict[str, Any]] = None,
    ) -> GeminiAIChat:
        """
        Get or create a chat session for a specific user.

        Args:
            user_id: Unique identifier for the user.
            model: Gemini model to use.
            instruction: Default system instruction.
            api_key: Google API key.
            vertexai: Whether to use Vertex AI.
            project: Google Cloud project ID.
            location: Google Cloud region.
            http_options: Additional HTTP options for the client.

        Returns:
            GeminiAIChat instance for the specified user.

        Raises:
            ValueError: If authentication parameters are incomplete.
        """
        if user_id not in self.user_chats:
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
                http_options=http_options,
            )

        return self.user_chats[user_id]

    async def remove_chat(self, user_id: int) -> bool:
        """
        Remove a user's chat session.

        Args:
            user_id: Unique identifier for the user.

        Returns:
            True if the session was removed, False if it didn't exist.
        """
        if user_id in self.user_chats:
            del self.user_chats[user_id]
            return True
        return False


# Create a singleton instance of the ChatManager
gemini_chat = ChatManager()
