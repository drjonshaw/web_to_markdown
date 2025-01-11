# Web to Markdown Converter

A Python tool that converts web pages to markdown format, with special handling for code blocks and authentication for sites like Medium.

## Features

- Converts web pages to clean markdown format
- Intelligent code block detection and language highlighting
- Handles authentication for sites requiring login (e.g., Medium)
- Maintains session data for authenticated sites
- Smart file versioning with date-based naming
- Configurable through environment variables

## Requirements

- Python 3.13+
- UV package manager
- Playwright

## Installation

1. Clone the repository:
```bash
git clone https://github.com/drjonshaw/web_to_markdown.git
cd web_to_markdown
```

2. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows, use `.venv\Scripts\activate`
```

3. Install dependencies using UV:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv pip install .
```

4. Install Playwright browsers:
```bash
playwright install
```

## Configuration

Create a `.env` file with your configuration:

```env
TARGET_URL="https://example.com/page-to-convert"
TARGET_FILENAME="custom_output_name"
MARKDOWN_OUTPUT_DIR="markdown_output"
```

## Usage

1. Set your target URL and filename in the `.env` file
2. Run the converter:
```bash
python main.py
```

For sites requiring authentication (like Medium):
1. The browser will open automatically
2. Log in with your credentials
3. The session will be saved for future use
4. Subsequent runs will use the saved session

## Output

Files are saved in the `markdown_output` directory with the following naming convention:
- First version: `YYYYMMDD_filename.md`
- Subsequent versions: `YYYYMMDD_filename_v2.md`, `YYYYMMDD_filename_v3.md`, etc.

## License

MIT License 