"""Main consultation orchestration logic for Consult7."""

import asyncio
import logging
from typing import Optional

from .constants import DEFAULT_CONTEXT_LENGTH, LLM_CALL_TIMEOUT
from .file_processor import expand_file_patterns, format_content, save_output_to_file
from .token_utils import estimate_tokens, get_thinking_budget, calculate_max_file_size
from .providers import PROVIDERS

logger = logging.getLogger("consult7")


def format_combined_content(file_content: str, db_content: str, file_count: int, file_size: int) -> str:
    """Format combined file and database content with clear separators.
    
    Args:
        file_content: Formatted file content (may be empty)
        db_content: Formatted database results (may be empty)
        file_count: Number of files included
        file_size: Total file size in bytes
    
    Returns:
        Combined content with clear section separators
    """
    sections = []

    if file_content:
        sections.append(
            f"{'=' * 80}\n"
            f"FILE ANALYSIS SECTION\n"
            f"{'=' * 80}\n"
            f"Files included: {file_count} ({file_size:,} bytes)\n"
            f"{'=' * 80}\n\n"
            f"{file_content}"
        )

    if db_content:
        sections.append(
            f"\n\n{'=' * 80}\n"
            f"DATABASE ANALYSIS SECTION\n"
            f"{'=' * 80}\n\n"
            f"{db_content}"
        )

    return "\n".join(sections)


async def execute_database_queries(
    queries: list[str],
    dsn: str,
    timeout: float,
    max_rows: int,
    max_tokens: Optional[int] = None,
) -> tuple[str, int, Optional[str]]:
    """Execute database queries and return formatted results.
    
    Args:
        queries: List of SQL/database queries to execute
        dsn: Database connection string
        timeout: Query timeout in seconds
        max_rows: Maximum rows per query
        max_tokens: Optional maximum tokens for results (enables truncation)
    
    Returns:
        Tuple of (formatted_results, estimated_tokens, error_message)
    """
    from .database.connection import parse_dsn, ConnectionPool
    from .database.adapters import create_adapter

    try:
        # Parse DSN to determine database type and connection parameters
        dsn_parts = parse_dsn(dsn)
        protocol = dsn_parts["protocol"]

        # Get or create connection pool for this DSN
        pool = ConnectionPool.get_pool(dsn, pool_size=5)

        # Create adapter factory based on protocol
        def adapter_factory():
            return create_adapter(
                protocol=protocol,
                host=dsn_parts["host"],
                port=dsn_parts["port"],
                database=dsn_parts["database"],
                username=dsn_parts["username"],
                password=dsn_parts["password"],
                timeout=timeout,
                max_rows=max_rows,
            )

        # Acquire connection from pool
        adapter = pool.acquire(adapter_factory, timeout=30.0)

        try:
            # Execute all queries and collect results
            all_results = []
            truncation_warnings = []

            for query in queries:
                results = adapter.execute_query(query)

                # Apply token budget truncation if max_tokens specified
                if max_tokens and results:
                    from .token_utils import truncate_database_results
                    results, was_truncated, truncation_msg = truncate_database_results(
                        results, max_tokens, query, dsn_parts["database"]
                    )
                    if was_truncated:
                        truncation_warnings.append(truncation_msg)

                formatted = adapter.format_result(results, query)
                all_results.append(formatted)

            # Combine all results
            combined_results = "\n\n".join(all_results)

            # Add truncation warnings if any
            if truncation_warnings:
                combined_results += "\n\n" + "\n".join(truncation_warnings)

            # Estimate tokens
            total_tokens = estimate_tokens(combined_results, is_database_result=True)

            return combined_results, total_tokens, None

        finally:
            # Release connection back to pool
            pool.release(adapter)

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Database query execution failed: {error_msg}")
        return "", 0, error_msg


async def get_model_context_info(model_name: str, provider: str, api_key: Optional[str]) -> dict:
    """Get model context information from OpenRouter API."""
    try:
        # Get provider instance (always openrouter)
        if not (provider_instance := PROVIDERS.get(provider)):
            logger.warning(f"Unknown provider '{provider}'")
            return {"context_length": DEFAULT_CONTEXT_LENGTH, "provider": provider}

        # Get model info from provider API
        info = await provider_instance.get_model_info(model_name, api_key)

        if info and "context_length" in info:
            return info

        # Fallback to default if no info available
        logger.warning(
            f"Could not determine context length for {model_name}, using default of 128k tokens"
        )
        return {"context_length": DEFAULT_CONTEXT_LENGTH, "provider": provider}

    except Exception as e:
        logger.error(f"Error getting model info: {e}")
        return {"context_length": DEFAULT_CONTEXT_LENGTH, "provider": provider}


