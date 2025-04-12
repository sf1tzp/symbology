import os
import time
import random
import ollama
import openai
import tiktoken


OLLAMA_HOST = (
    os.getenv("OLLAMA_HOST") if os.getenv("OLLAMA_HOST") else "localhost:24098"
)

DEFAULT_MODEL = "my-gemma3-4b:latest"  # "llama3.2-54k:latest" # "deepseek-r1:7b-32k" # "gemma3:4b-42k"


def ollama_chat(model, system_prompt, content, temperature):
    ollama_client = ollama.Client(host=f"http://{OLLAMA_HOST}")

    input_tokens = estimate_tokens(model, system_prompt + content)

    if input_tokens > 40960:
        print(f"WARNING token input ({input_tokens}) is larger over 40k")
        # return progressive_refinement(model, context_window, system_prompt, content)

    start = time.time()
    response = ollama_client.chat(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "You are a helpful research assistant that identifies important topics and tone in documents."
            },
            {
                "role": "assistant",
                "content": "Always present your reports in valid mardown"

            },
            {
                "role": "assistant",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": content
            }
        ],
        options={
            "top_k" : 64,
            "top_p" : 0.95,
            "min_p" : 0.0,
            "num_ctx": 48 * 1024,
            "temperature": temperature,
            "num_predict": 2 * 1024,
            "repeat_last_n": 1024,
            "repeat_penalty": 1.0,
            "seed": random.randrange(1024)
        }
    )
    duration = time.time() - start
    summary = response.message['content']
    output_tokens = estimate_tokens(model, summary)
    tokens_per_second = output_tokens / duration
    print(
        f"{input_tokens} tokens in, {output_tokens} tokens out in {duration:.2f} seconds ({tokens_per_second:.2f} tokens/second)"
    )
    return summary

def estimate_tokens(model, text):
    try:
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except:
        return len(text) // 4 # Rough estimation: ~4 chars per token in English text



def openai_chat(model, system_prompt, content, temperature):
    input_tokens=estimate_tokens(model, system_prompt + content)
    start = time.time()
    client = openai.OpenAI()
    response = client.chat.completions.create(
        model = model,
        messages = [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": content
            }
        ],
        temperature = temperature,
        seed = random.randrange(1024)
    )

    duration = time.time() - start
    summary = response.choices[0].message.content
    output_tokens = estimate_tokens(model, summary)
    tokens_per_second = output_tokens / duration
    print(
        f"{input_tokens} tokens in, {output_tokens} tokens out in {duration:.2f} seconds ({tokens_per_second:.2f} tokens/second)"
    )
    return summary

