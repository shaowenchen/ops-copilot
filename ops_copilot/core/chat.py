"""
Chat module with MCP tool calling support
"""

import json
from typing import Dict, Any, List, Optional
from ..tools.mcp_tool import MCPTool
from ..core.openai_client import OpenAIClient
from ..utils.logging import get_logger

logger = get_logger(__name__)


class ChatMessage:
    """Chat message history manager"""
    
    def __init__(self, max_history: int = 8):
        """
        Initialize chat message history
        
        Args:
            max_history: Maximum number of messages to keep in history
        """
        self.max_history = max_history
        self.messages: List[Dict[str, str]] = []
    
    def add_system_content(self, content: str) -> 'ChatMessage':
        """Add or update system message"""
        # Remove existing system message
        self.messages = [msg for msg in self.messages if msg.get('role') != 'system']
        # Add new system message at the beginning
        self.messages.insert(0, {"role": "system", "content": content})
        self._trim_history()
        return self
    
    def add_user_content(self, content: str) -> 'ChatMessage':
        """Add user message"""
        self.messages.append({"role": "user", "content": content})
        self._trim_history()
        return self
    
    def add_assistant_content(self, content: str) -> 'ChatMessage':
        """Add assistant message"""
        self.messages.append({"role": "assistant", "content": content})
        self._trim_history()
        return self
    
    def add_tool_result(self, tool_call_id: str, name: str, content: str) -> 'ChatMessage':
        """Add tool result message"""
        self.messages.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": name,
            "content": content
        })
        return self
    
    def _trim_history(self) -> None:
        """Trim message history to max_history"""
        if len(self.messages) <= self.max_history:
            return
        
        # Keep system message and most recent messages
        system_msg = None
        other_messages = []
        
        for msg in self.messages:
            if msg.get('role') == 'system':
                system_msg = msg
            else:
                other_messages.append(msg)
        
        # Keep only the most recent messages
        keep_count = self.max_history - (1 if system_msg else 0)
        if len(other_messages) > keep_count:
            other_messages = other_messages[-keep_count:]
        
        # Rebuild messages
        self.messages = []
        if system_msg:
            self.messages.append(system_msg)
        self.messages.extend(other_messages)
    
    def get_messages(self) -> List[Dict[str, str]]:
        """Get all messages"""
        return self.messages.copy()


