import asyncio
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union, cast

from google import genai
from google.genai import types
from google.genai.types import GenerateContentConfig, GoogleSearch, Tool
from PIL import Image

from delta import config

# Define types for better type hinting
T = TypeVar("T")
ImageType = Union[str, Image.Image]

SYSTEM_INSTRUCTION = (
    "You are a friendly and helpful assistant. Provide complete answers unless the user requests a concise response. "
    "Keep simple answers short. When generating code, follow best practices and include explanations when necessary. "
    "Ensure all responses are factually correct and well-structured. Respond to all non-English queries in the same language as "
    "the user's query unless instructed otherwise. For reasoning tasks, explain the thought process before giving the final answer. "
    "Maintain a professional yet approachable tone."
)

IMAGE_PROMPT = (
    "Analyze the given image and provide a brief summary of its key elements. Identify the main objects, colors, and any visible text. "
    "If people are present, mention their actions or expressions. Keep the response short and clear. "
    "Respond to all non-English queries in the same language as the user's query unless instructed otherwise."
)


def error_handler(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator to handle exceptions in async functions with consistent error messages.
    """

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> T:
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            operation = func.__name__.replace("_", " ")
            raise Exception(f"Failed to {operation}: {str(e)}") from e

    return cast(Callable[..., T], wrapper)


class GeminiAI:
    """
    Client for interacting with Google's Gemini models that supports multiple API keys.

    A class-level dictionary (`sessions`) maps a user ID to its GeminiAI instance.
    When you call get_session with a user ID, it returns the instance that was created
    with that user's API key. If a session for that user already exists, it retains the
    originally provided API key until the session is explicitly removed or recreated.
    """

    # Mapping from user_id to GeminiAI instance.
    sessions: Dict[int, "GeminiAI"] = {}

    def __init__(
        self,
        model: str = "gemini-2.0-flash",
        instruction: Optional[str] = SYSTEM_INSTRUCTION,
        api_key: Optional[str] = None,
        vertexai: bool = False,
        project: Optional[str] = None,
        location: Optional[str] = None,
        http_options: Optional[Dict[str, Any]] = None,
    ):
        # Validate authentication parameters.
        if vertexai and (not project or not location):
            raise ValueError("Project and location are required when using Vertex AI")

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
        self.api_key = api_key

    @error_handler
    async def _create_chat(self) -> None:
        """
        Create a new chat session asynchronously using the current instruction.
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
    async def send(self, message: str, tools: Optional[List[Tool]] = None) -> str:
        """
        Send a message to the Gemini model and return the text response.

        By default, if no tools are provided, this method will use the Google Search tool.
        """
        if tools is None:
            tools = [Tool(google_search=GoogleSearch())]
        cfg = GenerateContentConfig(
            system_instruction=self.instruction,
            max_output_tokens=500,
            temperature=0.1,
            tools=tools,
        )
        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=message,
            config=cfg,
        )
        return response.text

    @error_handler
    async def set_instruction(self, instruction: str) -> None:
        """
        Update the system instruction and recreate the chat session.
        """
        self.instruction = instruction
        await self._create_chat()

    @error_handler
    async def vision(
        self,
        image: ImageType,
        prompt: str = IMAGE_PROMPT,
        tools: Optional[List[Tool]] = None,
    ) -> str:
        """
        Use the Gemini Vision model to analyze an image and return a summary.
        """
        loop = asyncio.get_running_loop()
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
        Open an image file and return a copy of the image.
        """
        try:
            with Image.open(image_path) as img:
                return img.copy()
        except FileNotFoundError:
            raise FileNotFoundError(f"Image file not found: {image_path}")
        except Exception as e:
            raise ValueError(f"Failed to open image: {str(e)}")

    @classmethod
    @error_handler
    async def get_session(
        cls,
        user_id: int,
        model: str = "gemini-2.0-flash",
        instruction: str = SYSTEM_INSTRUCTION,
        api_key: Optional[str] = None,
        vertexai: bool = False,
        project: Optional[str] = None,
        location: Optional[str] = None,
        http_options: Optional[Dict[str, Any]] = None,
    ) -> "GeminiAI":
        """
        Retrieve an existing session for the given user_id or create a new one.

        If a session for the user already exists, it will return the session that was created
        with the original API key. To recreate a session (with a new API key), you must remove
        the current session first using remove_session.
        """
        if user_id in cls.sessions:
            return cls.sessions[user_id]
        else:
            new_instance = GeminiAI(
                model=model,
                instruction=instruction,
                api_key=api_key if api_key is not None else config.gemini_api_key,
                vertexai=vertexai,
                project=project,
                location=location,
                http_options=http_options,
            )
            cls.sessions[user_id] = new_instance
            return new_instance

    @classmethod
    async def remove_session(cls, user_id: int) -> bool:
        """
        Remove a user's session if it exists.
        """
        if user_id in cls.sessions:
            del cls.sessions[user_id]
            return True
        return False


gemini_chat = GeminiAI()