async def consultation_impl(
    files: list[str],
    query: str,
    model: str,
    mode: str,
    provider: str = "openrouter",
    api_key: Optional[str] = None,
    output_file: Optional[str] = None,
    db_queries: Optional[list[str]] = None,
    db_dsn: Optional[str] = None,
    db_timeout: Optional[float] = None,
    db_max_rows: Optional[int] = None,
) -> str:
    """Implementation of the consultation tool logic.
    
    Supports three consultation modes:
    1. Files only (existing behavior): files provided, no db_queries
    2. Database only (new): db_queries + db_dsn provided, no files
    3. Hybrid (new): both files and db_queries + db_dsn provided
    
    Args:
        files: List of file patterns to analyze
        query: User's question/analysis request
        model: Model name to use
        mode: Performance mode (fast/mid/think)
        provider: Provider name (openrouter/gemini-cli/qwen-code)
        api_key: API key or OAuth path
        output_file: Optional file to save results
        db_queries: Optional list of database queries to execute
        db_dsn: Optional database connection string
        db_timeout: Optional query timeout (default from constants)
        db_max_rows: Optional max rows per query (default from constants)
    
    Returns:
        Analysis result or error message
    """
    # Import database utilities if needed
    from .constants import DB_QUERY_TIMEOUT, DB_MAX_ROWS

    db_timeout = db_timeout or DB_QUERY_TIMEOUT
    db_max_rows = db_max_rows or DB_MAX_ROWS

    # Validate DSN availability if db_queries provided
    if db_queries and not db_dsn:
        return (
            "Error: Database queries provided but no DSN available.\n\n"
            "**CRITICAL**: This server does NOT have a default database DSN configured.\n"
            "You MUST provide the 'db_dsn' parameter in your tool call.\n\n"
            "Example: db_dsn='mysql://root:@localhost:3306/database_name'\n\n"
            "Note: If server had default DSN, you should NEVER override it.\n"
            "To configure default DSN, add to MCP config: --db-dsn mysql://root:@host:3306/db"
        )

    # Expand file patterns (may be empty for database-only mode)
    file_paths, errors = expand_file_patterns(files) if files else ([], [])

    # Get model info early for token budget calculations
    model_info = await get_model_context_info(model, provider, api_key)
    model_context_length = model_info.get("context_length", DEFAULT_CONTEXT_LENGTH)

    # Database execution (if db_queries provided)
    db_results_content = ""
    db_total_tokens = 0

    if db_queries and db_dsn:
        # Calculate database token budget based on model and file content
        from .token_utils import calculate_database_token_budget

        # Estimate file tokens (rough estimate before actual formatting)
        file_tokens = 0
        if file_paths:
            # Quick estimate: sum of file sizes / 3 (rough chars per token)
            import os
            for fp in file_paths:
                try:
                    file_tokens += os.path.getsize(fp) // 3
                except (OSError, FileNotFoundError):
                    pass

        max_db_tokens, truncation_needed = calculate_database_token_budget(
            model_context_length, mode, model, file_tokens
        )

        # Log warning if truncation likely needed
        if truncation_needed:
            logger.warning(
                f"Token budget constrained: {max_db_tokens:,} tokens available for database results. "
                f"Truncation may occur."
            )

        db_results_content, db_total_tokens, db_error = await execute_database_queries(
            db_queries, db_dsn, db_timeout, db_max_rows, max_tokens=max_db_tokens
        )
        if db_error:
            return f"Error executing database queries: {db_error}"

    # Validate that we have SOME content to analyze
    if not file_paths and not db_results_content:
        if errors:
            return "Error: No files found and no database results. Errors:\n" + "\n".join(errors)
        return "Error: No files or database queries provided for analysis"

    # Provide immediate feedback about what was found
    if not file_paths and not db_results_content:
        return "No files matching the patterns were found and no database results."

    # Calculate dynamic file size limits based on model's context window (model_info already fetched above)
    max_total_size, max_file_size = calculate_max_file_size(model_context_length, mode, model)

    # Format file content with model-specific limits (if files provided)
    file_content = ""
    total_size = 0
    if file_paths:
        file_content, total_size = format_content(file_paths, errors, max_total_size, max_file_size)

    # Combine files and database results with clear separators
    combined_content = format_combined_content(file_content, db_results_content, len(file_paths), total_size)

    # Determine thinking mode based on mode parameter
    thinking_budget_value = get_thinking_budget(model, mode)
    thinking_mode = thinking_budget_value is not None

    # Add size info that will be part of the query
    size_info = "\n\n---\n"
    if file_paths:
        size_info += f"Files: {total_size:,} bytes from {len(file_paths)} files"
    if db_results_content:
        size_info += f"{' | ' if file_paths else ''}Database: {len(db_results_content):,} bytes ({db_total_tokens:,} tokens estimated)"

    # Estimate tokens for the full input
    full_content = combined_content + size_info + f"\n\nQuery: {query}"
    estimated_tokens = estimate_tokens(full_content)
    token_info = f"\nEstimated tokens: ~{estimated_tokens:,}"
    if model_context_length:
        token_info += f" (Model limit: {model_context_length:,} tokens)"

    # Call appropriate LLM based on provider
    thinking_budget = None
    provider_instance = PROVIDERS.get(provider)
    if not provider_instance:
        return f"Error: Unknown provider '{provider}'"

    # Call the provider with generous timeout protection (10 minutes)
    try:
        async with asyncio.timeout(LLM_CALL_TIMEOUT):
            response, error, thinking_budget = await provider_instance.call_llm(
                combined_content + size_info,
                query,
                model,
                api_key,
                thinking_mode,
                thinking_budget_value,
            )
    except asyncio.TimeoutError:
        metadata_parts = []
        if file_paths:
            metadata_parts.append(f"{len(file_paths)} files ({total_size:,} bytes)")
        if db_results_content:
            metadata_parts.append(f"database results ({db_total_tokens:,} tokens)")
        metadata_summary = " + ".join(metadata_parts) if metadata_parts else "no content"

        return (
            f"Error: Request timed out after {LLM_CALL_TIMEOUT} seconds "
            f"(10 minutes). This is an extremely long time - "
            f"the model or API may be having issues.\n\n"
            f"Collected {metadata_summary}{token_info}"
        )

    # Add reasoning budget info if applicable (even for errors)
    if thinking_budget is not None:
        if thinking_budget == -1:
            # Special marker for OpenAI effort-based reasoning
            token_info += ", reasoning mode: effort=high (~80% of output budget)"
        elif thinking_budget > 0:
            # Calculate percentage of maximum possible reasoning tokens
            # Import these only when needed to avoid circular imports
            from .token_utils import (
                FLASH_MAX_THINKING_TOKENS,
                MAX_REASONING_TOKENS,
            )

            # Determine max reasoning based on model
            if "gemini" in model.lower() and "flash" in model.lower():
                max_reasoning = FLASH_MAX_THINKING_TOKENS  # 24,576
            else:
                max_reasoning = MAX_REASONING_TOKENS  # 32,000 (Anthropic, others)

            percentage = (thinking_budget / max_reasoning) * 100
            token_info += (
                f", reasoning budget: {thinking_budget:,} tokens ({percentage:.1f}% of max)"
            )
        else:
            token_info += ", reasoning disabled (insufficient context)"

    if error:
        metadata_parts = []
        if file_paths:
            metadata_parts.append(f"{len(file_paths)} files ({total_size:,} bytes)")
        if db_results_content:
            metadata_parts.append(f"database results ({db_total_tokens:,} tokens)")
        metadata_summary = " + ".join(metadata_parts) if metadata_parts else "no content"

        return (
            f"Error calling {provider} LLM: {error}\n\n"
            f"Collected {metadata_summary}{token_info}"
        )

    # Handle output file if specified
    if output_file:
        # Save just the LLM response (without the metadata)
        save_path, save_error = save_output_to_file(response, output_file)

        if save_error:
            return f"Error saving output: {save_error}"

        # Return brief confirmation message
        return f"Result has been saved to {save_path}"

    # Normal mode: return full response with metadata
    mode_str = f" [{mode}]" if mode != "fast" else ""

    # Build metadata summary
    metadata_parts = []
    if file_paths:
        metadata_parts.append(f"{len(file_paths)} files ({total_size:,} bytes)")
    if db_results_content:
        metadata_parts.append(f"database queries ({len(db_queries)} queries, {db_total_tokens:,} tokens)")

    metadata_summary = " + ".join(metadata_parts) if metadata_parts else "no content"

    return (
        f"{response}\n\n---\n"
        f"Processed {metadata_summary} "
        f"with {model}{mode_str} ({provider}){token_info}"
    )
