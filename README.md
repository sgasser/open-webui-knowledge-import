# Open WebUI Knowledge Import

Bulk import your documents into Open WebUI knowledge bases. Point it at a folder, and it automatically creates knowledge bases and uploads all your files.

## Quick Start

```bash
# 1. Setup
cp .env.example .env
# Edit .env with your API key (get from Open WebUI → Settings → Account)

pip install -r requirements.txt

# 2. Import your documents
./knowledge_import.py /path/to/documents

# That's it! ✨
```

## Features

- **Fast** - Concurrent uploads (5 workers)
- **Reliable** - Automatic retries with exponential backoff
- **Safe** - Health checks and dry-run mode
- **Smart** - Auto-detects single or multiple knowledge bases

## Usage

```bash
# Basic import
./knowledge_import.py /path/to/documents

# Filter by extension
./knowledge_import.py --extensions .pdf,.txt /path/to/documents

# Verbose logging
./knowledge_import.py --verbose /path/to/documents

# Using environment variables (no .env file)
export OPENWEBUI_API_KEY=sk-your-key
export OPENWEBUI_URL=http://localhost:8080
./knowledge_import.py /path/to/documents
```

## Get API Key

Open WebUI → Settings → Account → API Key

## Development

### Run Tests
```bash
python3 test_knowledge_import.py
```

### Code Quality
```bash
# Check code
ruff check knowledge_import/ knowledge_import.py test_knowledge_import.py

# Auto-fix issues
ruff check --fix knowledge_import/ knowledge_import.py test_knowledge_import.py
```

### Preview Import
```bash
./knowledge_import.py --dry-run examples/documents
```

## License

MIT
