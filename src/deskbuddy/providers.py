"""AI providers Desk Buddy can talk to. All of them speak the OpenAI-style chat API, so one
client covers every provider; only the address, key and model names differ.

The model names are starting suggestions. They can be edited on the Settings page, because
providers rename and retire models often."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Provider:
    key: str
    name: str
    base_url: str
    fast_model: str
    agent_model: str
    needs_key: bool = True
    key_help: str = ""          # where to get a key


CUSTOM = "custom"

PROVIDERS: list[Provider] = [
    Provider("nvidia", "NVIDIA", "https://integrate.api.nvidia.com/v1",
             "nvidia/nemotron-3.5-bolt-e4b", "nvidia/nemotron-3.5-super-vl-120b-a12b",
             key_help="build.nvidia.com"),
    Provider("openai", "OpenAI", "https://api.openai.com/v1",
             "gpt-4.1-mini", "gpt-4.1", key_help="platform.openai.com/api-keys"),
    Provider("anthropic", "Anthropic (Claude)", "https://api.anthropic.com/v1/",
             "claude-haiku-5-5", "claude-sonnet-5-5", key_help="console.anthropic.com"),
    Provider("gemini", "Google Gemini", "https://generativelanguage.googleapis.com/v1beta/openai/",
             "gemini-2.5-flash", "gemini-2.5-pro", key_help="aistudio.google.com/apikey"),
    Provider("openrouter", "OpenRouter", "https://openrouter.ai/api/v1",
             "openai/gpt-4.1-mini", "anthropic/claude-sonnet-4.5", key_help="openrouter.ai/keys"),
    Provider("groq", "Groq", "https://api.groq.com/openai/v1",
             "llama-3.1-8b-instant", "llama-3.3-70b-versatile", key_help="console.groq.com/keys"),
    Provider("together", "Together AI", "https://api.together.xyz/v1",
             "meta-llama/Llama-3.3-70B-Instruct-Turbo", "meta-llama/Llama-3.3-70B-Instruct-Turbo",
             key_help="api.together.ai/settings/api-keys"),
    Provider("mistral", "Mistral", "https://api.mistral.ai/v1",
             "mistral-small-latest", "mistral-large-latest", key_help="console.mistral.ai"),
    Provider("deepseek", "DeepSeek", "https://api.deepseek.com/v1",
             "deepseek-chat", "deepseek-chat", key_help="platform.deepseek.com"),
    Provider("ollama", "Ollama (on this PC)", "http://localhost:11434/v1",
             "llama3.1", "llama3.1", needs_key=False),
    Provider("lmstudio", "LM Studio (on this PC)", "http://localhost:1234/v1",
             "local-model", "local-model", needs_key=False),
    Provider(CUSTOM, "Other (any OpenAI-compatible address)", "", "", ""),
]
BY_KEY = {p.key: p for p in PROVIDERS}
DEFAULT = "nvidia"


def get(key: str) -> Provider:
    return BY_KEY.get((key or "").strip().lower(), BY_KEY[CUSTOM])


def guess(base_url: str) -> str:
    """The provider whose address matches `base_url` (for a .env written before providers existed)."""
    url = (base_url or "").strip().rstrip("/").lower()
    for provider in PROVIDERS:
        if provider.base_url and provider.base_url.rstrip("/").lower() == url:
            return provider.key
    return CUSTOM if url else DEFAULT
