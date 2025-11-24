"""Consult7 MCP server - Analyze large file collections with AI models."""

import sys
import logging
from mcp.server import Server
import mcp.server.stdio
import mcp.types as types
from mcp.server.models import InitializationOptions
from mcp.server.lowlevel import NotificationOptions

# Import constants
from .constants import SERVER_VERSION, EXIT_SUCCESS, EXIT_FAILURE, MIN_ARGS, TEST_MODELS
from .tool_definitions import ToolDescriptions
from .providers import PROVIDERS
from .consultation import consultation_impl
from typing import Optional

# Set up consult7 logger with flushing
logger = logging.getLogger("consult7")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stderr)
handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
handler.flush = lambda: sys.stderr.flush()  # Force flush after each log
logger.addHandler(handler)

# Also force stderr to be unbuffered
sys.stderr.reconfigure(line_buffering=True) if hasattr(sys.stderr, 'reconfigure') else None


class Consult7Server(Server):
    """Extended MCP Server that stores API configuration."""

    def __init__(self, name: str, api_key: str, provider: str, db_dsn: Optional[str] = None):
        super().__init__(name)
        self.api_key = api_key
        self.provider = provider
        self.db_dsn = db_dsn


async def test_api_connection(server: Consult7Server) -> bool:
    """Test API connection with a simple query.
    
    Args:
        server: Consult7Server instance
        
    Returns:
        True if test successful, False otherwise
    """
    print()
    print(f"Testing {server.provider} API connection...")

    # For OAuth providers, None means use default path (which is valid)
    is_oauth_provider = server.provider in ["gemini-cli", "qwen-code", "github-copilot"]

    # Special handling for GitHub Copilot - check token exists first (only in interactive test mode)
    if server.provider == "github-copilot":
        from .oauth.token_storage import TokenStorage
        from .providers.github_copilot import GitHubCopilotProvider

        token_storage = TokenStorage()
        token_data = token_storage.load_token("github-copilot")

        if not token_data:
            print("OAuth Token: Not found")
            print()
            print("[WARNING] No GitHub Copilot token found!")
            print("          You need to authenticate first.")
            print()

            # Check if running interactively (has stdin)
            import sys
            if sys.stdin and sys.stdin.isatty():
                # Ask user if they want to authenticate now
                try:
                    response = input("Would you like to authenticate now? (yes/no): ").strip().lower()
                    if response in ["yes", "y"]:
                        copilot = GitHubCopilotProvider()
                        await copilot.authenticate()
                        print()
                        print("[SUCCESS] Authentication successful! Continuing with test...")
                        print()
                    else:
                        print()
                        print("Test cancelled. Authenticate later with:")
                        print("  consult7 github-copilot oauth:")
                        return False
                except (KeyboardInterrupt, EOFError):
                    print("\n\nTest cancelled.")
                    return False
            else:
                # Non-interactive mode (e.g., MCP server) - just show error
                print()
                print("Cannot authenticate in non-interactive mode.")
                print("Please authenticate first with:")
                print("  consult7 github-copilot oauth:")
                return False

    if server.api_key is None:
        if is_oauth_provider:
            # OAuth with default path
            if server.provider == "gemini-cli":
                print("OAuth Path: ~/.gemini/oauth_creds.json (default)")
            elif server.provider == "qwen-code":
                print("OAuth Path: ~/.qwen/oauth_creds.json (default)")
            elif server.provider == "github-copilot":
                print("OAuth Token: ~/.consult7/github-copilot_oauth_token.enc (encrypted)")
        else:
            # Non-OAuth provider needs API key
            print("API Key: Not set")
            print()
            print("Error: No API key provided!")
            print("Usage: consult7 openrouter <your-api-key> --test")
            return False
    else:
        # API key or custom OAuth path is provided
        if is_oauth_provider:
            print(f"OAuth Path: {server.api_key}")
        else:
            # Mask API key for security
            masked = server.api_key[:8] + "..." if len(server.api_key) > 8 else "***"
            print(f"API Key: {masked}")

    # Get test model
    test_model = TEST_MODELS.get(server.provider)
    if not test_model:
        print(f"Error: No test model configured for provider '{server.provider}'")
        return False

    print(f"Test Model: {test_model}")
    print("Test Mode: fast")
    print()
    print("Running test query...")

    try:
        # Create a simple test file content
        test_content = "# Test Python file\ndef hello():\n    print('Hello, World!')\n"
        
        # For test mode, we bypass the validation by calling the provider directly
        # This ensures we can test the API connection without hitting the validation error
        from .providers import PROVIDERS
        
        provider_instance = PROVIDERS[server.provider]
        
        # Call the provider directly with test query
        result = await provider_instance.call_llm(
            content=test_content,
            query="Analyze this code and say 'Connection successful'.",
            model_name=test_model,
            api_key=server.api_key,
            thinking_mode=False,
            thinking_budget=None,
        )
        
        # Providers return (response, error_message, thinking_used) tuple
        if isinstance(result, tuple) and len(result) >= 2:
            response = result[0]
            error_message = result[1]
        else:
            response = str(result)
            error_message = None
        
        if error_message:
            print()
            print("[FAILED] Test FAILED")
            print(f"Error: {error_message}")
            return False

        print()
        print("[PASSED] Test PASSED")
        if response:
            preview = response[:200] if len(response) > 200 else response
            print(f"Response: {preview}")
        return True

    except Exception as e:
        print()
        print("[FAILED] Test FAILED")
        print(f"Error: {e}")
        import traceback
        logger.debug(f"Test error traceback: {traceback.format_exc()}")
        return False


