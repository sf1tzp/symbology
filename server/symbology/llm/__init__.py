"""
AI integration package for Symbology.

This package provides functionalities for interacting with the Anthropic API
and implementing prompt engineering for financial document analysis.
"""

from .chunking import chunk_text, chunk_text_with_index
from .client import (
    get_chat_response,
    get_generate_response,
    init_client,
    init_openai_chat_client,
    OpenAIResponseAdapter,
    remove_thinking_tags,
)
from .content_processing import (
    chunk_and_embed_document,
    chunk_and_embed_generated_content,
    chunk_embed_and_cluster_document,
)
from .embeddings import embed_query, embed_texts, init_embedding_client
from .section_chunker import chunk_document_sections, SectionChunk
from .topic_clustering import (
    assign_unclustered_chunks,
    recluster_company_doctype,
    TOPIC_DISTANCE_THRESHOLD,
)

__all__ = [
    'init_client',
    'init_openai_chat_client',
    'OpenAIResponseAdapter',
    'get_chat_response',
    'get_generate_response',
    'remove_thinking_tags',
    # Embeddings
    'init_embedding_client',
    'embed_texts',
    'embed_query',
    # Chunking
    'chunk_text',
    'chunk_text_with_index',
    # Content processing
    'chunk_and_embed_document',
    'chunk_and_embed_generated_content',
    'chunk_embed_and_cluster_document',
    # Section-aware chunking + topic clustering
    'chunk_document_sections',
    'SectionChunk',
    'assign_unclustered_chunks',
    'recluster_company_doctype',
    'TOPIC_DISTANCE_THRESHOLD',
]
