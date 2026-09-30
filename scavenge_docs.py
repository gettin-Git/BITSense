import os
import json
import asyncio
import urllib.parse
import shutil
import aiohttp
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from dotenv import load_dotenv

load_dotenv(override=True)

TARGET_URL = "https://swd.bits-goa.ac.in/dashboard/"
STAGING_DIR = os.path.join(os.path.dirname(__file__), "data", "staging")
POLICIES_DIR = os.path.join(os.path.dirname(__file__), "data", "policies")
SCREENSHOTS_DIR = os.path.join(os.path.dirname(__file__), "data", "screenshots")
HISTORY_FILE = os.path.join(os.path.dirname(__file__), "data", "scavenged_history.json")

os.makedirs(STAGING_DIR, exist_ok=True)
os.makedirs(POLICIES_DIR, exist_ok=True)
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

SESSION_COOKIE = os.getenv("SESSION_COOKIE", "")

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()

def save_history(history):
    with open(HISTORY_FILE, "w") as f:
        json.dump(list(history), f, indent=4)

def get_headers():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Referer": "https://swd.bits-goa.ac.in/"
    }
    if SESSION_COOKIE:
        headers["Cookie"] = SESSION_COOKIE
    return headers

def parse_cookies_for_playwright(cookie_string: str, domain: str = "swd.bits-goa.ac.in"):
    """Parse cookie string into Playwright cookie objects."""
    cookies = []
    if not cookie_string:
        return cookies
    for part in cookie_string.split(";"):
        if "=" in part:
            k, v = part.strip().split("=", 1)
            cookies.append({
                "name": k.strip(),
                "value": v.strip(),
                "domain": domain,
                "path": "/"
            })
    return cookies

async def download_pdf(session, url, pdf_path):
    try:
        async with session.get(url, headers=get_headers(), timeout=15) as r:
            if r.status == 200:
                content = await r.read()
                # Verify that it's actually a PDF (starts with %PDF)
                if content.startswith(b"%PDF"):
                    with open(pdf_path, "wb") as f:
                        f.write(content)
                    return True
                else:
                    print(f"  ⚠️ Warning: Response for {url} is not a valid PDF binary.")
            else:
                print(f"  ❌ Failed with HTTP status {r.status} for {url}")
    except Exception as e:
        print(f"  ❌ Failed to download PDF {url}: {e}")
    return False

async def scavenge_dashboard_pdfs():
    print(f"🎯 Target Page: {TARGET_URL}")
    print("📋 Policy: Downloading ALL PDFs from this page only (no keyword filtering).")
    
    if SESSION_COOKIE:
        print(f"🔑 Using Session Cookie from .env for authentication.")
    else:
        print("⚠️ No SESSION_COOKIE found in .env. Note: Dashboard might redirect to login.")

    history = load_history()
    discovered_pdf_links = set()

    screenshot_filename = "screenshot_swd_goa_dashboard.png"
    staging_screenshot_path = os.path.join(STAGING_DIR, screenshot_filename)
    permanent_screenshot_path = os.path.join(SCREENSHOTS_DIR, screenshot_filename)

    # 1. Launch Playwright to capture the user verification screenshot and extract dynamic DOM links
    print("\n📸 Launching browser to capture dashboard screenshot for user verification...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        # Inject session cookie into browser context
        cookies = parse_cookies_for_playwright(SESSION_COOKIE)
        if cookies:
            await context.add_cookies(cookies)

        page = await context.new_page()
        try:
            print(f"Navigating to {TARGET_URL}...")
            await page.goto(TARGET_URL, wait_until="networkidle", timeout=20000)
        except Exception:
            # Fallback if networkidle times out
            try:
                await page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=15000)
            except Exception as e:
                print(f"⚠️ Navigation warning: {e}")

        # Capture screenshot for human user verification
        try:
            await page.screenshot(path=staging_screenshot_path, full_page=True)
            shutil.copyfile(staging_screenshot_path, permanent_screenshot_path)
            print(f"✅ Dashboard screenshot saved to: {staging_screenshot_path}")
            print("   (This screenshot will be presented to the user to visually verify how to locate documents on the portal)")
        except Exception as e:
            print(f"❌ Failed to capture screenshot: {e}")

        # Extract all links directly from the rendered DOM
        try:
            dom_links = await page.evaluate("""() => {
                const links = [];
                document.querySelectorAll('a[href]').forEach(a => links.push(a.href));
                document.querySelectorAll('embed[src]').forEach(e => links.push(e.src));
                document.querySelectorAll('iframe[src]').forEach(i => links.push(i.src));
                return links;
            }""")
            for link in dom_links:
                cleaned = link.split("#")[0].strip()
                if ".pdf" in cleaned.lower():
                    discovered_pdf_links.add(cleaned)
        except Exception as e:
            print(f"⚠️ DOM link extraction warning: {e}")

        await browser.close()

    # 2. Also perform raw HTTP fetch with BeautifulSoup to catch any static links
    print("\n⚡ Checking static HTML content for PDF links...")
    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        try:
            async with session.get(TARGET_URL, headers=get_headers(), timeout=10) as response:
                if response.status == 200:
                    html_content = await response.text()
                    
                    # Save HTML for debugging to see why no PDFs are found
                    with open("debug_page.html", "w", encoding="utf-8") as f:
                        f.write(html_content)
                        
                    soup = BeautifulSoup(html_content, "html.parser")
                    for a in soup.find_all(["a", "link"], href=True):
                        full_url = urllib.parse.urljoin(TARGET_URL, a['href'])
                        cleaned = full_url.split("#")[0].strip()
                        if ".pdf" in cleaned.lower():
                            discovered_pdf_links.add(cleaned)
                else:
                    print(f"⚠️ HTTP fetch returned status: {response.status}")
        except Exception as e:
            print(f"⚠️ HTTP fetch error: {e}")

        # 3. Process and download discovered PDFs
        print(f"\n🔍 Total PDF links found on {TARGET_URL}: {len(discovered_pdf_links)}")
        
        downloaded_count = 0
        for pdf_url in discovered_pdf_links:
            # Parse clean filename
            parsed_path = urllib.parse.urlparse(pdf_url).path
            raw_name = os.path.basename(parsed_path) or "document.pdf"
            if not raw_name.lower().endswith(".pdf"):
                raw_name += ".pdf"
            safe_pdf_name = urllib.parse.unquote(raw_name)
            
            pdf_path = os.path.join(POLICIES_DIR, safe_pdf_name)
            meta_path = pdf_path + ".meta.json"
            
            print(f"\n📥 Downloading (Auto-Approved): {safe_pdf_name}")
            print(f"   URL: {pdf_url}")
            
            success = await download_pdf(session, pdf_url, pdf_path)
            if success:
                # Save metadata linking to the source URL and visual verification screenshot
                meta_content = {
                    "source_url": TARGET_URL,
                    "pdf_url": pdf_url,
                    "screenshot": permanent_screenshot_path,
                    "pdf_path": pdf_path,
                    "pdf_name": safe_pdf_name
                }
                with open(meta_path, "w") as mf:
                    json.dump(meta_content, mf, indent=4)
                    
                history.add(pdf_url)
                save_history(history)
                downloaded_count += 1
                print(f"   ✅ Saved to: {pdf_path}")
                print(f"   📄 Metadata saved: {meta_path}")

    print("\n" + "="*60)
    print(f"🎉 Complete! Downloaded {downloaded_count} PDFs from {TARGET_URL}.")
    print(f"🖼️ Verification screenshot ready at: {permanent_screenshot_path}")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(scavenge_dashboard_pdfs())
