import os
import json
import asyncio
import urllib.parse
import shutil
import aiohttp
import argparse
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from dotenv import load_dotenv

load_dotenv(override=True)

TARGET_URLS = [
    "https://swd.bits-goa.ac.in/dashboard/",
    "https://www.bits-pilani.ac.in/goa/"
]

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

def get_headers(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Referer": "https://www.bits-pilani.ac.in/"
    }
    if SESSION_COOKIE and "swd.bits-goa.ac.in" in url:
        headers["Cookie"] = SESSION_COOKIE
    return headers

def parse_cookies_for_playwright(cookie_string: str, url: str):
    domain = urllib.parse.urlparse(url).hostname
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
        async with session.get(url, headers=get_headers(url), timeout=15) as r:
            if r.status == 200:
                content = await r.read()
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

async def scavenge_url(target_url, auto_approve, history):
    print(f"\n🎯 Target Page: {target_url}")
    
    discovered_pdf_links = set()
    domain_name = urllib.parse.urlparse(target_url).hostname.replace(".", "_")
    screenshot_filename = f"screenshot_{domain_name}.png"
    staging_screenshot_path = os.path.join(STAGING_DIR, screenshot_filename)
    permanent_screenshot_path = os.path.join(SCREENSHOTS_DIR, screenshot_filename)

    print("\n📸 Launching browser to capture dashboard screenshot for user verification...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        if SESSION_COOKIE and "swd.bits-goa.ac.in" in target_url:
            cookies = parse_cookies_for_playwright(SESSION_COOKIE, target_url)
            if cookies:
                await context.add_cookies(cookies)

        page = await context.new_page()
        try:
            print(f"Navigating to {target_url}...")
            await page.goto(target_url, wait_until="networkidle", timeout=20000)
        except Exception:
            try:
                await page.goto(target_url, wait_until="domcontentloaded", timeout=15000)
            except Exception as e:
                print(f"⚠️ Navigation warning: {e}")

        try:
            await page.screenshot(path=staging_screenshot_path, full_page=True)
            shutil.copyfile(staging_screenshot_path, permanent_screenshot_path)
            print(f"✅ Dashboard screenshot saved to: {staging_screenshot_path}")
        except Exception as e:
            print(f"❌ Failed to capture screenshot: {e}")

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

    print("\n⚡ Checking static HTML content for PDF links...")
    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        try:
            async with session.get(target_url, headers=get_headers(target_url), timeout=10) as response:
                if response.status == 200:
                    html_content = await response.text()
                    soup = BeautifulSoup(html_content, "html.parser")
                    for a in soup.find_all(["a", "link"], href=True):
                        full_url = urllib.parse.urljoin(target_url, a['href'])
                        cleaned = full_url.split("#")[0].strip()
                        if ".pdf" in cleaned.lower():
                            discovered_pdf_links.add(cleaned)
                else:
                    print(f"⚠️ HTTP fetch returned status: {response.status}")
        except Exception as e:
            print(f"⚠️ HTTP fetch error: {e}")

        print(f"\n🔍 Total PDF links found on {target_url}: {len(discovered_pdf_links)}")
        
        downloaded_count = 0
        dest_dir = POLICIES_DIR if auto_approve else STAGING_DIR
        status_text = "Auto-Approved" if auto_approve else "Staged for Vetting"
        
        for pdf_url in discovered_pdf_links:
            if pdf_url in history:
                continue

            parsed_path = urllib.parse.urlparse(pdf_url).path
            raw_name = os.path.basename(parsed_path) or "document.pdf"
            if not raw_name.lower().endswith(".pdf"):
                raw_name += ".pdf"
            safe_pdf_name = urllib.parse.unquote(raw_name)
            
            pdf_path = os.path.join(dest_dir, safe_pdf_name)
            meta_path = pdf_path + ".meta.json"
            
            print(f"\n📥 Downloading ({status_text}): {safe_pdf_name}")
            print(f"   URL: {pdf_url}")
            
            success = await download_pdf(session, pdf_url, pdf_path)
            if success:
                meta_content = {
                    "source_url": target_url,
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

    return downloaded_count

async def scavenge_all(auto_approve):
    if SESSION_COOKIE:
        print(f"🔑 Using Session Cookie from .env for authentication.")
    else:
        print("⚠️ No SESSION_COOKIE found in .env. Note: Dashboard might redirect to login.")

    history = load_history()
    total_downloaded = 0
    
    for url in TARGET_URLS:
        try:
            count = await scavenge_url(url, auto_approve, history)
            total_downloaded += count
        except Exception as e:
            print(f"❌ Failed processing {url}: {e}")

    print("\n" + "="*60)
    print(f"🎉 Complete! Downloaded {total_downloaded} PDFs across {len(TARGET_URLS)} sites.")
    dest_str = "policies folder" if auto_approve else "staging folder (ready for manual approval)"
    print(f"Documents are saved in the {dest_str}.")
    print("="*60)

def main():
    parser = argparse.ArgumentParser(description="Scavenge PDFs from BITS Pilani sites.")
    parser.add_argument("--auto-approve", action="store_true", help="Auto-approve all downloaded PDFs to policies dir.")
    parser.add_argument("--stage", action="store_true", help="Stage all downloaded PDFs for manual vetting.")
    args = parser.parse_args()

    if args.auto_approve:
        auto_approve = True
    elif args.stage:
        auto_approve = False
    else:
        print("By default, scavenged documents must be manually vetted using the Admin UI.")
        print("You can auto-approve them directly into the knowledge base if you prefer.")
        choice = input("Do you want to AUTO-APPROVE all downloaded documents? (y/n): ").strip().lower()
        auto_approve = choice == 'y'

    asyncio.run(scavenge_all(auto_approve))

if __name__ == "__main__":
    main()
