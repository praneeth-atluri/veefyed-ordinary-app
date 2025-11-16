# Veefyed — The Ordinary (US) Product Scraper & Enrichment Toolkit

**Live App:** https://veefyed-ordinary-app.streamlit.app/  
This project was built with a strong focus on transparency, ethical scraping practices, and responsible AI usage.

---

## 📘 1. Project Methodology & Documentation

This work was executed with clear ethical intent: respecting website terms of service, following robots.txt rules, and applying responsible AI principles throughout.

---

## 🟦 **Day 1 — Scraping, Structuring & Strategic Pivot**

### **Objective**
Scrape ~30 skincare product listings and generate a structured dataset.

### **Ethical Due Diligence**
Before scraping, the project reviewed the `robots.txt` files of multiple candidate sites including:

- Sephora  
- Nykaa  
- The Ordinary  
- Glossier  

Only sites permissible for crawling were considered, and no site was scraped against its stated rules.

### **Key Finding — The “Scraper Trap”**
Initial attempts to scrape several popular skincare websites failed due to **enterprise-grade bot detection**, even when robots.txt allowed crawling.

Observed blockers included:

- HTTP timeouts  
- Blank or obfuscated HTML responses  
- Invalid or incomplete JSON payloads  
- Selenium bypass failures  

To scrape those sites ethically without bypassing protections was not feasible.

### **Working Script**
The most robust attempt, `theordinary_us_scraper_final.py`, successfully parsed the product URLs from category pages but still faced blocking on specific  pages.

### **Strategic Pivot**
To maintain compliance, project integrity, and focus on data quality rather than bypassing detection systems, I generated what was feasable:

- Generate **day1_raw…csv** product URLs from category pages based scraper  
- Produce **day1_clean…csv**,  structured product data  

This enabled rigorous testing of:

- Size normalization (ml → ml/oz fields)  
- Ingredient list standardization into JSON arrays  
- Category & metadata extraction  

And ensured Day 2 (enrichment + validation) could be fully completed.

---

## 🟩 **Day 2 — API Enrichment & Validation**

### **Objective**
Enrich at least 10 products using the **Google Custom Search API**, retrieving authoritative product pages, additional ingredients, SKU/UPC data, and metadata.

### **Output**
The file **day2_enriched…csv** contains all enriched attributes.

### **Reliability & Validation — The “Trust Hierarchy”**
To ensure accuracy,a multi-factor scoring model incorporating domain trust weighting, Levenshtein-based title similarity, and semantic keyword signals framework was used:

#### **Tier 1 — Source of Truth**
- Official manufacturer website  
  - Example: `theordinary.com`
 

Data was accepted **only** if:

- It originated from a Tier 1 source, **and**  
- Passed title similarity checks & ingredient-list overlap validation  

This logic powers the `enriched_reliability_tier` and `api_confidence` fields in the final dataset.

---

## ⚙️ 2. How to Run This Project Locally

### **Clone the repository**
```bash
git clone https://github.com/praneeth-atluri/veefyed-ordinary-app.git
cd veefyed-ordinary-app
