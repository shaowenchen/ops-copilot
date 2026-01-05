# Ops-copilot

AI-powered DevOps assistant that helps you with operations tasks using LLM and MCP tools.

## Installation

### Prerequisites

- Python 3.8 or higher
- pip

### Install Dependencies

```bash
pip install -r requirements.txt
```

## Usage

### Quick Start

```bash
# Set environment variables
export MCP_SERVER_URL="http://localhost/mcp"
export OPENAI_API_KEY="sk-your-key"
export OPENAI_API_HOST="https://api.openai.com/v1"
export OPENAI_API_MODEL="gpt-4o-mini"

# Run copilot
python main.py

# Or with verbose logging
python main.py --verbose
```

### Configuration

Configuration can be provided through:
1. **Command-line arguments** (highest priority)
2. **Environment variables** (medium priority)
3. **config.yaml file** (lowest priority)

#### Configuration File

Create a `configs/config.yaml` file:

```yaml
# MCP Server Configuration
mcp:
  server_url: "http://localhost/mcp"
  timeout: "600s"
  token: ""

# OpenAI Configuration
openai:
  endpoint: "https://api.openai.com/v1"
  api_key: "your-api-key-here"
  model: "gpt-4o-mini"

# Chat Configuration
chat:
  max_history: 8
  verbose: false
```

#### Environment Variables

Environment variables follow the config file structure: `SECTION_KEY` (all uppercase, one underscore per level).

These will override values in config.yaml:

