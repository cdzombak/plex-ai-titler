# plex-ai-titler

Use an LLM to generate human-readable titles for Plex media items based on their filenames. This tool only processes media items with unlocked title fields, so you can lock titles you want to preserve.

## Features

- Connects to Plex via MyPlex account or direct URL/token
- Caches Plex credentials for subsequent runs
- Only modifies media items with **unlocked** title fields
- Supports any OpenAI-compatible API endpoint
- Configurable system prompt and temperature
- Dry-run mode for safe previewing

## How It Works

For each media item with an unlocked title field, the tool:

1. Gets the file path relative to the library root (e.g., `DJ Earworm/United State of Pop 2012 (Shine Brighter).mp4`)
2. Sends that path to your configured LLM with your system prompt
3. Sets the item's title to the LLM's response

**Example transformation:**

| Relative Path                                              | Generated Title                                          |
| ---------------------------------------------------------- | -------------------------------------------------------- |
| `DJ Earworm/United State of Pop 2012 (Shine Brighter).mp4` | `DJ Earworm - United State of Pop 2012 (Shine Brighter)` |
| `Concerts/2023-05-15 Red Rocks/full_show.mp4`              | `Live at Red Rocks - May 15, 2023`                       |

The relative path (rather than just the filename) gives the LLM useful context from your folder structure.

## Configuration

The tool requires a YAML configuration file for AI settings. Copy the example and edit it:

```bash
cp config.example.yaml config.yaml
```

The config file supports the following options:

```yaml
ai:
  # OpenAI-compatible API endpoint
  endpoint: "https://api.openai.com/v1"

  # Model to use
  model: "gpt-4"

  # API key (can also be set via OPENAI_API_KEY environment variable)
  api_key: "sk-..."

  # Temperature for generation (0 = deterministic, higher = more creative)
  temperature: 0

  # System prompt for title generation
  system_prompt: |
    You will be given a file path of a video. Extract a meaningful title.
    Your response must contain only the title, with no additional formatting.

    Examples:
    - For a music video: "Artist Name - Song Title (Live from Location)"
    - For a YouTube video: "Creator Name - Video Title"
```

The API key can be set in the config file or via the `OPENAI_API_KEY` environment variable.

## Usage (Docker)

Docker images are available from Docker Hub at [`cdzombak/plex-ai-titler`](https://hub.docker.com/r/cdzombak/plex-ai-titler).

The Docker image stores Plex credentials in `/data/.creds.json` and reads config from `/data/config.yaml`. Mount a volume to `/data` to persist credentials and provide your config.

### Setup

```bash
# Create a local directory for credentials and config
mkdir -p ~/.plex-ai-titler

# Create your config file (see Configuration section above for all options)
cat > ~/.plex-ai-titler/config.yaml << 'EOF'
ai:
  endpoint: "https://api.openai.com/v1"
  model: "gpt-4"
  api_key: "sk-your-api-key-here"
  temperature: 0
  system_prompt: |
    You will be given a file path of a video. Extract a meaningful title.
    Your response must contain only the title, with no additional formatting.
EOF
```

### Running

```bash
docker run -it --rm \
  -v ~/.plex-ai-titler:/data \
  cdzombak/plex-ai-titler
```

On first run, you'll be prompted for Plex.tv credentials. After authentication, the token is saved to the mounted volume and reused automatically on subsequent runs.

### Direct Plex Connection

To bypass MyPlex authentication and connect directly to a Plex server:

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

Then copy and edit the config file as described in the [Configuration](#configuration) section above.

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
