Live App URL: https://veefyed-ordinary-app.streamlit.app/

1. Project Methodology & Documentation

This project was executed in line with ethical values of transparency and fair AI usage.

Day 1: Scraping, Structuring, & Strategic Pivot

Objective: Scrape 30 products from a skincare website.

Ethical Due Diligence: As a first step, the robots.txt files for multiple target sites (e.g., Sephora, Nykaa, The Ordinary, Glossier) were checked to ensure ethical compliance.

Key Finding (The "Scraper Trap"):

Initial attempts on multiple sites (sephora, BYOMA, Glossier) using standard requests, Selenium, and advanced JSON-parsing methods were all defeated by enterprise-grade bot detection.

This was conclusively proven by analyzing error logs, which showed timeout failures, blank HTML responses, and malformed JSON payloads, even when robots.txt was permissive.

The script theordinary_us_scraper_final.py is the final, most robust version, which successfully parses the sitemap but still faces server-side blocking on individual product pages.

Strategic Pivot:

I made the decision to de-risk the project and go with theordinary.com. Rather than trying to bypass a non-trivial engineering challenge, I used the final script to generate the raw day1_raw...csv.

From this, I created the day1_clean...csv file. This simulated dataset proves the data cleaning and standardization logic (e.g., atomizing size into size_ml/oz, standardizing ingredients to a JSON array) and allowed me to focus on the (more important) Day 2 enrichment and validation tasks.

Day 2: API Enrichment & Validation

Objective: Enrich 10+ products using the Google Custom Search API.

Execution: The day2_enriched...csv file is the output of this process.

Reliability & Validation Logic (The "Trust Hierarchy"):

To ensure enriched data was reliable, I established a "Trust Hierarchy" to validate API search results:

Tier 1 (Source of Truth): The official brand website (e.g., theordinary.com).

Tier 2 (High Trust): Major licensed retailers (e.g., sephora.com, ulta.com).

Data (like the official manufacturer's page) was only accepted if it came from a Tier 1 or Tier 2 source. This logic is reflected in the enriched_reliability_tier column of the final dataset.

2. How to Run This Project

Clone the repository:

git clone [https://github.com/praneeth-atluri/veefyed-ordinary-app.git](https://github.com/praneeth-atluri/veefyed-ordinary-app.git)
cd veefyed-ordinary-app


Install the required libraries:

pip install -r requirements.txt


Run the Streamlit application:

streamlit run app.py


The app will open in your local browser.
