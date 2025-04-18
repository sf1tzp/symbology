"""
OpenAI API client for making inference requests to the OpenAI endpoint.

This module provides functionality to:
1. Connect to the configured OpenAI endpoint
2. Send prompts with configurable parameters
3. Process and return responses
"""

from typing import Any, Dict, List, Optional, Union

import httpx
from pydantic import BaseModel, Field

from src.utils.config import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)



class Message(BaseModel):
    """Representation of a chat message."""

    role: str
    content: str


class CompletionRequest(BaseModel):
    """Parameters for a completion request."""

    model: str = Field(default_factory=lambda: settings.openai_api.default_model)
    messages: List[Message]
    temperature: float = Field(default=0.7)
    max_tokens: Optional[int] = Field(default=4000)
    top_p: Optional[float] = Field(default=1.0)
    frequency_penalty: Optional[float] = Field(default=0.0)
    presence_penalty: Optional[float] = Field(default=0.0)
    stop: Optional[Union[str, List[str]]] = Field(default=None)
    stream: bool = Field(default=False)
    context_window: Optional[int] = Field(default=None, description="Context window size for Ollama models")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API request."""
        result = self.model_dump(exclude_none=True)
        result["messages"] = [m.model_dump() for m in self.messages]

        # Ensure we have a valid model name
        if not result.get("model") or result["model"] == "":
            # Fallback to a default model
            result["model"] = "gemma-3-12b-it"
            logger.warning(f"Missing model name, using default: {result['model']}")

        # Log detailed info about the model parameter
        logger.debug(f"Model parameter: type={type(result['model'])}, value='{result['model']}', empty={result['model'] == ''}")

        # Log the model being used
        logger.debug(f"Using model in request: {result['model']}")

        # Add Ollama-specific parameters if using Ollama
        if settings.openai_api.is_ollama and self.context_window:
            # For Ollama, we need to add the num_ctx parameter to extend the context window
            result["options"] = result.get("options", {})
            result["options"]["num_ctx"] = self.context_window
            logger.debug(f"Setting Ollama context window to: {self.context_window}")

        # Remove context_window from top level as it's not a standard OpenAI parameter
        if "context_window" in result:
            del result["context_window"]

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
        self.base_url = f"http://{settings.openai_api.host}:{settings.openai_api.port}"
        self.client = httpx.Client(timeout=300.0)  # 5 minute timeout to accommodate larger models
        # Set default flag
        settings.openai_api.is_ollama = False

        # Test connection and log endpoint
        logger.info(f"Initialized OpenAI client with endpoint: {self.base_url}")
        try:
            # Test API connectivity
            response = self.client.get(f"{self.base_url}/v1/models")
            response.raise_for_status()
            logger.info("Successfully verified connection to OpenAI API")

            # Check if we're using Ollama
            if "ollama" in response.text.lower() or self.base_url.lower().find("ollama") >= 0:
                settings.openai_api.is_ollama = True
                logger.info("Detected Ollama API server")

            # Log available models
            try:
                models = response.json().get("data", [])
                model_ids = [model.get("id") for model in models if isinstance(model, dict) and "id" in model]
                logger.info(f"Available models: {', '.join(model_ids)}")
            except Exception as e:
                logger.warning(f"Could not parse models list: {e}")

        except httpx.HTTPError as e:
            logger.warning(f"Could not verify connection to OpenAI API: {e}")
            logger.warning("Requests may fail if the API is not available")

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

        # Convert the request to a dictionary
        request_data = request.to_dict()

        # Detailed logging for request data, especially model parameter
        logger.debug(f"Sending request to {url}")
        logger.debug(f"Request model: {request_data.get('model', 'MISSING')}")
        logger.debug(f"Request model type: {type(request_data.get('model', None))}")
        logger.debug(f"Request message count: {len(request_data.get('messages', []))}")
        logger.debug(f"Request data keys: {list(request_data.keys())}")
        logger.debug(f"First few messages: {[m.get('role', '') for m in request_data.get('messages', [])[:2]]}")

        # Force model parameter if it's missing or empty
        if 'model' not in request_data or not request_data['model']:
            request_data['model'] = settings.openai_api.default_model
            logger.warning(f"Added missing model parameter: {request_data['model']}")

        try:
            # Log the full request payload for debugging
            logger.debug(f"Request payload: {request_data}")

            response = self.client.post(
                url,
                json=request_data,
                headers={"Content-Type": "application/json"}
            )

            # Log response status
            logger.debug(f"Response status: {response.status_code}")

            response.raise_for_status()

            return CompletionResponse(**response.json())

        except httpx.HTTPError as e:
            logger.error(f"Error making completion request: {str(e)}")
            # Additional logging for 4XX errors to help diagnose the issue
            if hasattr(e, 'response') and e.response and 400 <= e.response.status_code < 500:
                try:
                    error_body = e.response.json()
                    logger.error(f"API error response: {error_body}")
                except Exception:
                    # If we can't parse the JSON response, log the raw text
                    logger.error(f"API error text: {e.response.text}")
            raise

    def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        context_texts: Optional[List[str]] = None,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        model: Optional[str] = None,
        context_window: Optional[int] = 20480,
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
            model: Model to use for completion (overrides default)
            context_window: Size of context window for Ollama models (overrides default 2048)
            **kwargs: Additional parameters for the completion request

        Returns:
            The generated text from the completion
        """
        # Start with the system message (instructions to the AI)
        messages = [
            Message(role="system", content=system_prompt),
        ]

        # Add context as separate messages before the user prompt
        content_to_add = ""
        if context_texts:
            for i, context in enumerate(context_texts):
                if context.strip():  # Skip empty contexts
                    # Add each context with clear labeling to indicate it's content to analyze
                    content_to_add = f"CONTENT TO ANALYZE #{i+1}:\n\n{context}"
                    # messages.append(Message(role="user", content=content_to_add))

        # Add the actual user prompt/query as the final user message
        messages.append(Message(role="user", content=f"{user_prompt}: \n\n {content_to_add}"))

        # Ensure model parameter is specified and valid
        if model is None or model == "":
            model = settings.openai_api.default_model
            logger.warning(f"Model parameter missing or empty, using default: {model}")
        else:
            logger.debug(f"Using provided model: '{model}' (type: {type(model)})")

        # Ensure temperature is within bounds
        if temperature is None:
            temperature = 0.7
            logger.warning(f"Temperature parameter missing, using default: {temperature}")

        # Create the completion request with validated parameters
        request = CompletionRequest(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            context_window=context_window,
            **kwargs
        )

        logger.info(f"Sending completion request with {len(messages)} messages, temperature={temperature}")

        response = self.create_completion(request)

        # Extract the assistant's message from the response
        if response.choices and len(response.choices) > 0:
            return response.choices[0]["message"]["content"]

        return ""