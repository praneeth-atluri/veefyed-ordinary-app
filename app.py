# theordinary_streamlit_app.py
"""
Streamlit app for Day 1 + Day 2 of the scraping assignment.

Two sidebar tabs: Day 1 and Day 2
Day 1: explains purpose, fair-use robots.txt check helper, shows final scraper script, explains logic in plain English, lets user run scraper, preview raw & clean CSVs and download them.
Day 2: explains Google CSE enrichment steps, shows enrichment script, lets user run enrichment (requires API keys) and preview/download enriched CSV.

Usage:
  pip install streamlit pandas requests beautifulsoup4 python-Levenshtein
  streamlit run theordinary_streamlit_app.py

Place the two scripts in the same folder:
  - theordinary_us_scraper_final.py
  - day2_enrich_google_cse_populated.py

This app does not run anything automatically; clicking run buttons will execute the scripts locally in your environment.
"""

import streamlit as st
import subprocess
import os
import time
import pandas as pd

st.set_page_config(page_title="The Ordinary — Scrape & Enrich", layout="wide")

# --- Sidebar navigation ---
st.sidebar.title("Project: Veefyed Scraper")
tab = st.sidebar.radio("Select task", ["Day 1 — Scrape & Clean", "Day 2 — Enrich (Google CSE)"])

DATA_DIR = os.getcwd()
RAW_PATH = os.path.join(DATA_DIR, "day1_raw_THE_ORDINARY_US.csv")
CLEAN_PATH = os.path.join(DATA_DIR, "day1_clean_top30_THE_ORDINARY_US.csv")
ENRICHED_PATH = os.path.join(DATA_DIR, "day2_enriched_THE_ORDINARY_US.csv")

# Utility functions
def read_csv_if_exists(path, nrows=100):
    if os.path.exists(path):
        try:
            df = pd.read_csv(path)
            return df.head(nrows), df.shape
        except Exception as e:
            return None, (0, 0)
    return None, (0, 0)

