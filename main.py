import streamlit as st
import pandas as pd
import os
import time

from scraper import scrape_all_pages, scrape_each_url
from ai_analyzer import summarize_html_data, generate_regex_patterns
from utils import save_summaries_to_files
from logger import logger

# Load API Key from environment variable
TOGETHER_API_KEY = st.secrets["TOGETHER_API_KEY"]

if not TOGETHER_API_KEY:
    st.error("⚠️ TOGETHER_API_KEY not found! Set it in your environment variables.")
    logger.error("TOGETHER_API_KEY not found - cannot proceed.")
    st.stop()

# Hard-coded password
REQUIRED_PASSWORD = "Secret123"

st.title("AI Web Scraper")

# Create two columns for input (80%) & search button (20%)
col1, col2 = st.columns([8, 2])

with col1:
    url = st.text_input(
        label="Enter the URL to scrape:",
    )

with col2:
    start_search = st.button("Search", type="primary", help="Start scraping")

# We'll store final results in these variables
scraped_data = None
detailed_data = None
summary_table = None

# Step 1: If user clicks "Search" and we have a URL, ask for a password
if start_search and url:
    st.session_state["attempt_scrape"] = True

# If user triggered search, show password prompt (emulating a modal)
if st.session_state.get("attempt_scrape", False):
    with st.expander("Password Required", expanded=True):
        input_pw = st.text_input("Enter password to proceed:", type="password")
        password_ok = st.button("Validate Password")

        if password_ok:
            if input_pw == REQUIRED_PASSWORD:
                # Password is correct: proceed with pipeline
                logger.info("[console.log] Password correct. Proceeding with scraping...")
                st.session_state["password_check"] = True
            else:
                logger.error("[console.log] Wrong password. Aborting.")
                st.error("Incorrect password. Scraping aborted.")
                st.session_state["password_check"] = False
                st.session_state["attempt_scrape"] = False

# Step 2: If password is correct, run the entire process
if st.session_state.get("password_check", False):

    progress_bar = st.progress(0)
    percent = 0

    with st.spinner("Running entire process. Please wait..."):
        logger.info(f"[console.log] Starting AI-based regex for URL: {url}")
        patterns = generate_regex_patterns(url)
        percent += 25
        progress_bar.progress(percent)

        scraped_data = scrape_all_pages(url, patterns)
        logger.info(f"[console.log] Found {len(scraped_data)} items after pagination scraping.")
        percent += 25
        progress_bar.progress(percent)

        if scraped_data:
            detailed_data = scrape_each_url(
                scraped_data,
                progress_callback=lambda current, total: None
            )
        percent += 25
        progress_bar.progress(percent)

        if detailed_data:
            summary_table = summarize_html_data(detailed_data)
        percent = 100
        progress_bar.progress(percent)

    if summary_table:
        st.write("## AI Understanding & Summary")
        df = pd.DataFrame(summary_table)
        st.write(df)

        if st.button("Export to Excel"):
            save_summaries_to_files(df, "output/summarized_data")
            st.success("Data exported as summarized_data.csv and summarized_data.xlsx!")
    else:
        st.warning("No summary or no data found. Check logs for details.")

    st.session_state["attempt_scrape"] = False
    st.session_state["password_check"] = False
