MODEL_CONFIG = {
    "gemma3:12b": {
        "name": "gemma3:12b",
        "ctx": 10000, # reliably fits on my GPU
    },

    "qwen3:14b": {
        "name": "qwen3:14b",
        "ctx": 8000, # reliably fits on my GPU
    },

    "qwen3:4b": {
        "name": "qwen3:4b",
        "ctx": 24567, # larger window for very long input documents
    }
}