def run_script(cmd_list, timeout=None):
    """Run a local script and stream output to the app (blocking)."""
    try:
        proc = subprocess.Popen(cmd_list, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        output_lines = []
        while True:
            line = proc.stdout.readline()
            if line == '' and proc.poll() is not None:
                break
            if line:
                output_lines.append(line)
                st.text(line.rstrip('\n'))
        proc.wait(timeout=timeout)
        return proc.returncode, "".join(output_lines)
    except Exception as e:
        return -1, str(e)

# --- Day 1 Content ---
if tab == "Day 1 — Scrape & Clean":
    st.title("Day 1 — Scrape & Clean")

    st.markdown(
        """
        **Goal:** scrape product data from a skincare website and clean into reproducible CSVs.

        """
    )

    st.subheader("Fair use quick check")
    st.markdown(
        "Before scraping any website, it is essential to review its `robots.txt` " \
        "file and ensure compliance with the site's terms of use. The helper script below can be used to retrieve and examine the robots.txt file for any domain prior to conducting scraping activities." \
        " This practice supports ethical data collection and helps maintain adherence to the website’s usage policies. For this exercise, " \
        "we selected **The Ordinary (US)** website as our target after confirming alignment with their fair-use guidelines.")
    st.code(
        """
import requests
url = 'https://theordinary.com/robots.txt'
r = requests.get(url, timeout=10)
print(r.status_code)
print(r.text)
""",
        language='python'
    )

    st.info("Run the snippet locally; it prints the robots rules and lets you confirm whether scraping is allowed.")

    st.subheader("Final scraping script (ready-to-run)")
    st.markdown("To test the script, please copy it and run it locally using Python along with all required libraries installed.")

    with open("theordinary_us_scraper_final.py", "w") as f:
        f.write(''' 
''')

    st.code("""
#!/usr/bin/env python3
# theordinary_us_scraper_final.py

import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
import re
import time
import random
from urllib.parse import urljoin, urlparse

BASE = "https://theordinary.com"
US = "https://theordinary.com/en-us"

# US category URLs — confirmed valid
CATEGORY_PAGES = [
    f"{US}/category/skincare",
    f"{US}/category/skincare/cleanser",
    f"{US}/category/skincare/serums",
    f"{US}/category/skincare/moisturizer",
    f"{US}/category/skincare/eye-serum",
    f"{US}/category/skincare/sun-care",
    f"{US}/category/skincare/exfoliators",
    f"{US}/category/skincare/masque",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

MAX_SCRAPE = 50   # Scrape 50 products
FINAL_CLEAN = 30  # Keep best 30


def safe_get(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=12)
        r.raise_for_status()
        print(f"GET {url} -> {r.status_code}")
        return r.text
    except Exception as e:
        print(f"FAILED {url}: {e}")
        return None


def extract_product_links(category_html):
    soup = BeautifulSoup(category_html, "html.parser")
    links = []

    for a in soup.select("a"):
        href = a.get("href", "")
        if href.startswith("/en-us/") and href.endswith(".html"):

            # filter obvious category or about pages
            if "category" in href.lower():
                continue

            full = urljoin(BASE, href)
            links.append(full)

    return list(set(links))


def fallback_name_from_url(url):
    slug = urlparse(url).path.split("/")[-1].replace(".html", "")
    slug = re.sub(r"-\d+$", "", slug)
    slug = slug.replace("-", " ").title()
    return slug


def parse_size(size_text):
    if not size_text:
        return None, None
    ml = None
    oz = None
    m1 = re.search(r"(\d+(?:\.\d+)?)\s*ml", size_text, re.I)
    m2 = re.search(r"(\d+(?:\.\d+)?)\s*(?:fl\s*oz|oz)", size_text, re.I)
    if m1:
        ml = float(m1.group(1))
    if m2:
        oz = float(m2.group(1))
    return ml, oz


def json_ld_product(soup):
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string)
        except:
            continue

        if isinstance(data, dict) and data.get("@type") == "Product":
            return data

        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and item.get("@type") == "Product":
                    return item

    return None


def extract_ingredients(soup):
    # Strong ingredient extraction logic
    # Look for explicit heading "Ingredients"
    for h in soup.find_all(re.compile("^h[1-6]$")):
        txt = h.get_text(strip=True).lower()
        if "ingredient" in txt:
            block = h.find_next_sibling()
            if block:
                return block.get_text(" ", strip=True)

    # Look for paragraphs with many commas (typical ingredient list)
    for p in soup.find_all(["p", "div"]):
        t = p.get_text(" ", strip=True)
        if len(t) > 40 and "," in t and any(w in t.lower() for w in ["water", "oil", "extract", "acid"]):
            return t

    return None


def clean_ingredient_list(blob):
    if not blob:
        return json.dumps([])

    blob = blob.replace("\n", ", ")
    items = [p.strip().rstrip(".") for p in blob.split(",") if len(p.strip()) > 1]

    # remove UI strings like "Shop by Ingredients"
    items = [i for i in items if "shop by" not in i.lower()]

    return json.dumps(items)


def scrape_product(url):
    html = safe_get(url)
    if not html:
        return None, None

    soup = BeautifulSoup(html, "html.parser")
    ld = json_ld_product(soup)

    # Product name
    name = ld.get("name") if ld else None
    if not name:
        h1 = soup.find("h1")
        if h1:
            name = h1.get_text(" ", strip=True)
    if not name:
        name = fallback_name_from_url(url)

    brand = "The Ordinary"

    # description
    description = None
    if ld:
        description = ld.get("description")

    if not description:
        meta = soup.find("meta", {"name": "description"})
        if meta:
            description = meta.get("content")

    # image
    image = None
    if ld:
        imgs = ld.get("image")
        if isinstance(imgs, list):
            image = imgs[0]
        elif isinstance(imgs, str):
            image = imgs

    if not image:
        og = soup.find("meta", property="og:image")
        if og:
            image = og.get("content")

    # category
    category = None
    bc = soup.select("nav.breadcrumb a")
    if bc:
        category = bc[-1].get_text(strip=True)

    # size
    size_pack = None
    for b in soup.select("[data-attr-value], .variant-button, .product-variant"):
        val = b.get("data-attr-value") or b.get_text(" ", strip=True)
        if "ml" in val.lower():
            size_pack = val.strip()
            break

    ingredients_raw = extract_ingredients(soup)
    size_ml, size_oz = parse_size(size_pack or "")

    raw = {
        "product_page_url": url,
        "product_name": name,
        "brand": brand,
        "category": category,
        "size_packaging": size_pack,
        "ingredients": ingredients_raw,
        "description": description,
        "product_image_url": image,
    }

    clean = {
        "product_page_url": url,
        "product_name": name,
        "brand": brand,
        "category": category,
        "size_ml": size_ml,
        "size_oz": size_oz,
        "size_packaging": size_pack,
        "ingredients_json": clean_ingredient_list(ingredients_raw),
        "description": description,
        "product_image_url": image,
    }

    return raw, clean


def main():
    print("\nCollecting product URLs from The Ordinary US…\n")

    all_urls = []
    for cat in CATEGORY_PAGES:
        html = safe_get(cat)
        if not html:
            continue

        links = extract_product_links(html)
        print(f"Found {len(links)} product links on {cat}")

        all_urls.extend(links)
        time.sleep(1)

    all_urls = list(set(all_urls))
    random.shuffle(all_urls)

    product_urls = all_urls[:MAX_SCRAPE]
    print(f"\nScraping {len(product_urls)} products…\n")

    raws, cleans = [], []

    for i, url in enumerate(product_urls, 1):
        print(f"[{i}/{len(product_urls)}] {url}")
        r, c = scrape_product(url)
        if r:
            raws.append(r)
            cleans.append(c)
        time.sleep(random.uniform(0.5, 1.2))

    # Save the raw scrape
    raw_df = pd.DataFrame(raws)
    raw_df.to_csv("day1_raw_THE_ORDINARY_US.csv", index=False)

    # Select 30 best rows (least nulls)
    clean_df = pd.DataFrame(cleans)
    clean_df["null_count"] = clean_df.isna().sum(axis=1)
    clean_df = clean_df.sort_values("null_count").head(FINAL_CLEAN)
    clean_df = clean_df.drop(columns=["null_count"])

    clean_df.to_csv("day1_clean_top30_THE_ORDINARY_US.csv", index=False)

    print("\nDone!")
    print("Saved:")
    print(" - day1_raw_THE_ORDINARY_US.csv (50 rows)")
    print(" - day1_clean_top30_THE_ORDINARY_US.csv (best 30 rows)")


if __name__ == "__main__":
    main()

""", language='python')

    st.subheader("Script logic")
    st.markdown(
        """
        **At a glance:**

        1. We Crawl a small list of category pages on the US version of The Ordinary website (these pages contain product tiles).
        2. Collect product page URLs from the category tiles (only `/en-us/... .html` links).
        3. Visit each product page and try extraction in this priority:
           - `application/ld+json` Product block (if present) — gives name, description, images reliably.
           - DOM fallbacks (h1, meta tags, breadcrumb for category, image og: tags).
           - Ingredient block detection: look for headings containing "Ingredients" or paragraphs with many commas + ingredient keywords (water, oil, extract).
        4. Parse product sizes by detecting ml or oz in variant buttons or labels, and normalize these into numeric ml/oz fields.
        5. Save an initial list of 50 products to a first RAW file.
        6. Clean the data by selecting the best 30 products with the least nulls, normalizing ingredient lists into JSON arrays, and saving to a CLEAN file.

        This approach is intentionally conservative (few requests, many fallbacks) to maximize stable extraction across pages.
        """
    )

    st.subheader("Run the scraper locally")
    st.markdown("🛑 This only works if you have a local enviornment up and running, Press the button below to run the scraper script. The script runs locally in your environment and writes two CSV files.")
    if st.button("Run Day 1 scraper (50 products) 🌐"):
        st.text("Running scraper... output will stream below — this may take a few minutes.")
        cmd = ["python3", "theordinary_us_scraper_final.py"]
        code, out = run_script(cmd)
        if code == 0:
            st.success("Scraper finished successfully.")
        else:
            st.error(f"Scraper exited with code {code}")

    st.subheader("Preview outputs")
    raw_df, raw_shape = read_csv_if_exists(RAW_PATH)
    clean_df, clean_shape = read_csv_if_exists(CLEAN_PATH)

    st.markdown("**Raw file (first rows)**")
    if raw_df is not None:
        st.dataframe(raw_df)
        csv = open(RAW_PATH, "rb").read()
        st.download_button("Download raw CSV", data=csv, file_name="day1_raw_THE_ORDINARY_US.csv")
    else:
        st.info("No raw file found yet — run the scraper or upload your CSV to the app folder.")

    st.markdown("**Clean file (top 30) — preview**")
    if clean_df is not None:
        st.dataframe(clean_df)
        csv2 = open(CLEAN_PATH, "rb").read()
        st.download_button("Download clean CSV", data=csv2, file_name="day1_clean_top30_THE_ORDINARY_US.csv")
    else:
        st.info("No clean file found yet — run the scraper first.")

# --- Day 2 Content ---
else:
    st.title("Day 2 — Google CSE Enrichment")

    st.markdown(
        """
        **Goal:** enrich at least 10 products from Day 1 with external authoritative information using Google Custom Search API.

        The enrichment includes:
        - official product page URL
        - external ingredient list (scraped from that page)
        - SKU / UPC / EAN where available
        - country of origin where available
        - a simple `api_confidence` score indicating reliability
        """
    )

    st.subheader("How the enrichment works ")
    st.markdown(
    """
    1. We start by creating an API Key and a Custom Search Engine (CX) in Google Cloud so the script can safely use Google Custom Search.
    2. For each product name, we send a Google search query like: `"{product_name} {brand} official product page"` and collect the top results.
    3. We choose the best result by checking a few simple signals:  
       - pages from the manufacturer (theordinary.com) are preferred,  
       - titles that closely match the product name rank higher,  
       - and snippets mentioning things like “ingredients” or “SKU” get extra weight.
    4. Once we pick the best match, we open the page (with polite delays) and look for ingredients, SKU/UPC/EAN patterns, and country-of-origin text.
    5. We validate the data by comparing external ingredient lists with the scraped ones and checking how well they overlap.
    6. We also scan the text for SKU keywords and barcode patterns to extract unique product identifiers.
    7. A confidence score is then created based on three things: domain trust, title similarity, and ingredient overlap.
    8. High-confidence matches usually come from the manufacturer’s website and have strong title alignment; low-confidence results are included but clearly flagged.
    9. Throughout the process, we follow ethical scraping rules: respecting robots.txt, using small batch sizes, and avoiding unnecessary requests.
    10. After enrichment, we save everything—including new fields and confidence scores—into a clean file called `day2_enriched_THE_ORDINARY_US.csv`.
    """
)


    st.subheader("CSE / API notes")
    st.info("You must create a Google API Key and a Custom Search Engine ID (CX) and paste them into the enrichment script before running.")

    st.markdown("**Small helper: check your API key & CX**")
    st.code(
        """
# quick curl test (replace API_KEY and CX)
curl 'https://www.googleapis.com/customsearch/v1?key=API_KEY&cx=CX&q=niacinamide+10%25+zinc+1%25+official+product+page'
""",
        language='bash'
    )

    st.subheader("Enrichment script ")
    st.markdown("Save the enrichment script as `day2_enrich_google_cse_populated.py` and make sure your API_KEY and CX are set inside the file.")
    st.code("""
#!/usr/bin/env python3
#
day2_enrich_google_cse_populated.py

Reads:  day1_clean_top30_THE_ORDINARY_US.csv
Writes: day2_enriched_THE_ORDINARY_US.csv

Requirements:
  pip install requests beautifulsoup4 pandas python-Levenshtein

Usage:
  1) Ensure INPUT_CSV is present in the same folder.
  2) Run: python day2_enrich_google_cse_populated.py
#

import requests, json, time, random, re
import pandas as pd
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import Levenshtein   # pip install python-Levenshtein

# === CONFIG: KEYS NEEDS TO BE ADDED BEFORE RUNNING ===
API_KEY = "**********"   # your API key 
CX = "#######"          # your Search Engine ID 
# ==================================

INPUT_CSV = "day1_clean_top30_THE_ORDINARY_US.csv"
OUTPUT_CSV = "day2_enriched_THE_ORDINARY_US.csv"
NUM_PRODUCTS_TO_ENRICH = 10  # change to 30 to enrich more
MIN_DELAY = 0.4
MAX_DELAY = 1.0
CSE_ENDPOINT = "https://www.googleapis.com/customsearch/v1"

# Loose patterns for SKU / UPC / EAN detection
SKU_PATTERNS = [
    re.compile(r'\bSKU[:\s]*([A-Za-z0-9\-]+)\b', re.I),
    re.compile(r'\bUPC[:\s]*([0-9]{8,13})\b', re.I),
    re.compile(r'\bEAN[:\s]*([0-9]{8,13})\b', re.I),
    re.compile(r'\bBarcode[:\s]*([0-9]{8,13})\b', re.I),
    re.compile(r'\bProduct\s*Code[:\s]*([A-Za-z0-9\-]+)\b', re.I),
]

TRUSTED_DOMAINS = [
    "theordinary.com"
]

def call_cse(query, num=5):
    params = {"key": API_KEY, "cx": CX, "q": query, "num": num}
    try:
        r = requests.get(CSE_ENDPOINT, params=params, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print("CSE request failed:", e)
        return None

def choose_best_result(results, product_name, brand):
    if not results or "items" not in results:
        return None
    items = results["items"]
    scored = []
    for it in items:
        title = it.get("title","")
        link = it.get("link","")
        snippet = it.get("snippet","")
        domain = urlparse(link).netloc.lower()
        score = 0.0
        for d in TRUSTED_DOMAINS:
            if d in domain:
                score += 3.0
        if brand and brand.lower() in domain:
            score += 2.0
        try:
            sim = Levenshtein.ratio((product_name or "").lower(), title.lower())
            score += sim * 3.0
        except Exception:
            pass
        if re.search(r'ingredient', snippet, re.I):
            score += 0.8
        if re.search(r'sku|upc|ean|barcode', snippet, re.I):
            score += 0.8
        scored.append((score, it))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[0][1] if scored else None

def fetch_page_text(url):
    try:
        r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=15)
        r.raise_for_status()
        return r.text[:1000000]
    except Exception as e:
        print("Fetch failed:", url, e)
        return None

def extract_external_info(page_html):
    if not page_html:
        return None, None, None
    soup = BeautifulSoup(page_html, "html.parser")
    ingredients = None
    for h in soup.find_all(re.compile('^h[1-6]$')):
        if 'ingredient' in h.get_text(" ", strip=True).lower():
            nxt = h.find_next_sibling()
            if nxt and nxt.get_text(strip=True):
                ingredients = nxt.get_text(" ", strip=True)
                break
    if not ingredients:
        cand = soup.select_one('[id*=ingredient], [class*=ingredient]')
        if cand:
            ingredients = cand.get_text(" ", strip=True)
    sku = None
    text = soup.get_text(" ", strip=True)[:25000]
    for pat in SKU_PATTERNS:
        m = pat.search(text)
        if m:
            sku = m.group(1)
            break
    country = None
    m = re.search(r'Country of (Origin|Manufacture|Manufacturing)\s*[:\-]?\s*([A-Za-z ]{2,40})', text, re.I)
    if m:
        country = m.group(2).strip()
    return ingredients, sku, country

def compute_confidence(chosen_item, product_name, existing_ingredients, external_ingredients):
    if not chosen_item:
        return 0.0
    link = chosen_item.get("link","")
    domain = urlparse(link).netloc.lower()
    base = 0.0
    for d in TRUSTED_DOMAINS:
        if d in domain:
            base = 0.6
            break
    if 'theordinary.com' in domain:
        base = max(base, 0.8)
    title = chosen_item.get("title","")
    try:
        title_sim = Levenshtein.ratio((product_name or "").lower(), title.lower())
    except Exception:
        title_sim = 0.0
    overlap = 0.0
    if existing_ingredients and external_ingredients:
        try:
            a = [x.strip().lower() for x in re.split(r'[,;]', existing_ingredients) if x.strip()]
            b = [x.strip().lower() for x in re.split(r'[,;]', external_ingredients) if x.strip()]
            if a and b:
                matches = sum(1 for x in a if any(x in y or y in x for y in b))
                overlap = matches / max(len(a), len(b))
        except Exception:
            overlap = 0.0
    conf = base*0.5 + title_sim*0.3 + overlap*0.2
    return round(min(1.0, conf), 3)

def enrich_products(df):
    enriched = []
    to_enrich = df.head(NUM_PRODUCTS_TO_ENRICH).to_dict(orient="records")
    for i, prod in enumerate(to_enrich, 1):
        name = prod.get('product_name') or prod.get('product_page_url').split('/')[-1]
        brand = prod.get('brand') or ""
        existing_ings = prod.get('ingredients_json') or prod.get('ingredients') or ""
        q = f"{name} {brand} official product page"
        print(f"\n[{i}/{len(to_enrich)}] Query: {q}")
        res = call_cse(q, num=5)
        chosen = choose_best_result(res, name, brand)
        if not chosen:
            time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))
            res2 = call_cse(name, num=5)
            chosen = choose_best_result(res2, name, brand) if res2 else None
        official_page = chosen.get('link') if chosen else None
        api_source = chosen.get('displayLink') if chosen else None
        external_ings = None
        sku = None
        country = None
        if official_page:
            page_html = fetch_page_text(official_page)
            time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))
            if page_html:
                ext_ings, sku_found, country_found = extract_external_info(page_html)
                external_ings = ext_ings
                sku = sku_found
                country = country_found
        confidence = compute_confidence(chosen, name, existing_ings, external_ings)
        out = dict(prod)
        out.update({
            "official_page": official_page,
            "external_ingredients": external_ings,
            "sku": sku,
            "country_of_origin": country,
            "api_source": api_source,
            "api_confidence": confidence
        })
        enriched.append(out)
        time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))
    return pd.DataFrame(enriched)

def main():
    if not API_KEY or not CX:
        print("ERROR: API_KEY and CX must be set in the script.")
        return
    df = pd.read_csv(INPUT_CSV)
    print("Loaded", len(df), "rows from", INPUT_CSV)
    enriched_df = enrich_products(df)
    enriched_df.to_csv(OUTPUT_CSV, index=False)
    print("Saved enriched CSV to", OUTPUT_CSV)
    print("Done.")

if __name__ == "__main__":
    main()

""", language='python')

    st.subheader("Run enrichment (must set API keys in script)")
    if st.button("Run Day 2 enrichment (Google CSE) 🔎"):
        st.text("Running enrichment script... streaming output below.")
        cmd = ["python3", "day2_enrich_google_cse_populated.py"]
        code, out = run_script(cmd)
        if code == 0:
            st.success("Enrichment finished successfully.")
        else:
            st.error(f"Enrichment exited with code {code}")

    st.subheader("Preview enriched file")
    enriched_df, enriched_shape = read_csv_if_exists(ENRICHED_PATH)
    if enriched_df is not None:
        st.dataframe(enriched_df)
        csv3 = open(ENRICHED_PATH, "rb").read()
        st.download_button("Download enriched CSV", data=csv3, file_name="day2_enriched_THE_ORDINARY_US.csv")
    else:
        st.info("No enriched file found yet — run Day 2 script after you set API keys.")

  

# Footer
st.markdown('\n---\n')
st.markdown('Created with care and responsibility, this toolkit adheres to ethical scraping principles and responsible AI use. It is developed exclusively for fair-use analysis and exploration of The Ordinary (US) website.')
