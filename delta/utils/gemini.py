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
    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> T:
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            operation = func.__name__.replace("_", " ")
            raise Exception(f"Failed to {operation}: {str(e)}") from e

    return cast(Callable[..., T], wrapper)


class GeminiAIChat:
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

    @error_handler
    async def _create_chat(self) -> None:
        cfg = (
            types.GenerateContentConfig(system_instruction=self.instruction)
            if self.instruction
            else None
        )
        self.chat = self.client.aio.chats.create(model=self.model, config=cfg)

    @error_handler
    async def send(
        self,
        message: str,
        tools: Optional[List[Tool]] = None,
        temperature: float = 0.9,
        max_output_tokens: int = 1024,
    ) -> str:
        if not self.chat:
            await self._create_chat()
        if tools is None:
            tools = [Tool(google_search=GoogleSearch())]
        cfg = GenerateContentConfig(
            system_instruction=self.instruction,
            max_output_tokens=max_output_tokens,
            temperature=temperature,
            tools=tools,
        )
        response = await self.chat.send_message(message, config=cfg)
        return response.text

    @error_handler
    async def set_instruction(self, instruction: str) -> None:
        self.instruction = instruction
        await self._create_chat()

    @error_handler
    async def vision(
        self,
        image: ImageType,
        prompt: str = IMAGE_PROMPT,
        tools: Optional[List[Tool]] = None,
        temperature: float = 0.1,
        max_output_tokens: int = 500,
    ) -> str:
        loop = asyncio.get_running_loop()
        image_obj = image
        if isinstance(image, str):
            image_obj = await loop.run_in_executor(None, self._open_image, image)
        if tools is None:
            tools = [Tool(google_search=GoogleSearch())]
        cfg = GenerateContentConfig(
            system_instruction=self.instruction,
            max_output_tokens=max_output_tokens,
            temperature=temperature,
            tools=tools,
        )
        response = await self.client.aio.models.generate_content(
            model=self.model, contents=[prompt, image_obj], config=cfg
        )
        return response.text

    def _open_image(self, image_path: str) -> Image.Image:
        try:
            with Image.open(image_path) as img:
                return img.copy()
        except FileNotFoundError:
            raise FileNotFoundError(f"Image file not found: {image_path}")
        except Exception as e:
            raise ValueError(f"Failed to open image: {str(e)}")


class ChatManager:
    def __init__(self):
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
        if user_id in self.user_chats:
            del self.user_chats[user_id]
            return True
        return False


gemini_chat = ChatManager()