def detect_consultation_mode(
    files: list[str],
    db_queries: Optional[list[str]],
    db_dsn_arg: Optional[str]
) -> str:
    """Detect consultation mode based on provided parameters.
    
    Args:
        files: List of file patterns
        db_queries: Optional database queries
        db_dsn_arg: Optional database DSN from arguments (NOT from server config)
    
    Returns:
        Mode string: "files-only", "database-only", "hybrid", or "invalid"
    """
    has_files = files and len(files) > 0
    has_db_queries = db_queries and len(db_queries) > 0
    # CRITICAL: Only consider db_dsn_arg (explicit user parameter), not server.db_dsn
    has_db_dsn_arg = db_dsn_arg is not None and db_dsn_arg.strip() != ""

    # Determine mode based on what's provided
    # Key: db_queries is the primary indicator of database mode, not db_dsn
    if has_files and has_db_queries:
        # Has files + db_queries = hybrid mode
        return "hybrid"
    elif has_db_queries:
        # Has db_queries (no files) = database-only mode
        return "database-only"
    elif has_files:
        # Has only files = files-only mode (even if server has default db_dsn)
        return "files-only"
    else:
        # Nothing provided = invalid
        return "invalid"


def validate_consultation_params(
    files: list[str],
    db_queries: Optional[list[str]],
    db_dsn_arg: Optional[str]
) -> Optional[str]:
    """Validate consultation parameters for different modes.
    
    Args:
        files: List of file patterns
        db_queries: Optional database queries
        db_dsn_arg: Optional database DSN from arguments (NOT from server config)
    
    Returns:
        Error message if validation fails, None if valid
    """
    # Detect mode based on EXPLICIT parameters only (ignore server.db_dsn)
    mode = detect_consultation_mode(files, db_queries, db_dsn_arg)

    # Validate based on detected mode
    if mode == "invalid":
        return (
            "Invalid consultation mode: must provide either files, or db_queries, or both\n"
            "  Hint: Choose one of three consultation modes:\n"
            "  • Files-only mode: Provide 'files' parameter\n"
            "  • Database-only mode: Provide 'db_queries' parameter (db_dsn optional, uses env vars if not provided)\n"
            "  • Hybrid mode: Provide 'files' AND 'db_queries' parameters (db_dsn optional, uses env vars if not provided)\n"
            "  Example (files-only): files=['/path/to/*.py']\n"
            "  Example (database-only with DSN): db_queries=['SELECT * FROM users'], db_dsn='mysql://user:pass@host/db'\n"
            "  Example (database-only with env vars): db_queries=['SELECT * FROM users'] (db_dsn uses environment variables)\n"
            "  Example (hybrid): files=['/path/*.py'], db_queries=['SELECT...'], db_dsn='mysql://...' or omit db_dsn to use env vars"
        )

    # Additional validation for database modes
    # Key: Only validate if user explicitly provided db_dsn_arg without db_queries
    if mode in ("database-only", "hybrid"):
        has_db_queries = db_queries and len(db_queries) > 0
        has_db_dsn_arg_explicit = db_dsn_arg is not None and db_dsn_arg.strip() != ""

        # Validate: if user explicitly provided db_dsn_arg, they must also provide db_queries
        if has_db_dsn_arg_explicit and not has_db_queries:
            return (
                f"Invalid {mode} mode: Missing required parameter 'db_queries'\n"
                f"  Hint: When using db_dsn, you must also provide db_queries\n"
                f"  Example: db_queries=[\"SELECT * FROM users LIMIT 10\"]"
            )

    return None


