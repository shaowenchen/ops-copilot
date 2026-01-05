"""
Configuration loader for Ops Copilot
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass
from dotenv import load_dotenv

from ..utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class MCPConfig:
    """MCP server configuration"""
    server_url: str
    server_name: str
    timeout: str
    token: str


@dataclass
class OpenAIConfig:
    """OpenAI configuration"""
    endpoint: str
    api_key: str
    model: str


class ConfigLoader:
    """Configuration loader for Ops Copilot"""
    
    def __init__(self, config_file: str = None):
        """
        Initialize configuration loader
        
        Args:
            config_file: Configuration file path
        """
        if config_file:
            self.config_path = config_file
        else:
            # Try to find config in default locations
            default_locations = [
                os.path.join(os.path.dirname(__file__), "../../configs/config.yaml"),
                "./configs/config.yaml",
                os.path.expanduser("~/.ops-copilot/config.yaml"),
                "/etc/ops-copilot/config.yaml"
            ]
            
            for loc in default_locations:
                if os.path.exists(loc):
                    self.config_path = loc
                    break
            else:
                self.config_path = default_locations[1]  # Default to ./configs/config.yaml
        
        self._config = None
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file or environment variables"""
        # Load environment variables from .env if present
        try:
            # Try project root .env
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            project_root_env = os.path.join(project_root, '.env')
            if os.path.exists(project_root_env):
                load_dotenv(dotenv_path=project_root_env, override=False)
            # Also try current working directory .env
            load_dotenv(override=False)
        except Exception:
            # Best-effort loading; never fail on dotenv
            pass

        # First try to load from file
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self._config = yaml.safe_load(f) or {}
                logger.debug(f"Loaded config from: {self.config_path}")
            except Exception as e:
                logger.warning(f"Failed to load config file {self.config_path}: {e}")
                self._config = {}
        else:
            logger.debug(f"Config file not found: {self.config_path}, using defaults")
            self._config = {}
        
        # Override with environment variables
        self._load_from_env()
        return self._config
    
    def _load_from_env(self) -> None:
        """Load configuration from environment variables and override config file values"""
        # Initialize config sections if not present
        if 'mcp' not in self._config:
            self._config['mcp'] = {}
        if 'openai' not in self._config:
            self._config['openai'] = {}
        if 'chat' not in self._config:
            self._config['chat'] = {}
        
        # Recursively override config with environment variables
        # Format: SECTION_KEY -> SECTION_KEY (e.g., MCP_SERVER_URL -> mcp.server_url)
        self._override_with_env(self._config, "")
        
        # Also check for backward compatibility with old environment variable names
        self._handle_backward_compatibility()
    
    def _override_with_env(self, config: Dict[str, Any], prefix: str) -> None:
        """
        Recursively override config values with environment variables
        
        Args:
            config: Configuration dictionary (modified in place)
            prefix: Current prefix for environment variable name (e.g., "MCP_", "OPENAI_")
        """
        for key, value in list(config.items()):
            # Build environment variable name: PREFIX_KEY (all uppercase)
            # Convert key to uppercase, preserving underscores
            # e.g., "server_url" -> "SERVER_URL", "api_key" -> "API_KEY"
            clean_key = key.upper()
            env_key = f"{prefix}{clean_key}" if prefix else clean_key
            
            if isinstance(value, dict):
                # Recursively process nested dictionaries
                new_prefix = f"{env_key}_"
                self._override_with_env(value, new_prefix)
            else:
                # Override leaf values with environment variables
                env_value = os.environ.get(env_key)
                if env_value is not None:
                    # Try to convert to appropriate type
                    if isinstance(value, bool):
                        env_value = env_value.lower() in ('true', '1', 'yes', 'on')
                    elif isinstance(value, int):
                        try:
                            env_value = int(env_value)
                        except ValueError:
                            logger.warning(f"Invalid integer value for {env_key}: {env_value}")
                            continue
                    elif isinstance(value, float):
                        try:
                            env_value = float(env_value)
                        except ValueError:
                            logger.warning(f"Invalid float value for {env_key}: {env_value}")
                            continue
                    
                    config[key] = env_value
                    logger.debug(f"Config {key} overridden by environment variable {env_key}")
    
    def _handle_backward_compatibility(self) -> None:
        """Handle backward compatibility with old environment variable names"""
        # OPENAI_API_HOST and OPENAI_API_BASE -> OPENAI_ENDPOINT
        if os.environ.get('OPENAI_API_HOST') or os.environ.get('OPENAI_API_BASE'):
            if 'openai' not in self._config:
                self._config['openai'] = {}
            endpoint = os.environ.get('OPENAI_API_HOST') or os.environ.get('OPENAI_API_BASE')
            self._config['openai']['endpoint'] = endpoint
            logger.info("OpenAI endpoint overridden by environment variable (OPENAI_API_HOST/OPENAI_API_BASE)")
        
        # OPENAI_API_MODEL and OPENAI_MODEL -> OPENAI_MODEL
        if os.environ.get('OPENAI_API_MODEL') or os.environ.get('OPENAI_MODEL'):
            if 'openai' not in self._config:
                self._config['openai'] = {}
            model = os.environ.get('OPENAI_API_MODEL') or os.environ.get('OPENAI_MODEL')
            self._config['openai']['model'] = model
            logger.info("OpenAI model overridden by environment variable (OPENAI_API_MODEL/OPENAI_MODEL)")
    
    def get_mcp_config(self) -> MCPConfig:
        """
        Get MCP configuration
        
        Returns:
            MCPConfig instance
        """
        if not self._config:
            self.load_config()
        
        mcp_config = self._config.get('mcp', {})
        
        return MCPConfig(
            server_url=mcp_config.get('server_url', ''),
            server_name=mcp_config.get('server_name', 'default'),
            timeout=mcp_config.get('timeout', '600s'),
            token=mcp_config.get('token', '')
        )
    
    def get_openai_config(self) -> OpenAIConfig:
        """
        Get OpenAI configuration
        
        Returns:
            OpenAIConfig instance
        """
        if not self._config:
            self.load_config()
        
        openai_config = self._config.get('openai', {})
        
        return OpenAIConfig(
            endpoint=openai_config.get('endpoint', 'https://api.openai.com/v1'),
            api_key=openai_config.get('api_key', ''),
            model=openai_config.get('model', 'gpt-4o-mini')
        )
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value
        
        Args:
            key: Configuration key (supports dot notation, e.g., 'mcp.server_url')
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        if not self._config:
            self.load_config()
        
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        
        return value if value is not None else default

