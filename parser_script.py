import re
import json
import time
from datetime import datetime
from urllib.parse import urljoin
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from lxml import html as lxml_html
import csv
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

# === CONFIG ===
MAX_PAGES = 10
OUTPUT_FILE = "itif_results.csv"
DELAY_BETWEEN_PAGES = 2
MAX_WORKERS = 10

# === HELPERS ===
def clean_text(text):
    """Clean and normalize text"""
    if not text:
        return ""
    text = text.strip().replace("\xa0", " ").replace("\u200b", " ")
    return re.sub(r"\s+", " ", text)

def to_date(raw):
    """Convert date to YYYY-MM-DD"""
    if not raw:
        return ""
    raw = clean_text(raw)
    match = re.match(r"^(\d{4}-\d{2}-\d{2})", raw)
    if match:
        return match.group(1)
    try:
        return datetime.strptime(raw, "%B %d, %Y").strftime("%Y-%m-%d")
    except:
        return raw

def setup_driver():
    """Setup FAST driver for Selenium"""
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")

    prefs = {
        "profile.default_content_setting_values": {
            "images": 2,
            "stylesheets": 2,
        }
    }
    options.add_experimental_option("prefs", prefs)
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
    return webdriver.Chrome(options=options)

def get_page_html_fast(driver, url):
    """Get rendered HTML from a listing page"""
    driver.get(url)
    try:
        WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.TAG_NAME, "h2")))
        time.sleep(0.5)
    except:
        pass
    return driver.page_source

def parse_article_list(page_html):
    """Extract article links from a listing page"""
    tree = lxml_html.fromstring(page_html)
    links = tree.xpath("//a[h2[contains(@class,'font-gothicprobold')]]/@href")
    return links

# === STRICT PDF DETECTION ===
def extract_pdf_from_downloads(tree, base_url):
    """Find PDF links only inside the 'Downloads' button area"""
    UC, lc = "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"
    pdf_xpath = (
        "//a[contains(translate(@href,'{UC}','{lc}'),'.pdf')]["
        "  ancestor::*[self::div or self::section or self::aside or self::nav]"
        "  [ .//*[self::a or self::button or self::span or self::div]"
        "     [translate(normalize-space(string(.)),'{UC}','{lc}')='downloads']"
        "  ]"
        "]"
        "/@href"
    ).format(UC=UC, lc=lc)
    hrefs = tree.xpath(pdf_xpath)
    if hrefs:
        return urljoin(base_url, hrefs[0].strip())
    return ""

# === ARTICLE PARSER ===
def parse_article_with_requests(url, max_retries=3):
    """Download and parse a single article page"""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    for attempt in range(max_retries):
        try:
            r = requests.get(url, headers=headers, timeout=15)
            tree = lxml_html.fromstring(r.content)

            article = {"url": url}

            # Title
            title = tree.xpath("//h1//text()")
            article["title"] = clean_text(" ".join(title))

            # Date 
            pubdate = ""
            for script_text in tree.xpath("//script[@type='application/ld+json']/text()"):
                try:
                    data = json.loads(script_text)
                    if isinstance(data, dict) and data.get("@type") in {"Article", "NewsArticle", "BlogPosting"}:
                        raw = data.get("datePublished") or data.get("dateCreated") or data.get("dateModified")
                        if raw:
                            pubdate = to_date(raw)
                            break
                except:
                    continue
            if not pubdate:
                dates = tree.xpath("//time/@datetime | //time/text()")
                pubdate = to_date(dates[0]) if dates else ""
            article["pubdate"] = pubdate

            # Authors
            authors = tree.xpath("//main//a[contains(@href, '/person/')]/text()")
            article["authors"] = "; ".join([clean_text(a) for a in authors if clean_text(a)])

            # Full text
            text_nodes = tree.xpath(
                "//article//*[self::p or self::li]/descendant-or-self::text() | "
                "//main//div[contains(@class,'content')]//*[self::p or self::li]/descendant-or-self::text()"
            )
            article["article_body"] = " ".join([clean_text(t) for t in text_nodes if clean_text(t)])

            # PDF 
            article["pdf_link"] = extract_pdf_from_downloads(tree, url)
            return article

        except Exception:
            if attempt < max_retries - 1:
                time.sleep(1)
                continue
            return None
    return None

# === MAIN FUNCTION ===
def main():
    """Main scraping routine"""
    driver = setup_driver()
    all_articles = []

    try:
        page_num = 1
        while True:
            # Build page URL
            url = "https://itif.org/publications/" if page_num == 1 else f"https://itif.org/publications/?page={page_num}"
            page_html = get_page_html_fast(driver, url)
            links = parse_article_list(page_html)
            if not links:
                break

            article_urls = [urljoin(url, link) for link in links]


    # Save results
    if all_articles:
        with open(OUTPUT_FILE, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["title", "pubdate", "authors", "article_body", "pdf_link", "url"],
            )
            writer.writeheader()
            writer.writerows(all_articles)
        print(f"Saved {len(all_articles)} articles to {OUTPUT_FILE}")
    else:
        print("No data saved")

if __name__ == "__main__":
    main()
