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

# Set up consult7 logger
logger = logging.getLogger("consult7")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stderr)
handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
logger.addHandler(handler)


class Consult7Server(Server):
    """Extended MCP Server that stores API configuration."""

    def __init__(self, name: str, api_key: str, provider: str):
        super().__init__(name)
        self.api_key = api_key
        self.provider = provider


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
    is_oauth_provider = server.provider in ["gemini-cli", "qwen-code"]
    
    if server.api_key is None:
        if is_oauth_provider:
            # OAuth with default path
            if server.provider == "gemini-cli":
                print("OAuth Path: ~/.gemini/oauth_creds.json (default)")
            else:
                print("OAuth Path: ~/.qwen/oauth_creds.json (default)")
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
    print(f"Test Mode: fast")
    print()
    print("Running test query...")
    
    try:
        # Simple test with minimal content
        result = await consultation_impl(
            files=[],  # No files for test
            query="Say 'Connection successful' if you can read this.",
            model=test_model,
            mode="fast",
            provider=server.provider,
            api_key=server.api_key,
            output_file=None,
        )
        
        # Check if result contains error
        if result.startswith("Error:"):
            print()
            print("❌ Test FAILED")
            print(result)
            return False
        
        print()
        print("✅ Test PASSED")
        print(f"Response preview: {result[:200]}...")
        return True
        
    except Exception as e:
        print()
        print("❌ Test FAILED")
        print(f"Error: {e}")
        return False


async def main():
    """Parse command line arguments and run the server."""
    # Simple argument parsing
    args = sys.argv[1:]
    test_mode = False

    # Check for --test flag at the end
    if args and args[-1] == "--test":
        test_mode = True
        args = args[:-1]  # Remove --test from args

    # Validate arguments
    if len(args) < MIN_ARGS:
        sys.stderr.write("Error: Missing required arguments\n")
        sys.stderr.write("Usage: consult7 <provider> <api-key-or-oauth-path> [--test]\n")
        sys.stderr.write("\n")
        sys.stderr.write("Providers:\n")
        sys.stderr.write("  openrouter     - OpenRouter API (requires API key)\n")
        sys.stderr.write("  gemini-cli     - Gemini CLI OAuth (use oauth: for default path)\n")
        sys.stderr.write("  qwen-code      - Qwen Code OAuth (use oauth: for default path)\n")
        sys.stderr.write("\n")
        sys.stderr.write("Examples:\n")
        sys.stderr.write("  consult7 openrouter sk-or-v1-...\n")
        sys.stderr.write("  consult7 gemini-cli oauth:\n")
        sys.stderr.write("  consult7 qwen-code oauth:\n")
        sys.stderr.write("  consult7 gemini-cli oauth:/custom/path/oauth_creds.json\n")
        sys.stderr.write("  consult7 openrouter sk-or-v1-... --test\n")
        sys.stderr.write("\n")
        sys.stderr.write("Note: oauth: uses default paths:\n")
        sys.stderr.write("  - Gemini CLI: ~/.gemini/oauth_creds.json\n")
        sys.stderr.write("  - Qwen Code: ~/.qwen/oauth_creds.json\n")
        sys.exit(EXIT_FAILURE)

    if len(args) > MIN_ARGS + 1:
        sys.stderr.write(f"Error: Too many arguments. Expected {MIN_ARGS + 1}, got {len(args)}\n")
        sys.stderr.write("Usage: consult7 <provider> <api-key-or-oauth-path> [--test]\n")
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
    server = Consult7Server("consult7", api_key, provider)

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        """List available tools with provider-specific model examples."""
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
                    },
                    "required": ["files", "query", "model", "mode"],
                },
            )
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
        """Handle tool calls."""
        try:
            if name == "consultation":
                result = await consultation_impl(
                    arguments["files"],
                    arguments["query"],
                    arguments["model"],
                    arguments["mode"],
                    server.provider,
                    server.api_key,
                    arguments.get("output_file"),
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
        if server.provider in ["gemini-cli", "qwen-code"]:
            default_path = "~/.gemini/oauth_creds.json" if server.provider == "gemini-cli" else "~/.qwen/oauth_creds.json"
            logger.info(f"OAuth: Using default path ({default_path})")
        else:
            logger.info("API Key: Not set")
    else:
        if server.provider in ["gemini-cli", "qwen-code"]:
            logger.info(f"OAuth: Custom path ({server.api_key})")
        else:
            logger.info("API Key: Set")

    examples = ToolDescriptions.MODEL_EXAMPLES.get(server.provider, [])
    if examples:
        logger.info(f"Example models for {server.provider}:")
        for example in examples:
            logger.info(f"  - {example}")

    # Run test mode if requested
    if test_mode:
        success = await test_api_connection(server)
        sys.exit(EXIT_SUCCESS if success else EXIT_FAILURE)

    # Normal server mode
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="consult7",
                server_version=SERVER_VERSION,
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


def run():
    """Entry point for the consult7 command."""
    import asyncio

    asyncio.run(main())


if __name__ == "__main__":
    run()
