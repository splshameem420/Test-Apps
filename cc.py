import io
import sys
import xml.etree.ElementTree as ET

import newspaper
import requests

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# curl_cffi থাকলে সেটা ব্যবহার হবে (Cloudflare ব্লক এড়াতে), না থাকলে সাধারণ requests
try:
    from curl_cffi import requests as http
    IMPERSONATE = {"impersonate": "chrome"}
    print("curl_cffi ব্যবহার হচ্ছে")
except ImportError:
    http = requests
    IMPERSONATE = {}
    print("সাধারণ requests ব্যবহার হচ্ছে")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/xml,text/xml,text/html;q=0.9,*/*;q=0.8",
    "Accept-Language": "bn-BD,bn;q=0.9,en;q=0.8",
    "Referer": "https://www.tsports.com/",
}

SITEMAP_URL = "https://www.tsports.com/news_sitemap.xml"

NS = {
    "s": "http://www.sitemaps.org/schemas/sitemap/0.9",
    "n": "http://www.google.com/schemas/sitemap-news/0.9",
}


def fetch(url):
    r = http.get(url, headers=HEADERS, timeout=15, **IMPERSONATE)
    if r.status_code != 200:
        raise Exception(f"HTTP {r.status_code}")
    return r


def get_sitemap_entries(limit=5):
    r = fetch(SITEMAP_URL)
    root = ET.fromstring(r.content)

    items = []
    for u in root.findall("s:url", NS):
        loc = u.find("s:loc", NS).text.strip()
        title = u.find("n:news/n:title", NS)
        pub = u.find("n:news/n:publication_date", NS)
        items.append({
            "url": loc,
            "title": title.text.strip() if title is not None and title.text else None,
            "date": pub.text if pub is not None else "",
        })

    items.sort(key=lambda x: x["date"], reverse=True)
    return items[:limit]


def scrape_tsports(visited_urls, config):
    news_items = []

    try:
        entries = get_sitemap_entries(limit=5)
    except Exception as e:
        print(f"Error reading T Sports sitemap: {e}")
        return news_items

    for entry in entries:
        url = entry["url"]
        if url in visited_urls:
            continue

        try:
            res = fetch(url)
            article = newspaper.Article(url, config=config)
            article.download(input_html=res.text)
            article.parse()

            text = article.text.strip()
            if len(text) > 100:
                news_items.append({
                    "title": entry["title"] or article.title.strip(),
                    "text": text,
                    "url": url,
                    "image": article.top_image or None,
                })
            else:
                print(f"টেক্সট খুব ছোট ({len(text)} অক্ষর), বাদ: {url}")
        except Exception as e:
            print(f"Error scraping T Sports ({url}): {e}")

    return news_items


# ---------- টেস্ট অংশ ----------
config = newspaper.Config()
config.browser_user_agent = HEADERS["User-Agent"]
config.request_timeout = 15

items = scrape_tsports([], config)

print(f"\nমোট পোস্ট পাওয়া গেছে: {len(items)}\n")

for i, item in enumerate(items, 1):
    print(f"--- পোস্ট {i} ---")
    print("টাইটেল :", item["title"])
    print("লিংক   :", item["url"])
    print("ছবি    :", item["image"])
    print("টেক্সট :", len(item["text"]), "অক্ষর")
    print("শুরুর অংশ:", item["text"][:150].replace("\n", " "))
    print()
