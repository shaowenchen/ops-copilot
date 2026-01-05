#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ops Copilot - AI-powered DevOps assistant with MCP tool integration
"""

import os
import sys
import argparse
from typing import Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ops_copilot.utils.logging import setup_logging, get_logger
from ops_copilot.config.config_loader import ConfigLoader
from ops_copilot.tools.mcp_tool import MCPTool
from ops_copilot.core.openai_client import OpenAIClient
from ops_copilot.core.chat import Chat

logger = get_logger(__name__)

WELCOME_MSG = 'Welcome to Ops-copilot. Please type "exit" or "q" to quit.'
QUIT_MSG = "Goodbye!"
PROMPT = "Ops-copilot> "


def mask_key(key: str) -> str:
    """Mask API key for display"""
    if not key:
        return "(empty)"
    if len(key) <= 8:
        return "***"
    return key[:4] + "..." + key[len(key)-4:]


def get_env_var(name: str, default: Optional[str] = None) -> Optional[str]:
    """Get environment variable with fallback"""
    return os.environ.get(name, default)


def parse_timeout(timeout_str: str) -> str:
    """Validate timeout string format"""
    import re
    if not re.match(r'^\d+[smhd]$', timeout_str):
        raise ValueError(f"Invalid timeout format: {timeout_str}. Expected format like '30s', '1m', '2h'.")
    return timeout_str


def create_copilot(args):
    """Create and run copilot chat"""
    print(WELCOME_MSG)
    
    # Setup logging
    log_level = "DEBUG" if args.verbose else "INFO"
    setup_logging(log_level)
    
    # Load configuration (priority: args > env > config file)
    config_loader = ConfigLoader(config_file=args.config)
    config_loader.load_config()
    
    # Get MCP configuration (priority: args > env > config file)
    mcp_config = config_loader.get_mcp_config()
    mcp_server = args.mcp_server or get_env_var('MCP_SERVER_URL') or mcp_config.server_url
    mcp_token = args.mcp_token or get_env_var('MCP_TOKEN') or mcp_config.token
    mcp_timeout = args.mcp_timeout or get_env_var('MCP_TIMEOUT') or mcp_config.timeout
    
    if not mcp_server:
        logger.error("MCP_SERVER_URL is required. Please set it in config.yaml, environment variable, or use --mcp-server flag")
        return
    
    # Get OpenAI configuration (priority: args > env > config file)
    openai_config = config_loader.get_openai_config()
    openai_endpoint = args.endpoint or get_env_var('OPENAI_API_HOST') or get_env_var('OPENAI_API_BASE') or openai_config.endpoint
    openai_key = args.key or get_env_var('OPENAI_API_KEY') or openai_config.api_key
    openai_model = args.model or get_env_var('OPENAI_API_MODEL') or get_env_var('OPENAI_MODEL') or openai_config.model
    
    if not openai_key:
        logger.error("OPENAI_API_KEY is required. Please set it in config.yaml, environment variable, or use --key flag")
        return
    
    if not openai_endpoint:
        logger.error("OPENAI_API_HOST is required. Please set it in config.yaml, environment variable, or use --endpoint flag")
        return
    
    # Get chat configuration
    max_history = args.history or config_loader.get('chat.max_history', 8)
    verbose = args.verbose or config_loader.get('chat.verbose', False)
    
    # Validate timeout
    try:
        parse_timeout(mcp_timeout)
    except ValueError as e:
        logger.error(f"Invalid timeout format: {e}")
        return
    
    # Log configuration
    logger.debug("Configuration:")
    logger.debug(f"  OpenAI Endpoint: {openai_endpoint}")
    logger.debug(f"  OpenAI Model: {openai_model}")
    logger.debug(f"  OpenAI Key: {mask_key(openai_key)} (length: {len(openai_key)})")
    logger.debug(f"  MCP Server: {mcp_server}")
    logger.debug(f"  MCP Timeout: {mcp_timeout}")
    
    # Create MCP tool
    try:
        mcp_tool = MCPTool(server_url=mcp_server, token=mcp_token, timeout=mcp_timeout)
    except Exception as e:
        logger.error(f"Failed to create MCP tool: {e}")
        return
    
    # Create OpenAI client
    try:
        openai_client = OpenAIClient(endpoint=openai_endpoint, api_key=openai_key, model=openai_model)
    except Exception as e:
        logger.error(f"Failed to create OpenAI client: {e}")
        return
    
    # Create chat instance
    try:
        chat = Chat(
            openai_client=openai_client,
            mcp_tool=mcp_tool,
            verbose=verbose,
            max_history=max_history
        )
    except Exception as e:
        logger.error(f"Failed to create chat: {e}")
        return
    
    # Print summary in verbose mode
    logger.debug("\n=== Chat Ready ===\n")
    logger.debug("You can now start chatting. Type 'exit' or 'q' to quit.\n\n")
    
    # Interactive chat loop
    try:
        while True:
            try:
                user_input = input(PROMPT).strip()
                
                if user_input.lower() in ['exit', 'q']:
                    break
                
                if not user_input:
                    continue
                
                # Chat with MCP tools
                try:
                    response = chat.chat(user_input)
                    print(response)
                except Exception as e:
                    import traceback
                    logger.error(f"Chat error: {e}")
                    logger.error(f"Exception type: {type(e).__name__}")
                    if verbose:
                        logger.error(f"Full traceback:\n{traceback.format_exc()}")
                    # Print user-friendly error message
                    error_msg = str(e)
                    if "Connection" in error_msg or "timeout" in error_msg.lower():
                        print(f"❌ Connection error: {error_msg}\nPlease check your network connection and API endpoints.")
                    elif "HTTP" in error_msg or "502" in error_msg or "Bad Gateway" in error_msg:
                        print(f"❌ Server error: {error_msg}\nThe server may be temporarily unavailable. Please try again later.")
                    else:
                        print(f"❌ Error: {error_msg}")
            
            except KeyboardInterrupt:
                print("\n")
                break
            except EOFError:
                print("\n")
                break
    
    except Exception as e:
        logger.error(f"Chat error: {e}")
    
    finally:
        print(QUIT_MSG)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Ops Copilot - AI-powered DevOps assistant with MCP tool integration"
    )
    
    parser.add_argument(
        '--endpoint', '-e',
        type=str,
        default=None,
        help='OpenAI API endpoint (default: from OPENAI_API_HOST env var)'
    )
    
    parser.add_argument(
        '--model', '-m',
        type=str,
        default=None,
        help='OpenAI model (default: from OPENAI_API_MODEL env var or gpt-4o-mini)'
    )
    
    parser.add_argument(
        '--key', '-k',
        type=str,
        default=None,
        help='OpenAI API key (default: from OPENAI_API_KEY env var)'
    )
    
    parser.add_argument(
        '--mcp-server',
        type=str,
        default=None,
        help='MCP server URL (default: from MCP_SERVER_URL env var)'
    )
    
    parser.add_argument(
        '--mcp-token',
        type=str,
        default=None,
        help='MCP server token (default: from MCP_TOKEN env var)'
    )
    
    parser.add_argument(
        '--mcp-timeout',
        type=str,
        default=None,
        help='MCP timeout (default: from MCP_TIMEOUT env var or 600s)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose/debug logging'
    )
    
    parser.add_argument(
        '--history',
        type=int,
        default=None,
        help='Chat history length (default: from config.yaml or 8)'
    )
    
    parser.add_argument(
        '--config', '-c',
        type=str,
        default=None,
        help='Path to config.yaml file (default: ./configs/config.yaml)'
    )
    
    args = parser.parse_args()
    
    create_copilot(args)


if __name__ == "__main__":
    main()

