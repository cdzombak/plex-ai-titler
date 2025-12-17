# plex-ai-titler

Use an LLM to generate human-readable titles for Plex media items based on their filenames. This tool only processes media items with unlocked title fields, so you can lock titles you want to preserve.

## Features

- Connects to Plex via MyPlex account or direct URL/token
- Caches Plex credentials for subsequent runs
- Only modifies media items with **unlocked** title fields
- Provides the file path relative to the library root to the LLM for context
- Supports any OpenAI-compatible API endpoint
- Configurable system prompt and temperature
- Dry-run mode by default for safe previewing

## Usage (Docker)

Docker images are available from Docker Hub at [`cdzombak/plex-ai-titler`](https://hub.docker.com/r/cdzombak/plex-ai-titler).

### Running

The Docker image stores credentials in `/data/.creds.json` and reads config from `/data/config.yaml`. Mount a volume to `/data`:

```bash
# Create a local directory for credentials and config
mkdir -p ~/.plex-ai-titler

# Copy and edit the example config
cp config.example.yaml ~/.plex-ai-titler/config.yaml
# Edit ~/.plex-ai-titler/config.yaml with your AI settings

# Run interactively
docker run -it --rm \
  -v ~/.plex-ai-titler:/data \
  cdzombak/plex-ai-titler
```

On first run, you'll be prompted for Plex.tv credentials. After authentication, the token is saved to the mounted volume and reused automatically on subsequent runs.

### Direct Connection

```bash
docker run -it --rm \
  -v ~/.plex-ai-titler:/data \
  cdzombak/plex-ai-titler \
  --url http://192.168.1.100:32400 \
  --token YOUR_PLEX_TOKEN
```

### Building Locally

```bash
docker build -t plex-ai-titler .
```

## Usage (Python)

### Installation

Requires Python 3.10+.

```bash
git clone https://github.com/cdzombak/plex-ai-titler.git
cd plex-ai-titler
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Configuration

Copy the example config and edit it:

```bash
cp config.example.yaml config.yaml
```

Edit `config.yaml` to set your AI endpoint, model, and system prompt. The API key can be set in the config file or via the `OPENAI_API_KEY` environment variable.

### Running

```bash
python plex_ai_titler.py
```

The program will interactively:

1. Prompt for Plex.tv credentials (with 2FA support), or use cached credentials
2. Let you select a server and library
3. Ask whether to perform a dry run or real update
4. For each item with an unlocked title, generate a new title using the LLM
5. Preview or apply the title changes

### Credential Caching

After successful MyPlex authentication, your auth token is cached in `.creds.json`. On subsequent runs, the cached token is used automatically.

Set the `PLEX_CREDS_FILE` environment variable to change the credentials file location. Delete `.creds.json` to clear cached credentials.

## Configuration File

The config file (`config.yaml`) supports the following options:

```yaml
ai:
  # OpenAI-compatible API endpoint
  endpoint: "https://api.openai.com/v1"

  # Model to use
  model: "gpt-4"

  # API key (can also use OPENAI_API_KEY env var)
  api_key: "sk-..."

  # Temperature (0.0 = deterministic)
  temperature: 0

  # System prompt for title generation
  system_prompt: |
    You will be given a filename of a video...
```

## Command-Line Options

```
-v, --version          Show version and exit
-c, --config PATH      Path to YAML config file (default: config.yaml)

Direct connection:
  --url URL            Plex server URL
  --token TOKEN        Plex authentication token

MyPlex authentication:
  -u, --username USER  Plex.tv username
  -p, --password PASS  Plex.tv password
```

## License

GNU GPL v3; see [LICENSE](LICENSE) in this repository.

## Author

Chris Dzombak

- [dzombak.com](https://www.dzombak.com)
- [GitHub @cdzombak](https://github.com/cdzombak)
