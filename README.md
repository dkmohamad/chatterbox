# Chatterbox

A local voice agent with configurable character personalities. Chatterbox listens for speech, holds a back-and-forth conversation, and replies in character. Everything runs locally — no cloud APIs required.

## Quick Start

```bash
./setup.sh              # one-time: venv, deps, models, whisper.cpp build
source .venv/bin/activate
python -m chatterbox    # start talking
```

## How It Works

Speak → Chatterbox transcribes, thinks, and replies → continue the conversation → 60s silence clears context.

```
Listening → [speech ends] → Thinking → Speaking → Listening → ...
```

## Configuration

Each personality gets its own config file (e.g. `config/momo.toml`). See [docs/usage.md](docs/usage.md) for details.

## Documentation

- [Usage & Configuration](docs/usage.md)
- [Architecture](docs/architecture.md)
- [Dependencies](docs/dependencies.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Build Progress](TODO.md)
- [Project Structure](STRUCTURE.md)

## Tests

```bash
source .venv/bin/activate
pytest -v
```

## Isolation

Chatterbox is contained within this directory:

- **Python deps** are in `.venv/` (not system-wide)
- **whisper.cpp** is built in `vendor/` (not installed globally)
- **Models** are downloaded to `models/` (gitignored)
- **Ollama** is the only system-level install — it runs as a separate service and doesn't affect other software. If already installed, setup.sh won't reinstall it.
- **No system config** is modified (no systemd units, no cron, no PATH changes)

To fully remove: delete this directory, and optionally `ollama` if you don't need it elsewhere.
