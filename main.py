import asyncio
import os
import re
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from playwright.async_api import async_playwright
import html2text

# Load environment variables
load_dotenv(override=True)  # Force reload of environment variables

# Configuration
TARGET_URL = os.getenv("TARGET_URL")
MARKDOWN_OUTPUT_DIR = os.getenv("MARKDOWN_OUTPUT_DIR", "markdown_output")

# Configure html2text
h = html2text.HTML2Text()
h.ignore_links = False
h.ignore_images = False
h.ignore_emphasis = False
h.body_width = 0  # Don't wrap text
h.unicode_snob = True  # Use Unicode characters instead of their ascii pseudonyms
h.code_block_style = "fenced"  # Use ``` style blocks

def detect_code_language(content: str) -> str:
    """Try to detect the programming language of a code block."""
    # Simple language detection based on file extensions and common patterns
    if re.search(r'\.(tsx?|jsx?)(\s|$)', content, re.IGNORECASE):
        return 'typescript'
    elif re.search(r'(import|export|class|interface|function\s+\w+\s*\()', content):
        return 'typescript'
    elif re.search(r'\.(py|python)(\s|$)', content, re.IGNORECASE):
        return 'python'
    elif re.search(r'(def|class|import)\s', content):
        return 'python'
    elif re.search(r'\.(sh|bash)(\s|$)', content, re.IGNORECASE):
        return 'bash'
    elif re.search(r'(npm|yarn|pnpm|cd|ls|mkdir)\s', content):
        return 'bash'
    return ''

def is_code_line(line: str) -> bool:
    """Determine if a line is likely part of a code block."""
    # Check if line starts with 4 spaces (common markdown code block indicator)
    if line.startswith('    '):
        return True
    # Check for common code patterns
    code_patterns = [
        r'^\s*(import|export|class|function|def|return|const|let|var)\s',
        r'^\s*[<>{}()\[\]]+\s*$',  # Lines with just brackets/braces
        r'^\s*\w+\s*[=:]\s*',  # Assignment or object property
        r'^\s*[})\]];?\s*$',  # Closing brackets
        r'^\s*\/\/',  # JavaScript/TypeScript comments
        r'^\s*#',  # Python/Bash comments
    ]
    return any(re.search(pattern, line) for pattern in code_patterns)

def process_code_blocks(content: str) -> str:
    """Process the content to properly format code blocks."""
    lines = content.split('\n')
    processed_lines = []
    in_code_block = False
    code_block_content = []
    consecutive_empty_lines = 0
    
    for i, line in enumerate(lines):
        stripped_line = line.lstrip()
        
        # Handle code block detection
        if line.startswith('    ') or (in_code_block and (is_code_line(line) or not stripped_line)):
            if not in_code_block:
                # Start new code block
                code_block_content = []
                in_code_block = True
            
            # Remove exactly 4 spaces from the start if present
            if line.startswith('    '):
                code_block_content.append(line[4:])
            else:
                code_block_content.append(line)
            
            # Reset empty line counter
            consecutive_empty_lines = 0 if stripped_line else consecutive_empty_lines + 1
            
            # Only close block if we see multiple empty lines followed by non-code
            if consecutive_empty_lines > 1 and i + 1 < len(lines):
                next_line = lines[i + 1].lstrip()
                if next_line and not is_code_line(next_line):
                    # End code block
                    if code_block_content:
                        code = '\n'.join(code_block_content)
                        lang = detect_code_language(code)
                        processed_lines.append(f'```{lang}')
                        processed_lines.extend(code_block_content)
                        processed_lines.append('```')
                        processed_lines.append('')
                    in_code_block = False
                    code_block_content = []
                    consecutive_empty_lines = 0
        else:
            # Not a code line
            if in_code_block:
                # Check if we should end the code block
                if not stripped_line:
                    consecutive_empty_lines += 1
                elif not is_code_line(line):
                    # End code block
                    if code_block_content:
                        code = '\n'.join(code_block_content)
                        lang = detect_code_language(code)
                        processed_lines.append(f'```{lang}')
                        processed_lines.extend(code_block_content)
                        processed_lines.append('```')
                        processed_lines.append('')
                    in_code_block = False
                    code_block_content = []
                    consecutive_empty_lines = 0
            processed_lines.append(line)
    
    # Handle any remaining code block at the end
    if in_code_block and code_block_content:
        code = '\n'.join(code_block_content)
        lang = detect_code_language(code)
        processed_lines.append(f'```{lang}')
        processed_lines.extend(code_block_content)
        processed_lines.append('```')
        processed_lines.append('')
    
    # Join lines back together
    content = '\n'.join(processed_lines)
    
    # Replace any remaining pre tags with code fences
    content = re.sub(
        r'<pre><code>(.*?)</code></pre>',
        lambda m: f'```{detect_code_language(m.group(1))}\n{m.group(1)}\n```\n',
        content,
        flags=re.DOTALL
    )
    
    # Clean up duplicate navigation sections (common in documentation sites)
    content = re.sub(r'(On this page.*?)\1', r'\1', content, flags=re.DOTALL)
    
    # Format inline code
    content = re.sub(r'`([^`]+)`', r'`\1`', content)
    
    return content

