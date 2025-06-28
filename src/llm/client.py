from typing import Any, Dict, List, Optional, Union

from ollama import Client
from pydantic import BaseModel, Field

from src.llm.models import MODEL_CONFIG
from src.utils.config import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)



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

def init_client(url):
    return Client(host=url)

def get_chat_response(client, model, messages):
    model = MODEL_CONFIG[model]
    response = client.chat(model=model["name"],
        options= {
            "num_ctx": model["ctx"],
        },
        messages = messages,
    )
    return response

