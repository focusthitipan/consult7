"""Tool descriptions and model examples for Consult7 MCP server."""


class ToolDescriptions:
    """Centralized management of tool descriptions and model examples."""

    MODEL_EXAMPLES = {
        "openrouter": [
            '"openai/gpt-5.1" (GPT-5.1, 400k context)',
            '"google/gemini-2.5-pro" (Gemini Pro, 1M context)',
            '"google/gemini-2.5-flash" (Gemini Flash, 1M context)',
            '"google/gemini-2.5-flash-lite" (Gemini Flash Lite, 1M context)',
            '"anthropic/claude-sonnet-4.5" (Claude Sonnet 4.5, 1M context)',
            '"anthropic/claude-opus-4.1" (Claude Opus 4.1, 200k context)',
            '"x-ai/grok-4" (Grok 4, 256k context)',
            '"x-ai/grok-4-fast" (Grok 4 Fast, 2M context)',
        ],
        "gemini-cli": [
            '"gemini-2.5-flash" (Fast response ~2s, 1M context, OAuth free)',
            '"gemini-2.5-flash-lite" (Ultra fast, lightweight, 1M context, OAuth free)',
            '"gemini-2.5-pro" (High quality ~25s, 1M context, OAuth free)',
        ],
        "qwen-code": [
            '"qwen3-coder-plus" (High-performance code analysis, 1M context, OAuth)',
            '"qwen3-coder-flash" (Fast code analysis optimized for speed, 1M context, OAuth)',
        ],
        "github-copilot": [
            '"gpt-4o" (128k/16k, general purpose)',
            '"gpt-4.1" (128k/16k, improved reasoning)',
            '"gpt-5" (128k/16k, flagship)',
            '"gpt-5-mini" (128k/64k, fast + high output)',
            '"gpt-5.1" (128k/16k, latest GPT-5)',
            '"claude-haiku-4.5" (128k/16k, fast)',
            '"claude-sonnet-4" (128k/16k, balanced)',
            '"claude-sonnet-4.5" (128k/16k, best quality)',
            '"gemini-2.5-pro" (128k/64k, high quality)',
            '"gemini-3-pro-preview" (128k/64k, preview model)',
            '"grok-code-fast-1" (128k/10k, high output)',
        ],
    }

    @classmethod
    def get_consultation_tool_description(cls, provider: str) -> str:
        """Get the main description for the consultation tool."""
        provider_notes = cls._get_provider_notes(provider)

        return f"""Analyze files and/or database with an LLM - supports three modes:
1. Files only: Provide files parameter (existing behavior)
2. Database only: Provide db_queries + db_dsn parameters (new)
3. Hybrid: Provide both files and db_queries + db_dsn (new)

STATELESS: Each call must contain complete absolute paths. No context is remembered.

TIPS:
- Hard questions: Spawn 3 parallel calls with varied query formulations
- Long instructions: Put them in a file, include in files list, keep query short

Quick mnemonics:
- gptt = openai/gpt-5.1 + think (latest GPT, deep reasoning) [OpenRouter]
- gemt = google/gemini-2.5-pro + think (Gemini Pro, deep reasoning) [OpenRouter]
- gemf = google/gemini-2.5-flash-lite + fast (ultra fast) [OpenRouter]
- gcli = gemini-2.5-flash + mid (OAuth, free tier) [Gemini CLI]
- qwen = qwen-coder-turbo-latest + fast (OAuth, code-focused) [Qwen Code]

{provider_notes}

Files: Absolute paths, wildcards only in filenames (e.g., /path/*.py not /*/path/*.py)
Database: Read-only queries only (SELECT, SHOW, DESCRIBE, EXPLAIN)
Ignores: __pycache__, .env, secrets.py, .DS_Store, .git, node_modules
Limits: Dynamic per model - each model optimized for its full context capacity"""

    @classmethod
    def get_model_parameter_description(cls, provider: str) -> str:
        """Get the model parameter description with provider-specific examples."""
        examples = cls.MODEL_EXAMPLES.get(provider, [])

        # Show all 8 flagship models
        model_desc = "Model name. Options:\n"
        for example in examples:
            model_desc += f"  {example}\n"

        return model_desc.rstrip()

    @classmethod
    def get_files_description(cls) -> str:
        """Get the files parameter description."""
        return 'Absolute file paths or patterns. Example: ["/path/src/*.py", "/path/README.md"]'

    @classmethod
    def get_query_description(cls) -> str:
        """Get the query parameter description."""
        return "Your question about the files"

    @classmethod
    def get_output_file_description(cls) -> str:
        """Get the output_file parameter description."""
        return (
            "Optional: Save response to file (adds _updated suffix if exists). "
            "Tip: For code files, prompt the LLM to return raw code without markdown formatting"
        )

    @classmethod
    def get_db_queries_description(cls, has_database_in_dsn: bool = False) -> str:
        """Get the db_queries parameter description.
        
        Args:
            has_database_in_dsn: Whether the server's DSN includes database name
        """
        if has_database_in_dsn:
            # Server DSN has database - do NOT use USE
            return (
                "Optional: List of database queries to execute (requires db_dsn). "
                "Only read-only operations allowed (SELECT, SHOW, DESCRIBE, EXPLAIN). "
                "\n\n✅ **Server's DSN includes database name** - Database already selected. "
                "Start queries directly. Do NOT use database selection commands. "
                "\n\nExamples:\n"
                "• MySQL: [\"SHOW TABLES\", \"SELECT * FROM users LIMIT 10\"]\n"
                "• PostgreSQL: [\"SELECT * FROM pg_tables WHERE schemaname='public'\", \"SELECT * FROM users\"]\n"
                "• MongoDB: [{\"find\": \"users\"}, {\"aggregate\": \"orders\"}]\n"
                "• SQLite: [\"SELECT name FROM sqlite_master WHERE type='table'\", \"SELECT * FROM users\"]"
            )
        else:
            # Server DSN has NO database - MUST select database first
            return (
                "Optional: List of database queries to execute (requires db_dsn). "
                "Only read-only operations allowed (SELECT, SHOW, DESCRIBE, EXPLAIN). "
                "\n\n⚠️ **CRITICAL - Server's DSN does NOT include database name**. "
                "Database selection required:\n"
                "• MySQL/MariaDB: First query must be 'USE database_name'\n"
                "  Example: [\"USE smartfactory360\", \"SHOW TABLES\", \"SELECT * FROM users\"]\n"
                "• PostgreSQL: First query must be '\\\\c database_name' OR specify database in DSN\n"
                "• MongoDB: Database MUST be in DSN (mongodb://host:port/database) - cannot select via query\n"
                "• SQLite: Database is the file path in DSN (sqlite:///path/to/db.db) - no selection needed"
            )

    @classmethod
    def get_db_dsn_description(cls, has_default_dsn: bool = False) -> str:
        """Get the db_dsn parameter description.
        
        Args:
            has_default_dsn: Whether the server has a default DSN configured
        """
        if has_default_dsn:
            # Server HAS default DSN - strongly discourage overriding
            return (
                "Optional: Database connection string. "
                "**CRITICAL - THIS SERVER HAS DEFAULT DSN CONFIGURED**: "
                "NEVER provide this parameter unless user EXPLICITLY says 'use database at [different-dsn]' or 'connect to [other-server]'. "
                "Omit this parameter entirely to use the pre-configured DSN."
            )
        else:
            # Server has NO default DSN - must provide it
            return (
                "**REQUIRED**: Database connection string. "
                "**CRITICAL - THIS SERVER HAS NO DEFAULT DSN**: "
                "You MUST provide this parameter when using database queries. "
                "Example: db_dsn='mysql://root:@localhost:3306/database_name'"
                "\n\nFormat: protocol://user:password@host:port/database. "
                "Supported protocols: mysql, postgresql, sqlite, mongodb. "
                "\n\n**IMPORTANT - No Database in DSN**: "
                "If DSN does not include database name (e.g., mysql://root:@localhost:3306), "
                "you MUST select database first: "
                "MySQL: Add 'USE database_name' as first query. "
                "PostgreSQL: Add '\\c database_name' as first query. "
                "MongoDB: Queries fail if database not in DSN. "
                "SQLite: Always requires file path."
            )

    @classmethod
    def get_db_timeout_description(cls) -> str:
        """Get the db_timeout parameter description."""
        return "Optional: Query timeout in seconds (default: 30)"

    @classmethod
    def get_db_max_rows_description(cls) -> str:
        """Get the db_max_rows parameter description."""
        return "Optional: Maximum rows per query (default: 10000)"

    @classmethod
    def _get_provider_notes(cls, provider: str) -> str:
        """Get provider-specific notes."""
        base_modes = (
            "Performance Modes (use 'mode' parameter):\n"
            "- fast: No reasoning, fastest\n"
            "- mid: Moderate reasoning\n"
            "- think: Maximum reasoning for deepest analysis"
        )

        if provider == "github-copilot":
            return (
                f"{base_modes}\n\n"
                "Authentication: GitHub Copilot uses OAuth Device Flow.\n"
                "- First run: Use 'oauth:' to trigger device flow (opens browser)\n"
                "- Subsequent runs: Use 'oauth:' (auto-loads stored token)\n"
                "- Custom token path: 'oauth:/custom/path.json'\n"
                "- Token stored securely with AES-256-GCM encryption"
            )

        return base_modes
