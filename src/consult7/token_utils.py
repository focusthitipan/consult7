"""Token estimation and thinking budget utilities for Consult7."""

from typing import Optional
from .constants import DEFAULT_OUTPUT_TOKENS

# Token and model constants
TOKEN_SAFETY_FACTOR = 0.9  # Safety buffer for token calculations

# Thinking/reasoning constants
MAX_REASONING_TOKENS = 31_999  # OpenRouter maximum reasoning cap (actual limit for Anthropic)
FLASH_MAX_THINKING_TOKENS = 24_576  # Google Flash model thinking limit
PRO_MAX_THINKING_TOKENS = 32_768  # Google Pro model thinking limit

# Token estimation constants
CHARS_PER_TOKEN_REGULAR = 3.2  # Characters per token for regular text/code
CHARS_PER_TOKEN_HTML = 2.5  # Characters per token for HTML/XML
TOKEN_ESTIMATION_BUFFER = 1.1  # 10% buffer for token estimation

# Thinking/Reasoning Token Limits by Model - Officially Supported Models Only
THINKING_LIMITS = {
    # OpenAI models - use effort-based reasoning (not token counts)
    "openai/gpt-5.1": "effort",
    # Google Gemini models
    "google/gemini-2.5-pro": 32_768,
    "google/gemini-2.5-flash": 24_576,
    "google/gemini-2.5-flash-lite": 24_576,
    # Anthropic Claude models
    "anthropic/claude-sonnet-4.5": 31_999,
    "anthropic/claude-opus-4.1": 31_999,
    # X-AI Grok models - TBD (need to test)
    "x-ai/grok-4": 32_000,  # To be confirmed
    "x-ai/grok-4-fast": 32_000,  # To be confirmed
    # GitHub Copilot models (via OpenRouter-style o1 models)
    "o1-preview": 32_768,  # OpenAI o1-preview with reasoning
    "o1-mini": 65_536,  # OpenAI o1-mini with reasoning
}


