import time
import re
import requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from logger import logger

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; AI Web Scraper/1.0; +https://example.com)"
}

def determine_link_type_and_id(link, patterns):
    article_regex = patterns.get("article_pattern", "")
    job_regex = patterns.get("job_pattern", "")
    article_id_regex = patterns.get("article_id_capture", "")
    job_id_regex = patterns.get("job_id_capture", "")

    if article_regex:
        if re.search(article_regex, link):
            type_str = "article"
            if article_id_regex:
                m = re.search(article_id_regex, link)
                if m:
                    return (type_str, m.group(1))
            return (type_str, "")

    if job_regex:
        if re.search(job_regex, link):
            type_str = "job"
            if job_id_regex:
                m = re.search(job_id_regex, link)
                if m:
                    return (type_str, m.group(1))
            return (type_str, "")

    if "azubiyo.de/stellenanzeigen/" in link:
        type_str = "job"
        fallback_id_regex = r"https?://www\.azubiyo\.de/stellenanzeigen/([^/]+)/?"
        m = re.search(fallback_id_regex, link)
        if m:
            return (type_str, m.group(1))
        else:
            return (type_str, "")

    return (None, None)

def scrape_all_pages(base_url, patterns):
    logger.info(f"[console.log] Starting scrape_all_pages for base URL: {base_url}")
    data = []
    page_number = 1
    current_url = base_url

    while True:
        logger.debug(f"[console.log] Scraping Page {page_number}: {current_url}")

        try:
            response = requests.get(current_url, headers=HEADERS)
            if response.status_code != 200:
                logger.error(f"[console.log] Failed to retrieve {current_url} (Status: {response.status_code})")
                break

            soup = BeautifulSoup(response.text, "html.parser")
            elements = soup.find_all("a")
            logger.debug(f"[console.log] Found {len(elements)} <a> tags on page {page_number}.")

            for elem in elements:
                link = elem.get("href")
                text = elem.get_text().strip() if elem.get_text() else ""
                logger.debug(f"[console.log] Checking link: {link}  text='{text}'")
                if link:
                    full_link = urljoin(current_url, link)
                    ctype, cid = determine_link_type_and_id(full_link, patterns)
                    if ctype:
                        data.append({
                            "Text": text,
                            "URL": full_link,
                            "Type": ctype,
                            "ID": cid
                        })
                        logger.debug(f"[console.log] Matched {ctype.upper()} => {full_link} (ID={cid})")

            # Look for a pagination link with text equal to the next page number.
            next_page = soup.find("a", string=str(page_number + 1))
            if next_page and next_page.get("href"):
                current_url = urljoin(current_url, next_page.get("href"))
                page_number += 1
                time.sleep(2)  # Delay between pages
            else:
                logger.info(f"[console.log] No next page found after page {page_number}.")
                break

        except Exception as e:
            logger.error(f"[console.log] Error on page {page_number}: {e}")
            break

    return data

def scrape_each_url(scraped_data, progress_callback=None):
    logger.info("[console.log] Starting scrape_each_url for all scraped data...")
    detailed_data = []
    total_items = len(scraped_data)

    for i, item in enumerate(scraped_data, start=1):
        try:
            logger.debug(f"[console.log] Accessing URL {i}/{total_items}: {item['URL']}")
            response = requests.get(item["URL"], headers=HEADERS)
            if response.status_code != 200:
                logger.error(f"[console.log] Failed to retrieve {item['URL']} (Status: {response.status_code})")
                continue

            full_html = response.text
            snippet = full_html[:200].replace('\n',' ')
            logger.debug(f"[console.log] HTML snippet for {item['URL']}: {snippet}...")

            detailed_data.append({
                "Text": item["Text"],
                "URL": item["URL"],
                "Type": item["Type"],
                "ID": item["ID"],
                "HTML": full_html
            })
            logger.info(f"[console.log] Scraped HTML from: {item['URL']}")

        except Exception as e:
            logger.error(f"[console.log] Error scraping {item['URL']}: {e}")

        if progress_callback:
            progress_callback(i, total_items)
        time.sleep(2)  # Delay between requests

    logger.debug(f"[console.log] All detailed data collected: {detailed_data}")
    return detailed_data
