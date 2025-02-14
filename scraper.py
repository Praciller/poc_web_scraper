import time
import re
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By

from chrome_installer import install_chromedriver
from logger import logger

# Ensure ChromeDriver is installed
install_chromedriver()

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

    options = uc.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-gpu")

    driver = uc.Chrome(options=options)
    driver.get(base_url)
    time.sleep(2)

    data = []
    page_number = 1

    while True:
        logger.debug(f"[console.log] Scraping Page {page_number}...")

        try:
            elements = driver.find_elements(By.TAG_NAME, "a")
            logger.debug(f"[console.log] Found {len(elements)} <a> tags on page {page_number}.")

            for elem in elements:
                link = elem.get_attribute("href")
                text = elem.text.strip()
                logger.debug(f"[console.log] Checking link: {link}  text='{text}'")

                if link:
                    ctype, cid = determine_link_type_and_id(link, patterns)
                    if ctype:
                        data.append({
                            "Text": text,
                            "URL": link,
                            "Type": ctype,
                            "ID": cid
                        })
                        logger.debug(f"[console.log] Matched {ctype.upper()} => {link} (ID={cid})")

            next_btn = driver.find_elements(By.LINK_TEXT, str(page_number + 1))
            if next_btn:
                next_btn[0].click()
                time.sleep(2)
                page_number += 1
            else:
                break

        except Exception as e:
            logger.error(f"[console.log] Error on page {page_number}: {e}")
            break

    driver.quit()
    return data

def scrape_each_url(scraped_data, progress_callback=None):
    logger.info("[console.log] Starting scrape_each_url for all scraped data...")

    options = uc.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-gpu")

    driver = uc.Chrome(options=options)
    detailed_data = []

    total_items = len(scraped_data)
    for i, item in enumerate(scraped_data, start=1):
        try:
            logger.debug(f"[console.log] Accessing URL {i}/{total_items}: {item['URL']}")
            driver.get(item["URL"])
            time.sleep(2)

            full_html = driver.page_source
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

    driver.quit()
    logger.debug(f"[console.log] All data from each URL (full HTML included): {detailed_data}")
    return detailed_data