def calculate_max_file_size(context_length: int, mode: str, model_name: str) -> tuple[int, int]:
    """Calculate maximum file size in bytes based on model's context window.

    Uses generous limits - lets the API be the final arbiter if context overflows.

    Args:
        context_length: Model's context window in tokens
        mode: Performance mode (fast/mid/think)
        model_name: The model name

    Returns:
        Tuple of (max_total_bytes, max_per_file_bytes)
    """
    # Reserve tokens for output
    output_reserve = DEFAULT_OUTPUT_TOKENS

    # Reserve tokens for reasoning/thinking if applicable
    thinking_budget_value = get_thinking_budget(model_name, mode)

    # Handle different thinking budget types
    if thinking_budget_value == "effort":
        # OpenAI effort-based: reserve ~40% of output budget for reasoning
        thinking_budget = int(output_reserve * 0.4)
    elif thinking_budget_value is not None:
        thinking_budget = thinking_budget_value
    else:
        thinking_budget = 0

    # Calculate available tokens for input files
    # Be generous - let the API reject if truly too much
    available_tokens = context_length - output_reserve - thinking_budget

    # Ensure we have at least some capacity
    available_tokens = max(available_tokens, 10_000)  # Minimum 10k tokens

    # Convert tokens to bytes (approximately 4 bytes per token for code)
    max_total_bytes = available_tokens * 4

    # Per-file limit: generous - 50% of total or 10MB, whichever is smaller
    max_per_file = min(max_total_bytes // 2, 10_000_000)

    return max_total_bytes, max_per_file


def estimate_tokens(text: str, is_database_result: bool = False) -> int:
    """Estimate tokens in text using character-based approximation.

    Args:
        text: The text to estimate tokens for
        is_database_result: Whether text is formatted database results (affects estimation)

    Returns:
        Estimated number of tokens (rounded up)
    """
    # Check if text contains HTML/XML markers
    is_html = "<" in text and ">" in text

    # Database results are typically more token-dense due to tabular formatting
    if is_database_result:
        # Database results: more structured, slightly lower chars/token ratio
        chars_per_token = 2.8
    elif is_html:
        chars_per_token = CHARS_PER_TOKEN_HTML
    else:
        chars_per_token = CHARS_PER_TOKEN_REGULAR

    # Estimate tokens and apply buffer
    base_estimate = len(text) / chars_per_token
    buffered_estimate = base_estimate * TOKEN_ESTIMATION_BUFFER

    return int(buffered_estimate + 0.5)  # Round to nearest integer


def estimate_database_result_tokens(results: list, query: str, database_name: str = "unknown") -> int:
    """Estimate tokens for formatted database results.
    
    This provides upfront estimation before formatting, useful for
    token budget calculations and truncation decisions.
    
    Args:
        results: List of result rows/documents
        query: The query that produced results
        database_name: Name of the database
    
    Returns:
        Estimated token count for formatted results
    """
    if not results:
        # Empty result: minimal tokens
        return estimate_tokens(f"Query: {query}\nResult: No rows returned", is_database_result=True)

    # Estimate based on result structure
    # Header overhead: ~200 tokens (separators, query, metadata)
    header_tokens = 200

    # Per-row estimation
    # Each row: column names + values + formatting
    if isinstance(results[0], dict):
        # Calculate average row size
        sample_row = results[0]
        row_text = " ".join(f"{k}: {v}" for k, v in sample_row.items())
        tokens_per_row = estimate_tokens(row_text, is_database_result=True) + 5  # +5 for formatting

        # Total estimation
        total_tokens = header_tokens + (tokens_per_row * len(results))
    else:
        # Fallback: assume 50 tokens per row
        total_tokens = header_tokens + (50 * len(results))

    return total_tokens


def calculate_database_token_budget(
    context_length: int,
    mode: str,
    model_name: str,
    file_tokens: int = 0,
) -> tuple[int, int]:
    """Calculate token budget available for database results.
    
    Dynamically calculates how many tokens can be used for database
    query results based on model context, mode, and file content already loaded.
    
    Args:
        context_length: Model's context window in tokens
        mode: Performance mode (fast/mid/think)
        model_name: Model name for thinking budget calculation
        file_tokens: Tokens already used by file content
    
    Returns:
        Tuple of (max_db_tokens, truncation_needed) where:
        - max_db_tokens: Maximum tokens available for database results
        - truncation_needed: Whether truncation will likely be needed
    """
    # Reserve tokens for output
    output_reserve = DEFAULT_OUTPUT_TOKENS

    # Reserve tokens for reasoning/thinking if applicable
    thinking_budget_value = get_thinking_budget(model_name, mode)

    # Handle different thinking budget types
    if thinking_budget_value == "effort":
        thinking_budget = int(output_reserve * 0.4)
    elif thinking_budget_value is not None:
        thinking_budget = thinking_budget_value
    else:
        thinking_budget = 0

    # Calculate available tokens for database results
    # Context = system_message + files + database + output + thinking
    # Reserve ~500 tokens for system message
    system_message_reserve = 500

    available_tokens = (
        context_length
        - output_reserve
        - thinking_budget
        - system_message_reserve
        - file_tokens
    )

    # Apply safety factor (80% of calculated)
    max_db_tokens = int(available_tokens * 0.8)

    # Ensure minimum capacity
    max_db_tokens = max(max_db_tokens, 1000)  # At least 1k tokens for DB results

    # Determine if truncation likely needed
    # Truncation needed if budget is constrained (less than 20k tokens available)
    truncation_needed = max_db_tokens < 20_000

    return max_db_tokens, truncation_needed


def truncate_database_results(
    results: list[dict],
    max_tokens: int,
    query: str,
    database_name: str = "unknown",
) -> tuple[list[dict], bool, str]:
    """Truncate database results to fit within token budget.
    
    Intelligently truncates results while preserving data usefulness:
    1. Keeps first N rows that fit within budget
    2. Adds truncation notice with statistics
    
    Args:
        results: List of result rows/documents
        max_tokens: Maximum tokens allowed
        query: Original query
        database_name: Database name for context
    
    Returns:
        Tuple of (truncated_results, was_truncated, truncation_message)
    """
    if not results:
        return results, False, ""

    # Estimate tokens for full results
    full_tokens = estimate_database_result_tokens(results, query, database_name)

    if full_tokens <= max_tokens:
        # No truncation needed
        return results, False, ""

    # Calculate average tokens per row
    header_tokens = 200
    row_tokens = (full_tokens - header_tokens) / len(results)

    # Calculate how many rows we can keep
    available_row_tokens = max_tokens - header_tokens - 100  # Reserve 100 for truncation notice
    max_rows = max(1, int(available_row_tokens / row_tokens))

    # Truncate results
    truncated_results = results[:max_rows]

    # Build truncation message
    truncation_message = (
        f"\n\n[TRUNCATED] Original result had {len(results)} rows, "
        f"showing first {len(truncated_results)} rows to fit token budget. "
        f"Estimated tokens: {full_tokens:,} → {max_tokens:,}"
    )

    return truncated_results, True, truncation_message


def calculate_optimal_limit(
    max_tokens: int,
    estimated_tokens_per_row: int = 50,
) -> int:
    """Calculate optimal LIMIT clause value for SQL queries based on token budget.
    
    Helps prevent fetching too much data from database when token budget is constrained.
    
    Args:
        max_tokens: Maximum tokens available for results
        estimated_tokens_per_row: Estimated tokens per result row (default 50)
    
    Returns:
        Optimal LIMIT value for SQL query
    """
    # Reserve tokens for header/formatting
    header_tokens = 200
    available_tokens = max(max_tokens - header_tokens, 100)

    # Calculate max rows
    max_rows = int(available_tokens / estimated_tokens_per_row)

    # Ensure reasonable bounds
    max_rows = max(10, min(max_rows, 10_000))  # Between 10 and 10,000

    return max_rows


def get_thinking_budget(model_name: str, mode: str) -> Optional[int]:
    """Get thinking tokens for a model based on mode.

    Args:
        model_name: The model name
        mode: Performance mode - "fast", "mid", or "think"

    Returns:
        Thinking token budget, "effort" for OpenAI models, or None for fast mode
    """
    # Fast mode: no thinking
    if mode == "fast":
        return None

    # Get model's max thinking limit
    limit = THINKING_LIMITS.get(model_name)

    if limit is None:
        # Unknown model - return None to disable thinking
        return None

    # OpenAI models use effort-based reasoning
    if limit == "effort":
        return "effort"

    # Mid mode: moderate reasoning (50% of max)
    if mode == "mid":
        return limit // 2

    # Think mode: maximum reasoning budget
    if mode == "think":
        return limit

    # Unknown mode - default to fast
    return None
