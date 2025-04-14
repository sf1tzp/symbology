"""
OpenAI API client for making inference requests to the OpenAI endpoint.

This module provides functionality to:
1. Connect to the configured OpenAI endpoint
2. Send prompts with configurable parameters
3. Process and return responses
"""

import logging
from typing import Any, Dict, List, Optional, Union

import httpx
from pydantic import BaseModel, Field

from ..config import settings

logger = logging.getLogger(__name__)


class Message(BaseModel):
    """Representation of a chat message."""

    role: str
    content: str


class CompletionRequest(BaseModel):
    """Parameters for a completion request."""

    model: str = Field(default_factory=lambda: settings.openai.default_model)
    messages: List[Message]
    temperature: float = Field(default=0.7)
    max_tokens: Optional[int] = Field(default=4000)
    top_p: Optional[float] = Field(default=1.0)
    frequency_penalty: Optional[float] = Field(default=0.0)
    presence_penalty: Optional[float] = Field(default=0.0)
    stop: Optional[Union[str, List[str]]] = Field(default=None)
    stream: bool = Field(default=False)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API request."""
        result = self.model_dump(exclude_none=True)
        result["messages"] = [m.model_dump() for m in self.messages]
        return result


class CompletionResponse(BaseModel):
    """Response from a completion request."""

    id: str
    object: str
    created: int
    model: str
    choices: List[Dict[str, Any]]
    usage: Dict[str, int]


class OpenAIClient:
    """Client for interacting with the OpenAI API."""

    def __init__(self):
        """Initialize the OpenAI client with configuration from settings."""
        self.base_url = f"http://{settings.openai.open_ai_host}:{settings.openai.open_ai_port}"
        self.client = httpx.Client(timeout=60.0)  # 60 second timeout

    def create_completion(self, request: CompletionRequest) -> CompletionResponse:
        """
        Send a completion request to the OpenAI API.

        Args:
            request: The completion request parameters

        Returns:
            The completion response from the API

        Raises:
            httpx.HTTPError: If the request fails
        """
        url = f"{self.base_url}/v1/chat/completions"

        logger.debug(f"Sending request to {url}")

        try:
            response = self.client.post(
                url,
                json=request.to_dict(),
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()

            return CompletionResponse(**response.json())

        except httpx.HTTPError as e:
            logger.error(f"Error making completion request: {str(e)}")
            raise

    def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        context_texts: Optional[List[str]] = None,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        **kwargs
    ) -> str:
        """
        Generate text completion from the OpenAI API using system and user prompts.

        Args:
            system_prompt: The system instructions for the model
            user_prompt: The user query or content
            context_texts: Optional list of texts to provide as additional context
            temperature: Controls randomness (0.0-1.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters for the completion request

        Returns:
            The generated text from the completion
        """
        messages = [
            Message(role="system", content=system_prompt),
        ]

        # Add context messages if provided
        if context_texts:
            for context in context_texts:
                messages.append(Message(role="user", content=context))
                # Add an empty assistant response to maintain the conversation flow
                messages.append(Message(role="assistant", content="I've received this information."))

        # Add the main user prompt
        messages.append(Message(role="user", content=user_prompt))

        request = CompletionRequest(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )

        response = self.create_completion(request)

        # Extract the assistant's message from the response
        if response.choices and len(response.choices) > 0:
            return response.choices[0]["message"]["content"]

        return ""