async def setup():
    """Ensure the markdown output directory exists."""
    Path(MARKDOWN_OUTPUT_DIR).mkdir(exist_ok=True)

async def get_page_content(url: str) -> str:
    """Fetch the webpage content using Playwright."""
    async with async_playwright() as p:
        # Use persistent context to maintain login state
        user_data_dir = Path.home() / ".playwright-data"
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False  # Show browser for authentication
        )
        
        page = await browser.new_page()
        
        # Set viewport size to ensure proper rendering
        await page.set_viewport_size({"width": 1280, "height": 1080})
        
        print(f"Navigating to: {url}")
        
        try:
            # Navigate to the URL with longer timeout
            await page.goto(url, wait_until="networkidle", timeout=60000)
            
            # Check if we need to authenticate
            if "Sign in with Apple" in await page.content():
                print("Authentication required. Please sign in with your Apple ID.")
                print("The browser window will stay open for 60 seconds to allow authentication.")
                print("After signing in, the content will be automatically captured.")
                
                # Wait for authentication (up to 60 seconds)
                try:
                    # Wait for either the article content or the member-only content to appear
                    await page.wait_for_selector('article, div[class*="postContent"]', timeout=60000)
                except Exception as e:
                    print("Authentication timeout or error. Please try again.")
                    raise e
            
            # Wait for the main content to load
            await page.wait_for_load_state("networkidle")
            
            # Additional wait for dynamic content
            await asyncio.sleep(2)
            
            # Get the main content
            content = await page.content()
            
            # Close the browser
            await browser.close()
            return content
            
        except Exception as e:
            print(f"Error accessing the page: {e}")
            if not browser.is_closed():
                await browser.close()
            raise e

def get_next_version_number(base_filepath: Path) -> int:
    """Get the next available version number for a file."""
    # Check for existing versions
    pattern = re.compile(rf"{re.escape(base_filepath.stem)}_v(\d+){re.escape(base_filepath.suffix)}$")
    existing_versions = []
    
    # Look for files with version numbers
    for file in base_filepath.parent.glob(f"{base_filepath.stem}_v*{base_filepath.suffix}"):
        if match := pattern.match(file.name):
            existing_versions.append(int(match.group(1)))
    
    # Also check if the base file exists (will be considered as v1)
    if base_filepath.exists():
        existing_versions.append(1)
    
    return max(existing_versions, default=0) + 1 if existing_versions else 1

def save_markdown(content: str, url: str):
    """Save the markdown content to a file."""
    # Create a filename based on the date and target filename
    date = datetime.now().strftime("%Y%m%d")
    
    # Get target filename from environment or generate from URL
    target_filename = os.getenv("TARGET_FILENAME")
    if not target_filename:
        # Create a safe filename from the URL as fallback
        target_filename = url.split("/")[-1].split("#")[0][:30]  # Take last part of URL, remove fragment, limit length
        target_filename = "".join(c if c.isalnum() else "_" for c in target_filename)  # Make filename safe
    
    # Create base filename without version number
    base_filename = f"{date}_{target_filename}.md"
    base_filepath = Path(MARKDOWN_OUTPUT_DIR) / base_filename
    
    # If the file already exists, get the next version number
    if base_filepath.exists() or list(base_filepath.parent.glob(f"{base_filepath.stem}_v*{base_filepath.suffix}")):
        version = get_next_version_number(base_filepath)
        filename = f"{date}_{target_filename}_v{version}.md"
    else:
        filename = base_filename
    
    filepath = Path(MARKDOWN_OUTPUT_DIR) / filename
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"# Web Page Conversion\n\nSource: {url}\n\n")
        f.write(content)
    
    print(f"Markdown saved to: {filepath}")

async def main():
    """Main application function."""
    if not TARGET_URL:
        print("Error: TARGET_URL not set in .env file")
        return
    
    print(f"Processing URL: {TARGET_URL}")
    
    # Ensure output directory exists
    await setup()
    
    try:
        # Get the page content
        html_content = await get_page_content(TARGET_URL)
        
        # Convert HTML to Markdown
        md_content = h.handle(html_content)
        
        # Process code blocks and clean up formatting
        md_content = process_code_blocks(md_content)
        
        # Save the markdown
        save_markdown(md_content, TARGET_URL)
    except Exception as e:
        print(f"Error processing URL: {e}")

if __name__ == "__main__":
    asyncio.run(main())