**MCP Configuration:**
- `MCP_SERVER_URL`: MCP server URL (e.g., http://localhost/mcp)
- `MCP_TIMEOUT`: MCP request timeout (default: 600s)
- `MCP_TOKEN`: MCP server token (if authentication is enabled)

**Note:** The tools list is cached for 5 minutes (300 seconds) to reduce API calls.

**OpenAI Configuration:**
- `OPENAI_ENDPOINT`: OpenAI API endpoint (default: https://api.openai.com/v1)
- `OPENAI_API_KEY`: OpenAI API key
- `OPENAI_MODEL`: OpenAI model (default: gpt-4o-mini)

**Chat Configuration:**
- `CHAT_MAX_HISTORY`: Maximum chat history length (default: 8)
- `CHAT_VERBOSE`: Enable verbose logging (true/false, default: false)

**Backward Compatibility:**
- `OPENAI_API_HOST` or `OPENAI_API_BASE`: Same as `OPENAI_ENDPOINT`
- `OPENAI_API_MODEL`: Same as `OPENAI_MODEL`

#### Command Line Flags

- `--endpoint, -e`: OpenAI API endpoint (overrides OPENAI_API_HOST)
- `--model, -m`: OpenAI model (overrides OPENAI_API_MODEL)
- `--key, -k`: OpenAI API key (overrides OPENAI_API_KEY)
- `--mcp-server`: MCP server URL (overrides MCP_SERVER_URL)
- `--mcp-token`: MCP server token (overrides MCP_TOKEN)
- `--mcp-timeout`: MCP timeout (overrides config/env)
- `--verbose, -v`: Enable verbose/debug logging
- `--history`: Chat history length (default: from config or 8)
- `--config, -c`: Path to config.yaml file (default: ./configs/config.yaml)

### Example

#### Using Config File (Recommended)

```bash
# 1. Create config file (if not exists)
# Edit configs/config.yaml with your values

# 2. Run
python main.py

# Or with verbose logging
python main.py --verbose
```

#### Using Environment Variables

```bash
# Set environment variables
export MCP_SERVER_URL="http://localhost/mcp"
export OPENAI_API_KEY="sk-your-key"
export OPENAI_API_HOST="https://api.openai.com/v1"
export OPENAI_API_MODEL="gpt-4o-mini"

# Run
python main.py --verbose
```

#### Using Command Line Flags

```bash
# Run with flags (highest priority)
python main.py \
  --endpoint https://api.openai.com/v1 \
  --model gpt-4o-mini \
  --key sk-your-key \
  --mcp-server http://localhost/mcp \
  --verbose

# Or specify custom config file
python main.py --config /path/to/config.yaml
```

## Features

- **AI-powered assistance**: Uses OpenAI's GPT models for intelligent DevOps assistance
- **MCP tool integration**: Automatically calls MCP tools (SOPS, logs, events, metrics) based on conversation
- **Interactive chat**: Terminal-based interactive chat interface
- **Multi-language support**: Supports both English and Chinese
- **Configurable**: Flexible configuration through flags and environment variables
- **Automatic tool selection**: LLM automatically selects and executes appropriate MCP tools
- **Verbose logging**: Detailed logging of tool calls and LLM interactions

## Architecture

This project contains:
- `ops_copilot/`: Core package
  - `core/`: Core modules (OpenAI client, Chat)
  - `tools/`: MCP tool integration
  - `utils/`: Utility modules (logging)
- `main.py`: Command-line entry point

### Project Structure

```
ops-copilot/
├── main.py                 # Command-line entry point
├── requirements.txt        # Python dependencies
├── README.md              # This file
├── env.example            # Environment variables example
└── ops_copilot/           # Core package
    ├── __init__.py
    ├── core/              # Core modules
    │   ├── __init__.py
    │   ├── openai_client.py  # OpenAI API client
    │   └── chat.py           # Chat with MCP tool calling
    ├── tools/             # MCP tools
    │   ├── __init__.py
    │   └── mcp_tool.py    # MCP tool wrapper
    └── utils/             # Utilities
        ├── __init__.py
        └── logging.py     # Logging utilities
```

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run with verbose logging
python main.py --verbose

# Run with custom configuration
python main.py \
  --endpoint https://api.openai.com/v1 \
  --model gpt-4o-mini \
  --key sk-your-key \
  --mcp-server http://localhost/mcp \
  --verbose
```

## Docker Usage

### Build Docker Image

```bash
docker build -t ops-copilot .
```

### Run with Environment Variables

```bash
# Run interactively with environment variables
docker run -it --rm \
  -e MCP_SERVER_URL="http://your-mcp-server/mcp" \
  -e MCP_TOKEN="your-token" \
  -e MCP_TIMEOUT="600s" \
  -e OPENAI_API_KEY="sk-your-key" \
  -e OPENAI_API_HOST="https://api.openai.com/v1" \
  -e OPENAI_API_MODEL="gpt-4o-mini" \
  ops-copilot

# With verbose mode
docker run -it --rm \
  -e MCP_SERVER_URL="http://your-mcp-server/mcp" \
  -e OPENAI_API_KEY="sk-your-key" \
  -e OPENAI_API_HOST="https://api.openai.com/v1" \
  ops-copilot --verbose

# With custom config file (mount configs directory)
docker run -it --rm \
  -v $(pwd)/configs:/app/configs \
  -e MCP_SERVER_URL="http://your-mcp-server/mcp" \
  -e OPENAI_API_KEY="sk-your-key" \
  ops-copilot --config /app/configs/config.yaml
```

### Run with .env File

```bash
# Create .env file with your configuration
cat > .env << EOF
MCP_SERVER_URL=http://your-mcp-server/mcp
MCP_TOKEN=your-token
OPENAI_API_KEY=sk-your-key
OPENAI_API_HOST=https://api.openai.com/v1
OPENAI_API_MODEL=gpt-4o-mini
EOF

# Run with .env file
docker run -it --rm \
  --env-file .env \
  ops-copilot
```

### Run with Command Line Arguments

```bash
docker run -it --rm \
  -e MCP_SERVER_URL="http://your-mcp-server/mcp" \
  -e OPENAI_API_KEY="sk-your-key" \
  ops-copilot \
  --endpoint https://api.openai.com/v1 \
  --model gpt-4o-mini \
  --mcp-server http://your-mcp-server/mcp \
  --verbose
```

**Note:** The `-it` flags are required for interactive mode. Use `--rm` to automatically remove the container when it exits.

### Using Pre-built Images

Pre-built Docker images are available on:
- **Docker Hub**: `docker.io/<username>/ops-copilot:latest`
- **GitHub Container Registry**: `ghcr.io/<username>/ops-copilot:latest`

```bash
# Pull and run from Docker Hub
docker run -it --rm \
  -e MCP_SERVER_URL="http://your-mcp-server/mcp" \
  -e OPENAI_API_KEY="sk-your-key" \
  docker.io/<username>/ops-copilot:latest

# Pull and run from GitHub Container Registry
docker run -it --rm \
  -e MCP_SERVER_URL="http://your-mcp-server/mcp" \
  -e OPENAI_API_KEY="sk-your-key" \
  ghcr.io/<username>/ops-copilot:latest
```

## CI/CD

This project uses GitHub Actions to automatically build and push Docker images:

- **Docker Hub**: Images are pushed on push to `main`/`master` branch and on tag creation
- **GitHub Container Registry**: Images are pushed to `ghcr.io` on push to `main`/`master` branch

### Required Secrets

For Docker Hub push, configure these secrets in GitHub repository settings:
- `DOCKERHUB_USERNAME`: Your Docker Hub username
- `DOCKERHUB_TOKEN`: Your Docker Hub access token

For GitHub Container Registry, no additional secrets are needed (uses `GITHUB_TOKEN`).

## License

Same as the original project.
