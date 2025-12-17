# Ops-copilot

AI-powered DevOps assistant that helps you with operations tasks using LLM. This is a standalone version of the copilot functionality extracted from the ops project.

## Installation

### From Source
```bash
git clone https://github.com/shaowenchen/ops-copilot.git
cd ops-copilot
make build
```

### Using Go Install
```bash
go install github.com/shaowenchen/ops-copilot@latest
```

## Usage

```bash
ops-copilot copilot [flags]
```

### Flags

- `--endpoint, -e`: OpenAI API endpoint (default: https://api.openai.com/v1)
- `--model, -m`: OpenAI model to use (default: gpt-4o-mini)
- `--key, -k`: OpenAI API key
- `--opsserver`: Ops server endpoint
- `--opstoken`: Ops server token
- `--verbose, -v`: Verbose output
- `--history`: Chat history length (default: 5)
- `--silence, -s`: Silence mode
- `--runtimeimage`: Runtime image for tasks (default: registry.cn-beijing.aliyuncs.com/opshub/ubuntu:22.04)

### Environment Variables

- `OPENAI_API_HOST` or `OPENAI_API_BASE` or `endpoint`: OpenAI API endpoint
- `OPENAI_API_MODEL` or `model`: OpenAI model
- `OPENAI_API_KEY` or `key`: OpenAI API key
- `OPS_SERVER` or `opsserver`: Ops server endpoint
- `OPS_TOKEN` or `opstoken`: Ops server token

## Example

```bash
export OPENAI_API_KEY="sk-your-key"
export OPS_SERVER="https://your-ops-server.com"
export OPS_TOKEN="your-token"

ops-copilot copilot
```

## Development

```bash
# Install dependencies
make deps

# Build
make build

# Run
./ops-copilot copilot

# Test
make test
```

## Features

- **AI-powered assistance**: Uses OpenAI's GPT models for intelligent DevOps assistance
- **Pipeline integration**: Works with ops pipelines and clusters
- **Interactive chat**: Terminal-based interactive chat interface
- **Multi-language support**: Supports both English and Chinese
- **Configurable**: Flexible configuration through flags and environment variables

## Architecture

This project contains:
- `cmd/`: Command-line interface
- `pkg/copilot/`: Core copilot functionality (moved from ops project)
- `main.go`: Entry point

The project depends on the ops project for API types and utilities but provides a standalone copilot experience.
