"""Database result formatting for AI consumption."""

from typing import Any

RESULT_SEPARATOR = "=" * 80
ROW_SEPARATOR = "-" * 80


def format_database_results(results: list[dict[str, Any]], query: str, database_name: str = "unknown") -> str:
    """Format database query results as plain text for AI consumption.
    
    Formats results in a structured, readable format optimized for LLM analysis:
    - Clear section headers with separators
    - Column-aligned tabular format
    - Row numbers for reference
    - Summary statistics
    
    Args:
        results: List of result rows (each row is a dictionary)
        query: The original query that produced these results
        database_name: Name of the database (for context)
    
    Returns:
        Plain text formatted results with clear separators
    """
    if not results:
        return (
            f"{RESULT_SEPARATOR}\n"
            f"DATABASE QUERY RESULTS\n"
            f"{RESULT_SEPARATOR}\n"
            f"Database: {database_name}\n"
            f"Query: {query}\n"
            f"Result: No rows returned (empty result set)\n"
            f"{RESULT_SEPARATOR}\n"
        )

    # Get column names from first row
    columns = list(results[0].keys())

    # Calculate column widths for alignment
    col_widths = {col: len(str(col)) for col in columns}
    for row in results:
        for col in columns:
            value = str(row.get(col, ''))
            col_widths[col] = max(col_widths[col], len(value))

    # Build header
    output = [
        RESULT_SEPARATOR,
        "DATABASE QUERY RESULTS",
        RESULT_SEPARATOR,
        f"Database: {database_name}",
        f"Query: {query}",
        f"Rows returned: {len(results)}",
        "",
        ROW_SEPARATOR,
    ]

    # Build column headers
    header_parts = ["Row#"]
    for col in columns:
        header_parts.append(col.ljust(col_widths[col]))
    output.append("  ".join(header_parts))
    output.append(ROW_SEPARATOR)

    # Build data rows
    for idx, row in enumerate(results, start=1):
        row_parts = [f"{idx:4d}"]
        for col in columns:
            value = str(row.get(col, 'NULL'))
            row_parts.append(value.ljust(col_widths[col]))
        output.append("  ".join(row_parts))

    # Footer
    output.extend([
        ROW_SEPARATOR,
        f"Total rows: {len(results)}",
        RESULT_SEPARATOR,
        "",
    ])

    return "\n".join(output)


def format_mongodb_results(results: list[dict[str, Any]], query: str, database_name: str = "unknown") -> str:
    """Format MongoDB query results with JSON-like structure.
    
    Args:
        results: List of MongoDB documents
        query: The original query
        database_name: Name of the database
    
    Returns:
        Formatted string with JSON document structure
    """
    if not results:
        return (
            f"{RESULT_SEPARATOR}\n"
            f"MONGODB QUERY RESULTS\n"
            f"{RESULT_SEPARATOR}\n"
            f"Database: {database_name}\n"
            f"Query: {query}\n"
            f"Result: No documents returned (empty result set)\n"
            f"{RESULT_SEPARATOR}\n"
        )

    output = [
        RESULT_SEPARATOR,
        "MONGODB QUERY RESULTS",
        RESULT_SEPARATOR,
        f"Database: {database_name}",
        f"Query: {query}",
        f"Documents returned: {len(results)}",
        "",
        ROW_SEPARATOR,
    ]

    # Format each document
    for idx, doc in enumerate(results, start=1):
        output.append(f"Document #{idx}:")
        for key, value in doc.items():
            output.append(f"  {key}: {value}")
        output.append(ROW_SEPARATOR)

    output.extend([
        f"Total documents: {len(results)}",
        RESULT_SEPARATOR,
        "",
    ])

    return "\n".join(output)
