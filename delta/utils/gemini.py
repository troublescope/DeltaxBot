import asyncio
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union, cast

from google import genai
from google.genai import types
from google.genai.types import GenerateContentConfig, GoogleSearch, Tool
from PIL import Image

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
    Singleton client for interacting with Google's Gemini models.
    The class is implemented as a singleton, so only one instance exists.

    Methods like get_session return the same instance.
    """

    _instance: Optional["GeminiAI"] = None

    def __new__(cls, *args: Any, **kwargs: Any) -> "GeminiAI":
        if cls._instance is None:
            cls._instance = super(GeminiAI, cls).__new__(cls)
        return cls._instance

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
        # Avoid reinitializing if already initialized.
        if hasattr(self, "_initialized") and self._initialized:
            return

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
        self._initialized = True

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
        By default, if no tools are provided, the send method will use the Google Search tool.
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

    @error_handler
    async def get_session(
        self,
        user_id: int,
        api_key: Optional[str] = None,
        vertexai: bool = False,
        project: Optional[str] = None,
        location: Optional[str] = None,
        http_options: Optional[Dict[str, Any]] = None,
    ) -> "GeminiAI":
        """
        Return the singleton instance.
        In a singleton design, get_session simply returns self.
        """
        # If needed, you could update settings here if not already set.
        return self


# Create or retrieve the singleton instance:
gemini_chat = GeminiAI()
