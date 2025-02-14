import together
import json
import os
import time
import re
from bs4 import BeautifulSoup
from streamlit import secrets

from logger import logger

# Load API Key
TOGETHER_API_KEY = secrets["TOGETHER_API_KEY"]

if not TOGETHER_API_KEY:
    logger.error("[console.log] TOGETHER_API_KEY is missing! Exiting.")
    exit()

MAX_TOKENS = 4000
CHUNK_SIZE = 2500

def generate_regex_patterns(base_url):
    prompt = f"""
You are given a base URL: {base_url}.
We have two types of content: 'article' and 'job'.
We want to find:
1) A regex to match any 'article' URL (key: "article_pattern")
2) A regex to match any 'job' URL (key: "job_pattern")
3) A capturing-group regex to extract the 'article ID'
4) A capturing-group regex to extract the 'job ID'

Return it as Python code ending with:
print(solve())  # Output: {{ "article_pattern": "...", ... }}
The final line must be valid JSON.
"""
    try:
        logger.info("[console.log] Calling AI to generate regex patterns.")
        response = together.Completion.create(
            model="meta-llama/Llama-3.3-70B-Instruct-Turbo-Free",
            prompt=prompt,
            max_tokens=MAX_TOKENS,
            temperature=0.2
        )
        result_text = response.choices[0].text.strip()
        logger.debug(f"[console.log] AI regex pattern response:\n{result_text}")

        # Attempt to parse out the JSON from "print(solve()) # Output: {...}"
        pattern = r"print\(solve\(\)\)\s*#\s*Output:\s*(\{.*\})"
        match = re.search(pattern, result_text, flags=re.DOTALL)
        if match:
            dict_str = match.group(1)
            logger.debug(f"[console.log] Extracted dictionary substring:\n{dict_str}")
            patterns = json.loads(dict_str)
            return patterns
        else:
            raise ValueError("Could not parse JSON dictionary from AI result.")
    except Exception as e:
        logger.error(f"[console.log] AI generate_regex_patterns failed: {e}")
        return {
            "article_pattern": r"https://www\.azubiyo\.de/article/(\w+)",
            "job_pattern": r"https://www\.azubiyo\.de/stellenanzeigen/.*",
            "article_id_capture": r"/article/(\w+)",
            "job_id_capture": r"/stellenanzeigen/([^/]+)/?"
        }

def extract_relevant_content(html):
    soup = BeautifulSoup(html, "html.parser")
    for script in soup(["script", "style"]):
        script.extract()
    text_content = " ".join(soup.stripped_strings)
    logger.debug(f"[console.log] Extracted text length: {len(text_content)} chars")
    return text_content

def chunk_text(text, chunk_size=CHUNK_SIZE):
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end
    return chunks

def extract_json(text):
    try:
        json_start = text.find("{")
        json_end = text.rfind("}") + 1
        if json_start == -1 or json_end == 0:
            return None
        json_text = text[json_start:json_end]
        return json.loads(json_text)
    except (ValueError, json.JSONDecodeError):
        logger.error(f"[console.log] Failed JSON Extraction:\n{text}")
        return None

def call_ai_for_chunk(content_type, chunk):
    if content_type == "article":
        prompt = f"""
You are given a PART of an article's text (not the entire text).
Produce a JSON object with these fields ONLY:
{{
  "Title": "",
  "Summary": "",
  "Publication Date": "",
  "Category": "",
  "Link": ""
}}

Remember: this is only PART of the article. Extract whatever relevant info you can.
Text:
{chunk}
"""
    elif content_type == "job":
        prompt = f"""
You are given a PART of a job post (not the entire text).
Produce a JSON object with these fields ONLY:
{{
  "Company": "",
  "Position": "",
  "Contact person": "",
  "Contact email": "",
  "Mobile number": "",
  "Comments": "",
  "Information source": ""
}}

Remember: this is only PART of the job post. Extract whatever relevant info you can.
Text:
{chunk}
"""
    else:
        logger.warning("[console.log] Unrecognized content type in call_ai_for_chunk.")
        return None

    try:
        response = together.Completion.create(
            model="meta-llama/Llama-3.3-70B-Instruct-Turbo-Free",
            prompt=prompt,
            max_tokens=MAX_TOKENS,
            temperature=0.2
        )
        result_text = response.choices[0].text.strip()
        logger.debug(f"[console.log] AI partial result:\n{result_text}")
        return extract_json(result_text)
    except Exception as e:
        logger.error(f"[console.log] AI call failed for chunk: {e}")
        return None

def integrate_partials(content_type, partial_jsons):
    if content_type == "article":
        final_obj = {
            "Title": "",
            "Summary": "",
            "Publication Date": "",
            "Category": "",
            "Link": ""
        }
    else:  # job
        final_obj = {
            "Company": "",
            "Position": "",
            "Contact person": "",
            "Contact email": "",
            "Mobile number": "",
            "Comments": "",
            "Information source": ""
        }

    for partial in partial_jsons:
        if not partial:
            continue
        for key in final_obj:
            if final_obj[key] == "" and key in partial and partial[key]:
                final_obj[key] = partial[key]

    return final_obj

def finalize_prompt_for_merged(content_type, partial_jsons):
    return integrate_partials(content_type, partial_jsons)

def summarize_html_data(detailed_data):
    logger.info("[console.log] Starting AI summarization.")
    summary_table = []

    for idx, item in enumerate(detailed_data, start=1):
        start_time = time.time()
        extracted_text = extract_relevant_content(item["HTML"])
        content_type = item.get("Type", None)
        logger.debug(f"[console.log] Summarizing item {idx}/{len(detailed_data)} | URL: {item['URL']} | Type: {content_type}")

        if content_type not in ["article", "job"]:
            logger.warning(f"[console.log] Unrecognized content type: {content_type}. Skipping.")
            continue

        chunks = chunk_text(extracted_text)
        logger.debug(f"[console.log] Split text into {len(chunks)} chunk(s) for {item['URL']}.")

        partial_jsons = []
        for chunk_idx, chunk in enumerate(chunks, start=1):
            logger.debug(f"[console.log] Processing chunk {chunk_idx}/{len(chunks)} (length={len(chunk)}).")
            partial = call_ai_for_chunk(content_type, chunk)
            partial_jsons.append(partial)

        final_json = finalize_prompt_for_merged(content_type, partial_jsons)

        if content_type == "article":
            final_json["Link"] = item["URL"]
        elif content_type == "job":
            final_json["Information source"] = item["URL"]

        elapsed = time.time() - start_time
        logger.info(f"[console.log] Done summarizing {item['URL']} in {elapsed:.2f}s.")
        summary_table.append(final_json)

    return summary_table
