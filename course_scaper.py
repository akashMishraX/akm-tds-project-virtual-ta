 
import os
import json
import re
from datetime import datetime
from urllib.parse import urljoin, urlparse
from markdownify import markdownify as md
from playwright.sync_api import sync_playwright

BASE_URL = "https://tds.s-anand.net/#/2025-01"
BASE_ORIGIN = "https://tds.s-anand.net"
OUTPUT_DIR = "markdown_files"
METADATA_FILE = "metadata.json"

os.makedirs(OUTPUT_DIR, exist_ok=True)

visited = set()
metadata = []

def sanitize_filename(title):
    """Create a safe filename from title"""
    return re.sub(r'[\\/*?:"<>|]', "_", title).strip().replace(" ", "_")

def normalize_url(url):
    """Ensure consistent URL format"""
    if url.startswith('#'):
        return BASE_ORIGIN + '/#' + url[1:]
    if not url.startswith(('http://', 'https://')):
        return urljoin(BASE_ORIGIN, url)
    return url

def extract_all_links(page):
    """Extract all links from the page, including those in shadow DOM"""
    return page.evaluate('''() => {
        const links = new Set();
        // Regular links
        document.querySelectorAll('a[href]').forEach(a => {
            if (a.href) links.add(a.href);
        });
        // Links in shadow DOM (common in SPAs)
        const walker = (node) => {
            if (node.shadowRoot) {
                node.shadowRoot.querySelectorAll('a[href]').forEach(a => {
                    if (a.href) links.add(a.href);
                });
                node.shadowRoot.querySelectorAll('*').forEach(walker);
            }
        };
        document.querySelectorAll('*').forEach(walker);
        return Array.from(links);
    }''')

def wait_for_content(page):
    """Wait for the main content to load"""
    try:
        page.wait_for_selector('article.markdown-section', timeout=10000)
        return True
    except:
        return False

def save_page_content(page, url):
    """Save the page content as markdown"""
    try:
        if not wait_for_content(page):
            print(f"⏳ Content not found for {url}")
            return None

        title = page.title().split(" - ")[0].strip() or f"page_{len(visited)}"
        filename = sanitize_filename(title)
        filepath = os.path.join(OUTPUT_DIR, f"{filename}.md")

        # Get the main content HTML
        content_html = page.inner_html('article.markdown-section')
        markdown = md(content_html)

        # Save markdown file with front matter
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("---\n")
            f.write(f"title: \"{title}\"\n")
            f.write(f"original_url: \"{url}\"\n")
            f.write(f"downloaded_at: \"{datetime.now().isoformat()}\"\n")
            f.write("---\n\n")
            f.write(markdown)

        # Add to metadata
        metadata.append({
            "title": title,
            "filename": f"{filename}.md",
            "original_url": url,
            "downloaded_at": datetime.now().isoformat()
        })

        return filename
    except Exception as e:
        print(f"❌ Error saving {url}: {str(e)}")
        return None

def crawl_page(page, url):
    """Recursively crawl pages"""
    normalized_url = normalize_url(url)
    
    if normalized_url in visited:
        return
    visited.add(normalized_url)

    print(f"🌐 Visiting: {normalized_url}")
    
    try:
        # Navigate to the page
        page.goto(normalized_url, wait_until="networkidle", timeout=15000)
        
        # Save the content
        filename = save_page_content(page, normalized_url)
        if not filename:
            return

        # Extract all links from the page
        links = extract_all_links(page)
        internal_links = [
            link for link in links
            if urlparse(link).netloc == urlparse(BASE_ORIGIN).netloc
        ]

        # Recursively crawl internal links
        for link in internal_links:
            if link not in visited:
                crawl_page(page, link)

    except Exception as e:
        print(f"🚨 Error crawling {normalized_url}: {str(e)}")

def save_metadata():
    """Save the metadata file"""
    with open(METADATA_FILE, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

def main():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)  # Set headless=False for debugging
        context = browser.new_context()
        page = context.new_page()

        # Start crawling from the base URL
        crawl_page(page, BASE_URL)

        # Save metadata when done
        save_metadata()
        print(f"✅ Saved metadata to {METADATA_FILE}")
        print(f"📁 Total pages saved: {len(metadata)}")

        context.close()
        browser.close()

if __name__ == "__main__":
    main()
