"""
Configuration management for the Multi-Agent Code Review System.
"""
import os
from typing import Optional, Dict, Any
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # GitHub Configuration
    github_token: str = Field(..., env="GITHUB_TOKEN")
    github_webhook_secret: Optional[str] = Field(None, env="GITHUB_WEBHOOK_SECRET")
    
    # Ollama Configuration
    ollama_base_url: str = Field("http://localhost:11434", env="OLLAMA_BASE_URL")
    ollama_model_code: str = Field("mistral", env="OLLAMA_MODEL_CODE")  # Using mistral for now
    ollama_model_general: str = Field("mistral", env="OLLAMA_MODEL_GENERAL")
    
    # Redis Configuration
    redis_url: str = Field("redis://localhost:6379/0", env="REDIS_URL")
    
    # ChromaDB Configuration
    chroma_persist_directory: str = Field("./chroma_db", env="CHROMA_PERSIST_DIRECTORY")
    chroma_collection_name: str = Field("code_review_knowledge", env="CHROMA_COLLECTION_NAME")
    
    # API Configuration
    api_host: str = Field("0.0.0.0", env="API_HOST")
    api_port: int = Field(8000, env="API_PORT")
    api_workers: int = Field(1, env="API_WORKERS")
    
    # Security
    secret_key: str = Field("your-secret-key-here", env="SECRET_KEY")
    
    # Logging
    log_level: str = Field("INFO", env="LOG_LEVEL")
    log_file: str = Field("logs/code_review.log", env="LOG_FILE")
    
    # Feature Flags
    enable_security_agent: bool = Field(True, env="ENABLE_SECURITY_AGENT")
    enable_performance_agent: bool = Field(True, env="ENABLE_PERFORMANCE_AGENT")
    enable_style_agent: bool = Field(True, env="ENABLE_STYLE_AGENT")
    enable_docs_agent: bool = Field(True, env="ENABLE_DOCS_AGENT")
    
    # Rate Limiting
    max_requests_per_minute: int = Field(60, env="MAX_REQUESTS_PER_MINUTE")
    max_concurrent_reviews: int = Field(5, env="MAX_CONCURRENT_REVIEWS")
    
    # Model Parameters
    model_temperature: float = Field(0.1, env="MODEL_TEMPERATURE")
    model_max_tokens: int = Field(2048, env="MODEL_MAX_TOKENS")
    model_timeout: int = Field(30, env="MODEL_TIMEOUT")
    
    class Config:
        env_file = ".env"
        case_sensitive = False

class AgentConfig:
    """Configuration for individual agents."""
    
    def __init__(self, name: str, model: str = None, **kwargs):
        self.name = name
        self.model = model or settings.ollama_model_general
        self.temperature = kwargs.get("temperature", settings.model_temperature)
        self.max_tokens = kwargs.get("max_tokens", settings.model_max_tokens)
        self.system_prompt = kwargs.get("system_prompt", "")
        self.enabled = kwargs.get("enabled", True)

# Global settings instance
settings = Settings()

# Agent configurations
AGENT_CONFIGS = {
    "security": AgentConfig(
        name="Security Agent",
        model=settings.ollama_model_code,
        temperature=0.1,
        system_prompt="""You are a security expert reviewing code for vulnerabilities.
Focus on: SQL injection, XSS, authentication issues, exposed secrets, OWASP Top 10.
Provide specific line numbers and severity levels (CRITICAL, HIGH, MEDIUM, LOW)."""
    ),
    "performance": AgentConfig(
        name="Performance Agent",
        model=settings.ollama_model_code,
        temperature=0.1,
        system_prompt="""You are a performance optimization expert reviewing code.
Focus on: time complexity, memory usage, database queries, caching opportunities.
Identify O(n²) or worse algorithms, N+1 queries, memory leaks."""
    ),
    "style": AgentConfig(
        name="Style Agent",
        model=settings.ollama_model_code,
        temperature=0.1,
        system_prompt="""You are a code style expert ensuring clean, readable code.
Focus on: naming conventions, code organization, DRY principles, readability.
Reference language-specific style guides (PEP8, ESLint, etc.)."""
    ),
    "documentation": AgentConfig(
        name="Documentation Agent",
        model=settings.ollama_model_general,
        temperature=0.2,
        system_prompt="""You are a documentation expert reviewing code documentation.
Focus on: docstrings, inline comments, README updates, API documentation.
Ensure complex logic is explained and public APIs are documented."""
    ),
}

# Ensure directories exist
def ensure_directories():
    """Create necessary directories if they don't exist."""
    directories = [
        Path(settings.chroma_persist_directory),
        Path(settings.log_file).parent,
        Path("data/reviews"),
        Path("data/feedback"),
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)

# Run on import
ensure_directories()