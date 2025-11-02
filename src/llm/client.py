import json
import re
import time
from typing import Dict, List, Optional

from ollama import ChatResponse, Client, GenerateResponse, Options
from src.utils.config import settings
from src.utils.logging import get_logger
from transformers import AutoTokenizer

logger = get_logger(__name__)

# get_logger("httpx").setLevel(DEBUG)
# get_logger("httpcore").setLevel(DEBUG)

# Import the database ModelConfig - this is now the single source of truth
from src.database.model_configs import ModelConfig


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
    ) -> tuple[ChatResponse, Optional[str]]:

    if not client:
        client = init_client(settings.openai_api.url)

    contents = [msg['content'] for msg in messages]
    input_tokens = sum(count_tokens(model_config, content) for content in contents)

    logger.info("sending_chat_request", model=model_config.model, input_tokens=input_tokens)

    # Get options from the database model
    options_dict = json.loads(model_config.options_json)
    options = Options(**options_dict)
    num_ctx = options_dict.get('num_ctx', 4096)

    warning = None
    if input_tokens > num_ctx:
        warning = f"oversized_input: {input_tokens} tokens exceeds num_ctx {num_ctx}"
        logger.info("oversized_input", input_tokens=input_tokens, num_ctx=num_ctx)

    response = retry_backoff(3600, client.chat, model_config.model, options=options, messages=messages)

    duration=response.total_duration / 1e9
    output_tokens=count_tokens(model_config, response.message.content)
    tokens_per_second = output_tokens / duration

    logger.info("recieved_chat_response",
        model=model_config.model,
        done=response.done,
        done_reason=response.done_reason,
        duration=f"{duration / 1e9:.2f}s",
        output_tokens=output_tokens,
        tokens_per_second=f"{tokens_per_second:0.2f} tokens/s",
    )

    return response, warning



def count_tokens(model_config: ModelConfig, content: str):
    if 'qwen' in model_config.model.lower():
        encoder = "Qwen/Qwen3-4B"
    elif 'gemma' in model_config.model.lower():
        encoder = "google/gemma-3-12b-it"

    tokenizer = AutoTokenizer.from_pretrained(encoder, token=settings.huggingface_api.token)
    tokens = tokenizer.encode(content)

    return len(tokens)

def remove_thinking_tags(content: str):
    if not content:
        return None

    # Remove <think>...</think> blocks and any content before them
    cleaned = re.sub(r'<think>[\s\S]*?</think>\s*', '', content, flags=re.IGNORECASE)

    # Trim any remaining whitespace
    cleaned = cleaned.strip()

    return cleaned or None



def get_generate_response(model_config: ModelConfig, system_prompt: str, user_prompt: str, client: Optional[Client] = None) -> tuple[GenerateResponse, Optional[str]]:
    if not client:
        client = init_client(settings.openai_api.url)

    input_tokens = count_tokens(model_config, system_prompt + user_prompt)

    logger.info("sending_generate_request", model=model_config.model, input_tokens=input_tokens)

    # Get options from the database model
    options_dict = json.loads(model_config.options_json)
    options = Options(**options_dict)
    num_ctx = options_dict.get('num_ctx', 4096)

    warning = None
    if input_tokens > num_ctx:
        warning = f"oversized_input: {input_tokens} tokens exceeds num_ctx {num_ctx}"
        logger.warning("oversized_input", tokens=input_tokens, num_ctx=num_ctx)

    response = retry_backoff(
        timeout=3600,
        func=client.generate,
        model = model_config.model,
        system = system_prompt,
        prompt = user_prompt,
        options = options,
    )
    duration=response.total_duration / 1e9
    output_tokens=count_tokens(model_config, response.response)
    tokens_per_second = output_tokens / duration

    logger.info("recieved_generate_response",
        model=model_config.model,
        done=response.done,
        done_reason=response.done_reason,
        duration=f"{response.total_duration / 1e9:.2f}s",
        output_tokens=output_tokens,
        tokens_per_second=tokens_per_second,
    )

    return response, warning