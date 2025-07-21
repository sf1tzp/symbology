from dataclasses import dataclass
import re
import time
from typing import Dict, List, Optional

from ollama import ChatResponse, Client, GenerateResponse
from src.utils.config import settings
from src.utils.logging import get_logger
from transformers import AutoTokenizer

logger = get_logger(__name__)

# get_logger("httpx").setLevel(DEBUG)
# get_logger("httpcore").setLevel(DEBUG)

@dataclass
# TODO: replace with ollama's Options class
class ModelConfig:
    name: str
    num_ctx: int = 4096
    temperature: float = 0.8
    top_k: int = 40
    top_p: float = 0.9
    seed: int = 0b111001111110011101101110001011011111101100110111111001111111001 # symbology
    num_predict: int = -1
    num_gpu: Optional[int] = None

def retry_backoff(timeout, func, *args, **kwargs):
    backoff = 1
    logger.debug("retry_backoff", backoff=backoff, timeout=timeout, func=func, args=args, kwargs=kwargs)
    start = time.time()
    while time.time() - start < timeout:
        try:
            result = func(*args, **kwargs)
            return result

        except Exception as e:
            logger.error("retry_backoff", backoff=backoff, error=e)
            backoff = min(60, backoff * 2)
            time.sleep(backoff)
    else:
        raise TimeoutError

def init_client(url: str):
    client = Client(host=url)
    try:
        retry_backoff(3600, client.ps)
    except TimeoutError as err:
        logger.error("ollama_connection_failed", url=url, err=err)
        raise TimeoutError from err

    logger.debug('connected_to_ollama', url=url)
    return client


def get_chat_response(
        model_config: ModelConfig,
        messages: List[Dict],
        client: Optional[Client] = None,
    ) -> ChatResponse:

    if not client:
        client = init_client(settings.openai_api.url)

    contents = [msg['content'] for msg in messages]
    input_tokens = sum(count_tokens(model_config, content) for content in contents)

    logger.info("sending_chat_request", model=model_config.name, input_tokens=input_tokens)

    if input_tokens > model_config.num_ctx:
        logger.warn("oversized_input", input_tokens=input_tokens, num_ctx=model_config.num_ctx)

    options = {
        "num_ctx": model_config.num_ctx,
        "temperature": model_config.temperature,
        "top_k": model_config.top_k,
        "top_p": model_config.top_p,
        "seed": model_config.seed,
        "num_predict": model_config.num_predict,
    }

    response = retry_backoff(3600, client.chat, model_config.name, options=options, messages=messages)

    # response = client.chat(model_config.name,
    #     options = {
    #         "num_ctx": model_config.num_ctx,
    #         "temperature": model_config.temperature,
    #         "top_k": model_config.top_k,
    #         "top_p": model_config.top_p,
    #         "seed": model_config.seed,
    #         "num_predict": model_config.num_predict,
    #     },
    #     messages = messages,
    # )
    duration=response.total_duration / 1e9
    output_tokens=count_tokens(model_config, response.message.content)
    tokens_per_second = output_tokens / duration

    logger.info("recieved_chat_response",
        model=model_config.name,
        done=response.done,
        done_reason=response.done_reason,
        duration=f"{duration / 1e9:.2f}s",
        output_tokens=output_tokens,
        tokens_per_second=f"{tokens_per_second:0.2f} tokens/s",
    )

    return response



def count_tokens(model_config: ModelConfig, content: str):
    if 'qwen' in model_config.name.lower():
        encoder = "Qwen/Qwen3-4B"
    elif 'gemma' in model_config.name.lower():
        encoder = "google/gemma-3-12b-it"

    tokenizer = AutoTokenizer.from_pretrained(encoder, token=settings.huggingface_api.token)
    tokens = tokenizer.encode(content)

    return len(tokens)

def remove_thinking_tags(content: str):
    if not content:
        return None

    # Remove <think>...</think> blocks and any content before them
    cleaned = re.sub(r'<think>[\s\S]*?</think>\s*', '', content, flags=re.IGNORECASE)

    # Also handle cases where there might be thinking content without tags
    # cleaned = re.sub(
    #     r'^(Okay,|Let me|I need to|First,|Based on)[\s\S]*?(?=\n\n|\. [A-Z])',
    #     '',
    #     cleaned,
    #     flags=re.IGNORECASE
    # )

    # Trim any remaining whitespace
    cleaned = cleaned.strip()

    return cleaned or None

# class CompletionRequest(BaseModel):
#     """Parameters for a completion request."""

#     model: str = Field(default_factory=lambda: settings.openai.default_model)
#     messages: List[Message]
#     temperature: float = Field(default=0.7)
#     max_tokens: Optional[int] = Field(default=4000)
#     top_p: Optional[float] = Field(default=1.0)
#     frequency_penalty: Optional[float] = Field(default=0.0)
#     presence_penalty: Optional[float] = Field(default=0.0)
#     stop: Optional[Union[str, List[str]]] = Field(default=None)
#     stream: bool = Field(default=False)

#     def to_dict(self) -> Dict[str, Any]:
#         """Convert to dictionary for API request."""
#         result = self.model_dump(exclude_none=True)
#         result["messages"] = [m.model_dump() for m in self.messages]
#         return result


# class CompletionResponse(BaseModel):
#     """Response from a completion request."""

#     id: str
#     object: str
#     created: int
#     model: str
#     choices: List[Dict[str, Any]]
#     usage: Dict[str, int]



def get_generate_response(model_config: ModelConfig, system_prompt: str, user_prompt: str, client: Optional[Client] = None) -> GenerateResponse:
    if not client:
        client = init_client(settings.openai_api.url)

    input_tokens = count_tokens(model_config, system_prompt + user_prompt)

    logger.info("sending_generate_request", model=model_config.name, input_tokens=input_tokens)

    if input_tokens > model_config.num_ctx:
        logger.warn("oversized_input", tokens=input_tokens, num_ctx=model_config.num_ctx)


    response = retry_backoff(
        timeout=3600,
        func=client.generate,
        model = model_config.name,
        system = system_prompt,
        prompt = user_prompt,
        options = {
            "num_ctx": model_config.num_ctx,
            "temperature": model_config.temperature,
            "top_k": model_config.top_k,
            "top_p": model_config.top_p,
            "seed": model_config.seed,
            "num_predict": model_config.num_predict,
        },
    )
    duration=response.total_duration / 1e9
    output_tokens=count_tokens(model_config, response.response)
    tokens_per_second = output_tokens / duration

    logger.info("recieved_generate_response",
        model=model_config.name,
        done=response.done,
        done_reason=response.done_reason,
        duration=f"{response.total_duration / 1e9:.2f}s",
        output_tokens=output_tokens,
        tokens_per_second=tokens_per_second,
    )

    return response