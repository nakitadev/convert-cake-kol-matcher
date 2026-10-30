"""
Langfuse Tracing Service for Convert Cake KOL Matcher.

Provides optional tracing for LangGraph workflow execution and LLM calls.
Gracefully degrades to a no-op if Langfuse keys are not configured or if
langfuse is not installed.
"""
import os
import logging
from typing import Optional, Any, Dict

logger = logging.getLogger(__name__)


def is_langfuse_enabled() -> bool:
    """Check if Langfuse credentials are configured in the environment."""
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY", "").strip()
    secret_key = os.getenv("LANGFUSE_SECRET_KEY", "").strip()
    return bool(public_key and secret_key)


def get_langfuse_callback_handler() -> Optional[Any]:
    """
    Get a Langfuse CallbackHandler for LangGraph / LangChain execution.
    Returns None if LANGFUSE_PUBLIC_KEY or LANGFUSE_SECRET_KEY are missing.
    """
    if not is_langfuse_enabled():
        return None

    try:
        try:
            from langfuse.langchain import CallbackHandler
        except ImportError:
            from langfuse.callback import CallbackHandler

        public_key = os.getenv("LANGFUSE_PUBLIC_KEY", "").strip()
        handler = CallbackHandler(public_key=public_key)
        return handler
    except Exception as exc:
        logger.warning(f"Failed to initialize Langfuse CallbackHandler: {exc}")
        return None


def flush_langfuse_handler(handler: Optional[Any]) -> None:
    """Safely flush pending traces from the CallbackHandler."""
    if not handler:
        return
    try:
        client = getattr(handler, "_langfuse_client", None)
        if client and hasattr(client, "flush"):
            client.flush()
        elif hasattr(handler, "flush"):
            handler.flush()
    except Exception as exc:
        logger.warning(f"Error flushing Langfuse client: {exc}")


def get_trace_url_from_handler(handler: Optional[Any]) -> Optional[str]:
    """Retrieve the web trace URL for the completed run, if available."""
    if not handler:
        return None
    try:
        client = getattr(handler, "_langfuse_client", None)
        trace_id = getattr(handler, "last_trace_id", None)
        if client and trace_id and hasattr(client, "get_trace_url"):
            return client.get_trace_url(trace_id=trace_id)
    except Exception as exc:
        logger.debug(f"Could not retrieve Langfuse trace URL: {exc}")
    return None
