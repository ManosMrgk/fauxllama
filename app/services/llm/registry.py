from __future__ import annotations
import os, logging
from typing import Dict, Optional
from .base import LLMClient
from .azure_openai import AzureOpenAIClient
from .openai import OpenAIClient
from .anthropic import AnthropicClient
from .gemini import GeminiClient
from dotenv import load_dotenv

log = logging.getLogger(__name__)

load_dotenv()

_REGISTRY: Dict[str, LLMClient] = {}
_ACTIVE: Optional[str] = None

def register(client: LLMClient) -> None:
    _REGISTRY[client.name] = client

def get(provider: str) -> LLMClient:
    try:
        return _REGISTRY[provider]
    except KeyError:
        raise ValueError(f"Unknown provider '{provider}'. Registered: {list(_REGISTRY)}")

def _can_bootstrap(name: str) -> bool:
    if name == "azure":
        need = ("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_KEY", "AZURE_OPENAI_DEPLOYMENT")
        return all(os.getenv(k) for k in need)
    
    elif name == "openai":
        need = ("OPENAI_API_KEY", "OPENAI_MODEL")
        return all(os.getenv(k) for k in need)
    
    elif name == "anthropic":
        return True # Not implemented
    
    elif name == "gemini":
        return True # Not implemented

def _try_init(name: str) -> Optional[LLMClient]:
    try:
        if name == "azure" and _can_bootstrap("azure"):
            c = AzureOpenAIClient()
            c.validate()
            return c
        if name == "openai" and _can_bootstrap("openai"):
            c = OpenAIClient()
            c.validate()
            return c
    except Exception as e:
        log.warning("Provider %s failed validation: %s", name, e)
    return None

def auto_register_llm_from_env() -> None:
    """Register providers that have enough env config present."""
    
    # Azure
    if _can_bootstrap("azure"): client = None; client = AzureOpenAIClient(); client.validate(); register(client)
    # OpenAI
    if _can_bootstrap("openai"):  client = None; client = OpenAIClient(); client.validate(); register(client)
    # Anthropic
    if _can_bootstrap("anthropic"):  client = None; client = AnthropicClient(); client.validate(); register(client)
    # Gemini
    if _can_bootstrap("gemini"):  client = None; client = GeminiClient(); client.validate(); register(client)
    
    global _ACTIVE
    wanted = (os.getenv("LLM_PROVIDER") or "").strip().lower()
    print("Provider selected:", wanted)
    if wanted and wanted in _REGISTRY:
        _ACTIVE = wanted

    if not _ACTIVE:
        raise RuntimeError(
            "No LLM provider available. Set LLM_PROVIDER and provider-specific .env variables."
        )


def active_provider() -> LLMClient:
    assert _ACTIVE, "Registry not initialized. Call auto_register_llm_from_env() once at startup."
    return _REGISTRY[_ACTIVE]