class Chat:
    """Chat handler with MCP tool calling support"""
    
    def __init__(
        self,
        openai_client: OpenAIClient,
        mcp_tool: MCPTool,
        verbose: bool = False,
        max_history: int = 8
    ):
        """
        Initialize Chat instance
        
        Args:
            openai_client: OpenAI client instance
            mcp_tool: MCP tool instance
            verbose: Enable verbose logging
            max_history: Maximum chat history length
        """
        self.openai_client = openai_client
        self.mcp_tool = mcp_tool
        self.verbose = verbose
        self.history = ChatMessage(max_history=max_history)
        self.tool_map: Dict[str, Any] = {}  # Store raw tool info for prompt generation
        
        # Load available tools from MCP server
        self._load_tools()
    
    def _load_tools(self) -> None:
        """Load available tools from MCP server"""
        logger.debug("Loading MCP tools...")
        
        try:
            tools = self.mcp_tool.list_tools()
            if not tools:
                logger.warning("No MCP tools available. Chat will work without tool calling.")
                return
            
            logger.debug(f"Received {len(tools)} tools from MCP server")
            
            # Store tools in tool_map for prompt generation (ReAct mode doesn't need OpenAI format)
            for tool in tools:
                # Get tool name for tool_map (handle both dict and Pydantic objects)
                tool_name = tool.name if hasattr(tool, 'name') else (tool.get('name', '') if isinstance(tool, dict) else '')
                if tool_name:
                    self.tool_map[tool_name] = tool
            
            logger.debug(f"Successfully loaded {len(self.tool_map)} MCP tools")
            
            # Print tools details in verbose mode
            if self.verbose:
                self._print_tools_details(tools)
            else:
                # Even in non-verbose mode, log basic tool count
                logger.info(f"Loaded {len(self.tool_map)} MCP tools (use -v to see details)")
        except Exception as e:
            import traceback
            logger.error(f"Failed to load MCP tools: {e}, continuing without tools")
            logger.error(f"Exception type: {type(e).__name__}")
            logger.error(f"Exception details: {str(e)}")
            logger.error(f"Full traceback:\n{traceback.format_exc()}")
            logger.debug("No MCP tools available. Chat will work without tool calling.")
    
    def chat(self, input_text: str) -> str:
        """
        Handle a chat request using ReAct pattern (no function calling)
        
        Args:
            input_text: User input text
            
        Returns:
            Response text
        """
        self.history.add_user_content(input_text)
        messages = self._build_messages()
        
        max_iterations = 10
        for i in range(max_iterations):
            # Log iteration info
            if self.verbose:
                logger.info(f"\n{'=' * 80}")
                logger.info(f"=== Chat Iteration {i + 1}/{max_iterations} ===")
                logger.info(f"{'=' * 80}")
            
            try:
                # Log LLM request details in verbose mode
                if self.verbose:
                    logger.info(f"\n[LLM Request]")
                    logger.info(f"  Endpoint: {self.openai_client.base_url}")
                    logger.info(f"  Model: {self.openai_client.model}")
                    logger.info(f"  Messages count: {len(messages)}")
                    # Log last user message for context
                    for msg in reversed(messages):
                        if msg.get('role') == 'user':
                            user_msg = msg.get('content', '')
                            if len(user_msg) > 200:
                                user_msg = user_msg[:200] + "..."
                            logger.info(f"  Last user message: {user_msg}")
                            break
                
                # Call OpenAI API without tools parameter (ReAct mode)
                response = self.openai_client.create_chat_completion(
                    messages=messages,
                    tools=None,  # No function calling
                    temperature=0.1
                )
                
                if not response.get('choices'):
                    raise ValueError("No choices in response")
                
                choice = response['choices'][0]
                message = choice['message']
                response_text = message.get('content', '')
                
                # Log LLM response in verbose mode
                if self.verbose:
                    logger.info(f"\n[LLM Response]")
                    response_preview = response_text[:500] + "..." if len(response_text) > 500 else response_text
                    logger.info(f"  Response length: {len(response_text)} characters")
                    logger.info(f"  Response preview:\n{response_preview}")
                    if hasattr(choice, 'finish_reason') or 'finish_reason' in choice:
                        finish_reason = choice.get('finish_reason', 'unknown')
                        logger.info(f"  Finish reason: {finish_reason}")
                
            except Exception as e:
                logger.error(f"OpenAI API call failed: {e}")
                import traceback
                logger.error(f"Full traceback:\n{traceback.format_exc()}")
                raise Exception(f"Failed to get response from OpenAI API: {str(e)}")
            
            # Parse ReAct format to extract tool calls
            tool_calls = self._parse_react_tool_calls(response_text)
            
            if tool_calls:
                if self.verbose:
                    logger.info(f"\n[MCP Tool Calls Detected]")
                    logger.info(f"  Number of tool calls: {len(tool_calls)}")
                
                # Add assistant message with tool calls
                messages.append({
                    "role": "assistant",
                    "content": response_text
                })
                
                # Execute tool calls
                tool_results = []
                for idx, tool_call in enumerate(tool_calls, 1):
                    tool_name = tool_call.get('tool', '')
                    arguments = tool_call.get('arguments', {})
                    
                    if not tool_name:
                        logger.warning("Tool call missing tool name")
                        continue
                    
                    # Log MCP tool call details in verbose mode
                    if self.verbose:
                        logger.info(f"\n[MCP Tool Call {idx}/{len(tool_calls)}]")
                        logger.info(f"  Tool name: {tool_name}")
                        logger.info(f"  Arguments: {json.dumps(arguments, ensure_ascii=False, indent=2) if arguments else '{}'}")
                        logger.info(f"  Server URL: {self.mcp_tool.server_url}")
                    
                    # Call MCP tool
                    try:
                        result = self.mcp_tool.call_tool(tool_name, arguments)
                        
                        # Log MCP tool result in verbose mode
                        if self.verbose:
                            result_preview = result[:500] + "..." if len(result) > 500 else result
                            logger.info(f"  Result length: {len(result)} characters")
                            logger.info(f"  Result preview:\n{result_preview}")
                        
                        tool_results.append(f"Tool {tool_name} result: {result}")
                    except Exception as e:
                        logger.error(f"Tool call failed: {e}")
                        if self.verbose:
                            import traceback
                            logger.error(f"  Error details:\n{traceback.format_exc()}")
                        tool_results.append(f"Tool {tool_name} error: {str(e)}")
                
                # Add tool results to messages
                if tool_results:
                    result_text = "\n\n".join(tool_results)
                    messages.append({
                        "role": "user",
                        "content": f"Tool execution results:\n{result_text}\n\nPlease continue with your analysis and provide the final answer."
                    })
                
                # Continue conversation with tool results
                continue
            
            # No tool calls, return the final response
            if self.verbose:
                logger.info(f"\n[Final Response]")
                logger.info(f"  No tool calls needed, returning LLM response")
                logger.info(f"  Response length: {len(response_text)} characters")
            
            self.history.add_assistant_content(response_text)
            return response_text
        
        raise ValueError("Max iterations reached")
    
    def _parse_react_tool_calls(self, text: str) -> List[Dict[str, Any]]:
        """
        Parse ReAct format tool calls from LLM response
        
        Format: <tool_call>{"tool": "tool_name", "arguments": {...}}</tool_call>
        
        Args:
            text: LLM response text
            
        Returns:
            List of tool call dictionaries
        """
        import re
        tool_calls = []
        
        # Find all <tool_call>...</tool_call> blocks
        pattern = r'<tool_call>(.*?)</tool_call>'
        matches = re.findall(pattern, text, re.DOTALL)
        
        for match in matches:
            try:
                # Parse JSON from tool_call block
                tool_call_data = json.loads(match.strip())
                if isinstance(tool_call_data, dict) and 'tool' in tool_call_data:
                    tool_calls.append(tool_call_data)
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse tool call JSON: {match}, error: {e}")
                # Try to extract tool name and arguments manually
                try:
                    # Try to find tool name and arguments in the text
                    tool_match = re.search(r'"tool"\s*:\s*"([^"]+)"', match)
                    args_match = re.search(r'"arguments"\s*:\s*(\{.*\})', match, re.DOTALL)
                    if tool_match and args_match:
                        tool_name = tool_match.group(1)
                        args_text = args_match.group(1)
                        args = json.loads(args_text)
                        tool_calls.append({
                            "tool": tool_name,
                            "arguments": args
                        })
                except Exception as e2:
                    logger.warning(f"Failed to manually parse tool call: {e2}")
        
        return tool_calls
    
    def _build_messages(self) -> List[Dict[str, str]]:
        """Build message list from history, including system message"""
        messages = self.history.get_messages()
        
        # Check if system message exists
        has_system = any(msg.get('role') == 'system' for msg in messages)
        
        if not has_system:
            system_prompt = self._get_chat_prompt()
            messages.insert(0, {
                "role": "system",
                "content": system_prompt
            })
        
        return messages
    
    def _get_chat_prompt(self) -> str:
        """Get system prompt for chat using ReAct pattern"""
        prompt = """You are a DevOps expert assistant with access to operational tools through MCP (Model Context Protocol).

You can help users with various operational tasks using the following available tools:
"""
        
        # List available tools with their descriptions and parameters
        if self.tool_map:
            for tool_name, tool_info in self.tool_map.items():
                # Get description
                if hasattr(tool_info, 'description'):
                    description = tool_info.description
                elif isinstance(tool_info, dict):
                    description = tool_info.get('description', '')
                else:
                    description = getattr(tool_info, 'description', '')
                
                # Get input schema
                if hasattr(tool_info, 'inputSchema'):
                    input_schema = tool_info.inputSchema
                elif hasattr(tool_info, 'input_schema'):
                    input_schema = tool_info.input_schema
                elif isinstance(tool_info, dict):
                    input_schema = tool_info.get('inputSchema') or tool_info.get('input_schema')
                else:
                    input_schema = None
                
                # Convert schema to dict if needed
                if input_schema and not isinstance(input_schema, dict):
                    if hasattr(input_schema, 'dict'):
                        input_schema = input_schema.dict()
                    elif hasattr(input_schema, 'model_dump'):
                        input_schema = input_schema.model_dump()
                    elif hasattr(input_schema, '__dict__'):
                        input_schema = input_schema.__dict__
                
                prompt += f"\n- {tool_name}: {description or 'No description'}\n"
                if input_schema and isinstance(input_schema, dict):
                    properties = input_schema.get('properties', {})
                    if properties:
                        prompt += "  Parameters:\n"
                        for param_name, param_info in properties.items():
                            param_type = param_info.get('type', 'unknown') if isinstance(param_info, dict) else 'unknown'
                            param_desc = param_info.get('description', '') if isinstance(param_info, dict) else ''
                            required = param_info.get('required', False) if isinstance(param_info, dict) else False
                            req_mark = " (required)" if required else ""
                            prompt += f"    - {param_name} ({param_type}){req_mark}: {param_desc}\n"
        else:
            prompt += "- No tools available\n"
        
        prompt += """

CRITICAL DATA SOURCE RULES:
Your ONLY data sources are:
1. User's input/question
2. Data returned from MCP tools

You do NOT have access to:
- Real-time system information (unless you call MCP tools)
- Current logs, metrics, or events (unless you call MCP tools)
- Live Kubernetes cluster state (unless you call MCP tools)
- Any operational data (unless you call MCP tools)

IMPORTANT: If you don't have enough data to answer the user's question, you MUST call MCP tools to gather the necessary information. 
DO NOT make assumptions or use general knowledge - ALWAYS use tools to get actual, real-time data.

When a user asks about:
- System status, logs, metrics, events → MUST use query/search tools
- Kubernetes resources, pods, services → MUST use query tools
- SOPS operations → MUST use SOPS tools
- Any operational data → MUST use appropriate MCP tools
- Questions requiring current/real-time information → MUST use tools first

Use the ReAct (Reasoning and Acting) pattern to interact with tools:

When you need to use a tool, follow this format:
<think>
Your reasoning about what tool to use and why. Think step by step about what information you need.
</think>
<tool_call>
{"tool": "tool_name", "arguments": {"param1": "value1", "param2": "value2"}}
</tool_call>

After the tool is executed, you will receive the result. Then you can:
1. Continue thinking and call more tools if needed to gather complete information
2. Analyze all the information you've gathered
3. Provide a comprehensive answer to the user

Example workflow:
<think>
The user wants to check system logs. I should first list available log indices to see what's available, then search for relevant logs.
</think>
<tool_call>
{"tool": "list-log-indices-from-elasticsearch", "arguments": {}}
</tool_call>

[After receiving tool result, continue...]

<think>
Now I have the list of indices. I should search for error logs in the most relevant index.
</think>
<tool_call>
{"tool": "search-logs-from-elasticsearch", "arguments": {"index": "logs-*", "body": "{\"query\": {\"match\": {\"message\": \"error\"}}}"}}
</tool_call>

[After receiving search results, provide final answer...]

CRITICAL RULES:
1. DATA SOURCE CHECK: Before answering, ask yourself:
   - Do I have enough data from user input and previous tool calls to answer this question?
   - If NO, I MUST call MCP tools to gather the necessary information
   - If YES, I can proceed to answer

2. ALWAYS use MCP tools when the user asks about:
   - System status, logs, metrics, events → MUST call tools
   - Kubernetes resources, pods, services → MUST call tools
   - SOPS operations → MUST call tools
   - Any operational data → MUST call tools
   - Questions requiring current/real-time information → MUST call tools first

3. NEVER answer based on assumptions or general knowledge when real-time data is needed
   - Example: If user asks "What's the current CPU usage?", you MUST call metrics query tool
   - Example: If user asks "Show me recent errors", you MUST call log search tool
   - Example: If user asks "List running pods", you MUST call appropriate query tool

4. You can call multiple tools in sequence to gather complete information:
   - First, call tools to list/explore available resources
   - Then, call tools to get detailed information
   - Continue until you have enough data to answer

5. When you have the final answer, provide it clearly without using <tool_call> tags

6. Always explain what you're doing and provide context for the results

7. If a tool call fails, explain the error and try alternative approaches

8. If you cannot get the data needed to answer, clearly state what data is missing and what tools you tried

Support both English and Chinese users naturally."""
        
        return prompt
    
    def _print_tools_details(self, tools: List[Dict[str, Any]]) -> None:
        """Print detailed information about MCP tools in verbose mode"""
        if not tools:
            print("\n" + "=" * 80)
            print("=== MCP Server Tools ===")
            print("No tools available from MCP server")
            print("=" * 80 + "\n")
            return
        
        # Print to stdout for better visibility in verbose mode
        print("\n" + "=" * 80)
        print(f"=== MCP Server Tools (Total: {len(tools)}) ===")
        print("=" * 80 + "\n")
        for i, tool in enumerate(tools, 1):
            # Handle both dict and Pydantic objects
            if hasattr(tool, 'name'):
                tool_name = tool.name
                description = getattr(tool, 'description', '')
                input_schema = getattr(tool, 'inputSchema', None)
                if input_schema is None:
                    input_schema = getattr(tool, 'input_schema', None)
            elif isinstance(tool, dict):
                tool_name = tool.get('name', 'Unknown')
                description = tool.get('description', '')
                input_schema = tool.get('inputSchema', {})
            else:
                # Try to convert to dict
                if hasattr(tool, 'dict'):
                    tool_dict = tool.dict()
                elif hasattr(tool, '__dict__'):
                    tool_dict = tool.__dict__
                else:
                    tool_dict = {}
                tool_name = tool_dict.get('name', 'Unknown')
                description = tool_dict.get('description', '')
                input_schema = tool_dict.get('inputSchema', {})
            
            # Convert input_schema to dict if needed
            if input_schema is not None and not isinstance(input_schema, dict):
                if hasattr(input_schema, 'dict'):
                    input_schema = input_schema.dict()
                elif hasattr(input_schema, 'model_dump'):  # Pydantic v2
                    input_schema = input_schema.model_dump()
                elif hasattr(input_schema, '__dict__'):
                    input_schema = input_schema.__dict__
                else:
                    input_schema = {}
            elif input_schema is None:
                input_schema = {}
            
            print(f"[{i}] Tool: {tool_name}")
            print(f"  Description: {description if description else '(no description)'}")
            
            if input_schema:
                print("  Parameters:")
                self._print_schema(input_schema, "    ", use_print=True)
            else:
                print("  Parameters: (no parameters defined)")
            print()  # Empty line between tools
        
        print("=" * 80)
        print("=== End of Tools List ===\n")
    
    def _print_schema(self, schema: Dict[str, Any], indent: str = "", use_print: bool = False) -> None:
        """Recursively print schema structure"""
        log_func = print if use_print else logger.debug
        
        schema_type = schema.get('type', '')
        if schema_type:
            log_func(f"{indent}Type: {schema_type}")
        
        description = schema.get('description', '')
        if description:
            log_func(f"{indent}Description: {description}")
        
        properties = schema.get('properties', {})
        if properties:
            log_func(f"{indent}Properties:")
            for prop_name, prop_value in properties.items():
                if isinstance(prop_value, dict):
                    log_func(f"{indent}  - {prop_name}:")
                    self._print_schema(prop_value, indent + "    ", use_print=use_print)
                else:
                    log_func(f"{indent}  - {prop_name}: {prop_value}")
        
        required = schema.get('required', [])
        if required:
            log_func(f"{indent}Required: {required}")
        
        enum = schema.get('enum', [])
        if enum:
            log_func(f"{indent}Enum: {enum}")
        
        default = schema.get('default')
        if default is not None:
            log_func(f"{indent}Default: {default}")