async def main():
    """Parse command line arguments and run the server."""
    print("DEBUG: main() started", file=sys.stderr, flush=True)

    # Simple argument parsing
    args = sys.argv[1:]
    print(f"DEBUG: args={args}", file=sys.stderr, flush=True)
    test_mode = False
    db_dsn = None

    # Parse optional flags
    i = 0
    while i < len(args):
        if args[i] == "--test":
            test_mode = True
            args.pop(i)
        elif args[i] == "--db-dsn":
            if i + 1 >= len(args):
                sys.stderr.write("Error: --db-dsn requires a value\n")
                sys.exit(EXIT_FAILURE)
            db_dsn = args[i + 1]
            args.pop(i)  # Remove --db-dsn
            args.pop(i)  # Remove DSN value
        else:
            i += 1

    # Validate arguments
    if len(args) < MIN_ARGS:
        sys.stderr.write("Error: Missing required arguments\n")
        sys.stderr.write("Usage: consult7 <provider> <api-key-or-oauth-path> [--db-dsn <dsn>] [--test]\n")
        sys.stderr.write("\n")
        sys.stderr.write("Providers:\n")
        sys.stderr.write("  openrouter      - OpenRouter API (requires API key)\n")
        sys.stderr.write("  gemini-cli      - Gemini CLI OAuth (use oauth: for default path)\n")
        sys.stderr.write("  qwen-code       - Qwen Code OAuth (use oauth: for default path)\n")
        sys.stderr.write("  github-copilot  - GitHub Copilot OAuth (requires authentication)\n")
        sys.stderr.write("\n")
        sys.stderr.write("Examples:\n")
        sys.stderr.write("  consult7 openrouter sk-or-v1-...\n")
        sys.stderr.write("  consult7 gemini-cli oauth:\n")
        sys.stderr.write("  consult7 qwen-code oauth:\n")
        sys.stderr.write("  consult7 qwen-code oauth: --db-dsn mysql://root:@host:3306/db\n")
        sys.stderr.write("  consult7 gemini-cli oauth:/custom/path/oauth_creds.json\n")
        sys.stderr.write("  consult7 github-copilot oauth:\n")
        sys.stderr.write("  consult7 openrouter sk-or-v1-... --test\n")
        sys.stderr.write("\n")
        sys.stderr.write("Optional Flags:\n")
        sys.stderr.write("  --db-dsn <dsn>  - Database connection string for hybrid consultation\n")
        sys.stderr.write("                    Format: protocol://user:pass@host:port/database\n")
        sys.stderr.write("                    Example: mysql://root:@10.243.230.71:3306/mydb\n")
        sys.stderr.write("  --test          - Test API connection and exit\n")
        sys.stderr.write("\n")
        sys.stderr.write("GitHub Copilot Setup:\n")
        sys.stderr.write("  1. Authenticate:  consult7 github-copilot oauth: --test\n")
        sys.stderr.write("     (Answer 'yes' when prompted)\n")
        sys.stderr.write("  2. Use normally:  consult7 github-copilot oauth:\n")
        sys.stderr.write("\n")
        sys.stderr.write("Note: oauth: uses default paths:\n")
        sys.stderr.write("  - Gemini CLI: ~/.gemini/oauth_creds.json\n")
        sys.stderr.write("  - Qwen Code: ~/.qwen/oauth_creds.json\n")
        sys.stderr.write("  - GitHub Copilot: ~/.consult7/github-copilot_oauth_token.enc\n")
        sys.exit(EXIT_FAILURE)

    if len(args) > MIN_ARGS:
        sys.stderr.write(f"Error: Too many arguments\n")
        sys.stderr.write("Usage: consult7 <provider> <api-key-or-oauth-path> [--db-dsn <dsn>] [--test]\n")
        sys.exit(EXIT_FAILURE)

    # Parse provider and api key/oauth path
    provider = args[0]
    api_key = args[1] if len(args) > 1 else None

    # Handle oauth: prefix for OAuth-based providers
    # oauth: -> use default path (None)
    # oauth:/path/to/creds -> use custom path
    if api_key and api_key.startswith("oauth:"):
        oauth_path = api_key[6:]  # Remove 'oauth:' prefix
        api_key = oauth_path if oauth_path else None

    # Validate provider
    if provider not in PROVIDERS:
        sys.stderr.write(f"Error: Unknown provider '{provider}'\n")
        sys.stderr.write(f"Supported providers: {', '.join(PROVIDERS.keys())}\n")
        sys.exit(EXIT_FAILURE)

    # Create server with stored configuration
    print(f"DEBUG: Creating server - provider={provider}, api_key={api_key}, db_dsn={db_dsn}", file=sys.stderr, flush=True)
    server = Consult7Server("consult7", api_key, provider, db_dsn)
    print("DEBUG: Server created", file=sys.stderr, flush=True)

    print("DEBUG: Registering handlers...", file=sys.stderr, flush=True)

    @server.list_resources()
    async def list_resources() -> list[types.Resource]:
        """List available resources (none for this server)."""
        print("DEBUG: list_resources called", file=sys.stderr, flush=True)
        return []

    @server.list_prompts()
    async def list_prompts() -> list[types.Prompt]:
        """List available prompts (none for this server)."""
        print("DEBUG: list_prompts called", file=sys.stderr, flush=True)
        return []

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        """List available tools with provider-specific model examples."""
        print("DEBUG: list_tools called", file=sys.stderr, flush=True)
        return [
            types.Tool(
                name="consultation",
                description=ToolDescriptions.get_consultation_tool_description(server.provider),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "files": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": ToolDescriptions.get_files_description(),
                        },
                        "query": {
                            "type": "string",
                            "description": ToolDescriptions.get_query_description(),
                        },
                        "model": {
                            "type": "string",
                            "description": (
                                ToolDescriptions.get_model_parameter_description(server.provider)
                            ),
                        },
                        "mode": {
                            "type": "string",
                            "enum": ["fast", "mid", "think"],
                            "description": (
                                "Performance mode: 'fast' (no reasoning, fastest), "
                                "'mid' (moderate reasoning), 'think' (maximum reasoning)"
                            ),
                        },
                        "output_file": {
                            "type": "string",
                            "description": ToolDescriptions.get_output_file_description(),
                        },
                        "db_queries": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": ToolDescriptions.get_db_queries_description(
                                has_database_in_dsn=bool(server.db_dsn and server.db_dsn.count('/') >= 3)
                            ),
                        },
                        "db_dsn": {
                            "type": "string",
                            "description": ToolDescriptions.get_db_dsn_description(
                                has_default_dsn=bool(server.db_dsn)
                            ),
                        },
                        "db_timeout": {
                            "type": "number",
                            "description": ToolDescriptions.get_db_timeout_description(),
                        },
                        "db_max_rows": {
                            "type": "integer",
                            "description": ToolDescriptions.get_db_max_rows_description(),
                        },
                    },
                    "required": ["query", "model", "mode"],
                },
            )
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
        """Handle tool calls."""
        print(f"DEBUG: call_tool invoked: {name}", file=sys.stderr, flush=True)
        try:
            if name == "consultation":
                # Extract parameters
                files = arguments.get("files", [])
                db_queries = arguments.get("db_queries")
                db_dsn_arg = arguments.get("db_dsn")  # Explicit user parameter
                
                # Validate consultation mode using EXPLICIT parameters only
                # This prevents server.db_dsn from triggering validation errors in files-only mode
                validation_error = validate_consultation_params(files, db_queries, db_dsn_arg)
                if validation_error:
                    return [types.TextContent(type="text", text=f"Error: {validation_error}")]

                # AFTER validation, merge with server's db_dsn if not provided
                db_dsn_final = db_dsn_arg if db_dsn_arg is not None else server.db_dsn

                result = await consultation_impl(
                    files,
                    arguments["query"],
                    arguments["model"],
                    arguments["mode"],
                    server.provider,
                    server.api_key,
                    arguments.get("output_file"),
                    db_queries,
                    db_dsn_final,  # Use merged DSN
                    arguments.get("db_timeout"),
                    arguments.get("db_max_rows"),
                )
                return [types.TextContent(type="text", text=result)]
            else:
                return [types.TextContent(type="text", text=f"Error: Unknown tool '{name}'")]
        except Exception as e:
            # Log the full error for debugging
            logger.error(f"Error in {name}: {type(e).__name__}: {str(e)}")

            # Simple error message mapping
            error_str = str(e).lower()
            if any(x in error_str for x in ["connection", "network", "timeout", "unreachable"]):
                error_msg = "Network error. Please check your internet connection."
            elif any(x in error_str for x in ["unauthorized", "401", "403", "invalid api"]):
                error_msg = "Invalid API key. Please check your credentials."
            elif any(x in error_str for x in ["rate limit", "429", "quota"]):
                error_msg = "Rate limit exceeded. Please wait and try again."
            elif "not found" in error_str and "model" in error_str:
                error_msg = "Model not found. Please check the model name."
            elif any(x in error_str for x in ["too large", "exceeds", "context"]):
                error_msg = "Content too large. Try using fewer files or a larger context model."
            else:
                # Return the original error if no mapping
                error_msg = str(e)

            return [types.TextContent(type="text", text=f"Error: {error_msg}")]

    # Show startup information
    logger.info("Starting Consult7 MCP Server")
    logger.info(f"Provider: {server.provider}")

    # Show API key/OAuth status
    if server.api_key is None:
        if server.provider in ["gemini-cli", "qwen-code", "github-copilot"]:
            if server.provider == "gemini-cli":
                default_path = "~/.gemini/oauth_creds.json"
            elif server.provider == "qwen-code":
                default_path = "~/.qwen/oauth_creds.json"
            else:  # github-copilot
                default_path = "~/.consult7/github-copilot_oauth_token.enc"
            logger.info(f"OAuth: Using default path ({default_path})")
        else:
            logger.info("API Key: Not set")
    else:
        if server.provider in ["gemini-cli", "qwen-code", "github-copilot"]:
            logger.info(f"OAuth: Custom path ({server.api_key})")
        else:
            logger.info("API Key: Set")

    # Show database DSN status
    if server.db_dsn:
        # Mask password in DSN for security
        masked_dsn = server.db_dsn
        if "@" in masked_dsn and "://" in masked_dsn:
            # Format: protocol://user:pass@host:port/db
            parts = masked_dsn.split("://", 1)
            if len(parts) == 2 and "@" in parts[1]:
                protocol = parts[0]
                rest = parts[1]
                auth_host = rest.split("@", 1)
                if ":" in auth_host[0]:
                    user = auth_host[0].split(":")[0]
                    masked_dsn = f"{protocol}://{user}:***@{auth_host[1]}"
        logger.info(f"Database DSN: {masked_dsn}")

    examples = ToolDescriptions.MODEL_EXAMPLES.get(server.provider, [])
    if examples:
        logger.info(f"Example models for {server.provider}:")
        for example in examples:
            logger.info(f"  - {example}")

    print(f"DEBUG: test_mode={test_mode}", file=sys.stderr, flush=True)

    # Run test mode if requested
    if test_mode:
        print("DEBUG: Running test mode", file=sys.stderr, flush=True)
        success = await test_api_connection(server)
        sys.exit(EXIT_SUCCESS if success else EXIT_FAILURE)

    print("DEBUG: Entering normal server mode", file=sys.stderr, flush=True)
    # Normal server mode
    try:
        # Force flush to ensure logs appear
        print("DEBUG: Starting MCP stdio server...", file=sys.stderr, flush=True)
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            print("DEBUG: Stdio server created, running server.run()...", file=sys.stderr, flush=True)
            
            # Build instructions dynamically based on server configuration
            instructions = []
            if server.db_dsn:
                instructions.append(f"**Database Configuration**: Server has DEFAULT database DSN configured. NEVER provide 'db_dsn' parameter unless user explicitly requests different database.")
            else:
                instructions.append(f"**Database Configuration**: Server has NO default database DSN. You MUST provide 'db_dsn' parameter when using database queries.")
            
            init_options = InitializationOptions(
                server_name="consult7",
                server_version=SERVER_VERSION,
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
                instructions="\n".join(instructions),
            )
            print(f"DEBUG: InitializationOptions created: {init_options}", file=sys.stderr, flush=True)
            await server.run(
                read_stream,
                write_stream,
                init_options,
            )
            print("DEBUG: Server.run() completed", file=sys.stderr, flush=True)
    except Exception as e:
        print(f"ERROR: MCP Server error: {type(e).__name__}: {str(e)}", file=sys.stderr, flush=True)
        import traceback
        print(traceback.format_exc(), file=sys.stderr, flush=True)
        sys.exit(EXIT_FAILURE)


def run():
    """Entry point for the consult7 command."""
    import asyncio

    asyncio.run(main())


if __name__ == "__main__":
    run()
