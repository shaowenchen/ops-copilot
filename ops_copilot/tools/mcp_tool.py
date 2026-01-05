"""
MCP Tool for Ops Copilot
"""

import json
import asyncio
import re
from datetime import timedelta, datetime
from typing import Dict, Any, Optional, List

from fastmcp import Client as FastMCPClient

from ..utils.logging import get_logger

logger = get_logger(__name__)


class MCPTool:
    """MCP Tool for executing MCP server operations"""
    
    def __init__(self, server_url: str, token: str = "", timeout: str = "600s", cache_ttl: int = 300):
        """
        Initialize MCP Tool
        
        Args:
            server_url: MCP server URL
            token: MCP server token (optional)
            timeout: Timeout string (e.g., "30s", "1m", "2h")
            cache_ttl: Cache TTL in seconds for tools list (default: 300s = 5 minutes)
        """
        self.server_url = server_url.strip().rstrip('/')
        self.token = token
        self.timeout_str = timeout
        self.timeout = self._parse_timeout(timeout)
        self.cache_ttl = cache_ttl
        
        # Cache for tools list
        self._tools_cache: Optional[List[Dict[str, Any]]] = None
        self._tools_cache_time: Optional[datetime] = None
        
        # Initialize FastMCP client
        self.client = FastMCPClient(
            transport=self.server_url,
            auth=self.token if self.token else None,
            timeout=self.timeout
        )
    
    def _parse_timeout(self, timeout_str: str) -> timedelta:
        """
        Parse timeout string into datetime.timedelta object
        
        Args:
            timeout_str: Timeout string (e.g., "30s", "1m", "2h")
        
        Returns:
            datetime.timedelta object
        """
        match = re.match(r'^(\d+)([smhd])$', timeout_str)
        if not match:
            raise ValueError(f"Invalid timeout format: {timeout_str}. Expected format like '30s', '1m', '2h'.")
        
        value, unit = match.groups()
        value = int(value)
        
        if unit == 's':
            return timedelta(seconds=value)
        elif unit == 'm':
            return timedelta(minutes=value)
        elif unit == 'h':
            return timedelta(hours=value)
        elif unit == 'd':
            return timedelta(days=value)
        
        raise ValueError(f"Invalid timeout unit: {unit}")
    
    def call_tool(self, tool_name: str, arguments: Dict[str, Any] = None) -> str:
        """
        Call an MCP tool and return text content
        
        Args:
            tool_name: Tool name
            arguments: Tool arguments
            
        Returns:
            Text content from tool result
        """
        if arguments is None:
            arguments = {}
        
        try:
            # Log MCP tool call request (always log, not just debug)
            logger.info(f"[MCP Tool Call Request]")
            logger.info(f"  Tool name: {tool_name}")
            logger.info(f"  Server URL: {self.server_url}")
            logger.info(f"  Arguments count: {len(arguments) if arguments else 0}")
            if arguments:
                try:
                    formatted_args = json.dumps(arguments, ensure_ascii=False, indent=2)
                    logger.info(f"  Arguments:\n{formatted_args}")
                except Exception:
                    logger.info(f"  Arguments: {arguments}")
            
            result = asyncio.run(self._async_call_tool(tool_name, arguments))
            
            # Log MCP tool call response
            logger.info(f"[MCP Tool Call Response]")
            logger.info(f"  Tool name: {tool_name}")
            logger.info(f"  Result type: {type(result).__name__}")
            
            text_content = self._extract_text_content(result)
            logger.info(f"  Text content length: {len(text_content)} characters")
            if len(text_content) > 500:
                logger.info(f"  Text content preview: {text_content[:500]}...")
            else:
                logger.info(f"  Text content: {text_content}")
            
            return text_content
        except Exception as e:
            import traceback
            logger.error(f"MCP工具执行失败 {tool_name}: {e}")
            logger.error(f"异常类型: {type(e).__name__}")
            logger.error(f"异常详情: {str(e)}")
            full_traceback = traceback.format_exc()
            logger.error(f"完整堆栈:\n{full_traceback}")
            return f"Error: {e}"
    
    def list_tools(self, use_cache: bool = True, max_retries: int = 2) -> List[Dict[str, Any]]:
        """
        List all available MCP tools (with caching and retry)
        
        Args:
            use_cache: Whether to use cached result if available (default: True)
            max_retries: Maximum number of retry attempts on failure (default: 2)
        
        Returns:
            List of available tools
        """
        # Check cache first
        if use_cache and self._tools_cache is not None and self._tools_cache_time is not None:
            cache_age = (datetime.now() - self._tools_cache_time).total_seconds()
            if cache_age < self.cache_ttl:
                logger.debug(f"Using cached tools list (age: {cache_age:.1f}s, TTL: {self.cache_ttl}s)")
                return self._tools_cache
        
        # Retry logic for SSE connection issues
        last_exception = None
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    logger.info(f"Retrying to list MCP tools (attempt {attempt + 1}/{max_retries + 1})...")
                    # Wait a bit before retry (exponential backoff)
                    import time
                    time.sleep(min(2 ** attempt, 5))  # Max 5 seconds
                
                logger.info(f"Listing available MCP tools from {self.server_url}")
                tools = asyncio.run(self._async_list_tools())
                logger.info(f"Found {len(tools)} available MCP tools")
                
                # Update cache on success
                self._tools_cache = tools
                self._tools_cache_time = datetime.now()
                logger.debug(f"Cached tools list (TTL: {self.cache_ttl}s)")
                
                return tools
            except Exception as e:
                last_exception = e
                import traceback
                error_msg = str(e)
                error_type = type(e).__name__
                
                # Check if it's a connection-related error
                is_connection_error = any(keyword in error_msg.lower() for keyword in [
                    'connection', 'closed', 'timeout', 'protocol', 'incomplete', 'chunked'
                ])
                
                logger.error(f"Failed to list available MCP tools (attempt {attempt + 1}/{max_retries + 1}): {error_msg}")
                logger.error(f"Exception type: {error_type}")
                
                if attempt < max_retries and is_connection_error:
                    logger.warning(f"Connection error detected, will retry...")
                    continue
                else:
                    # Log full traceback only on final attempt
                    full_traceback = traceback.format_exc()
                    logger.error(f"Full traceback:\n{full_traceback}")
                    break
        
        # If we have cached tools, return them even if expired
        if self._tools_cache is not None:
            cache_age = (datetime.now() - self._tools_cache_time).total_seconds()
            logger.warning(f"Using expired cache due to error (age: {cache_age:.1f}s)")
            return self._tools_cache
        
        # Return empty list instead of raising exception
        logger.warning("No cached tools available, returning empty list")
        return []
    
    def clear_cache(self) -> None:
        """Clear the tools list cache"""
        self._tools_cache = None
        self._tools_cache_time = None
        logger.debug("Cleared tools list cache")
    
    async def _async_call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Async method to call FastMCP client's call_tool method
        
        Args:
            name: Tool name
            arguments: Tool arguments
            
        Returns:
            Tool response
        """
        try:
            async with self.client as client:
                result = await client.call_tool(
                    name=name,
                    arguments=arguments
                )
                
                # Convert result to dict if needed
                if hasattr(result, 'content'):
                    content_list = []
                    for content in result.content:
                        if hasattr(content, 'text'):
                            content_list.append(content.text)
                        elif hasattr(content, '__dict__'):
                            content_list.append(content.__dict__)
                        else:
                            content_list.append(str(content))
                    
                    return {
                        "content": content_list,
                        "isError": getattr(result, 'isError', False)
                    }
                elif hasattr(result, 'dict'):
                    return result.dict()
                elif hasattr(result, '__dict__'):
                    return result.__dict__
                else:
                    return {"result": str(result)}
        except Exception as e:
            # Log the error but don't raise it here - let the caller handle it
            logger.error(f"Error in _async_call_tool: {e}")
            logger.error(f"Exception type: {type(e).__name__}")
            raise
    
    async def _async_list_tools(self) -> List[Dict[str, Any]]:
        """
        Async method to list tools using FastMCP client
        
        Returns:
            List of available tools
        """
        try:
            async with self.client as client:
                tools = await client.list_tools()
                return tools
        except Exception as e:
            # Log the error but don't raise it here - let the caller handle it
            logger.error(f"Error in _async_list_tools: {e}")
            logger.error(f"Exception type: {type(e).__name__}")
            raise
    
    def _extract_text_content(self, result: Dict[str, Any]) -> str:
        """Extract text content from MCP tool result"""
        if isinstance(result, dict):
            if 'content' in result:
                content_list = result['content']
                if isinstance(content_list, list):
                    text_parts = []
                    for content in content_list:
                        if isinstance(content, str):
                            text_parts.append(content)
                        elif isinstance(content, dict) and 'text' in content:
                            text_parts.append(content['text'])
                    return '\n'.join(text_parts)
            elif 'result' in result:
                return str(result['result'])
        
        return str(result)

