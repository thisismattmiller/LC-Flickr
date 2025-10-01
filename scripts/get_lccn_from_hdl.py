#!/usr/bin/env python3
"""
Get LCCN numbers from HDL URLs using ChromeDriver to fetch and parse the HTML pages.
Supports resuming from where it left off if interrupted.
"""

import json
import os
import re
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from typing import Dict, Optional

# Configuration
CHROMEDRIVER_PATH = "/Users/m/Downloads/chromedriver-mac-arm64/chromedriver"
NO_MATCH_FILE = "../data/marc_to_flickr_mapping_no_match.json"
OUTPUT_FILE = "../data/hdl_to_lccn.json"
CHECKPOINT_FILE = "../data/.hdl_to_lccn_checkpoint.json"

# Request settings
PAGE_LOAD_TIMEOUT = 30
RETRY_ATTEMPTS = 3
DELAY_BETWEEN_REQUESTS = 1  # seconds

def load_checkpoint() -> Dict:
    """Load checkpoint data if it exists."""
    if os.path.exists(CHECKPOINT_FILE):
        try:
            with open(CHECKPOINT_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load checkpoint: {e}")
    return {}

def save_checkpoint(checkpoint_data: Dict):
    """Save checkpoint data."""
    try:
        with open(CHECKPOINT_FILE, 'w', encoding='utf-8') as f:
            json.dump(checkpoint_data, f, indent=2)
    except Exception as e:
        print(f"Warning: Could not save checkpoint: {e}")

def load_existing_results() -> Dict:
    """Load existing results if the output file exists."""
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load existing results: {e}")
    return {}

def save_results(results: Dict):
    """Save results to output file."""
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

def extract_data_from_page(driver) -> Dict:
    """Extract LCCN and meta tags from the loaded page using Selenium."""
    result = {
        "lccn": None,
        "meta_tags": {}
    }
    
    try:
        # Wait for page to load and look for the "About This Item" link
        wait = WebDriverWait(driver, 10)
        
        # Extract LCCN
        try:
            about_link = driver.find_element(By.LINK_TEXT, "About This Item")
            href = about_link.get_attribute('href')
            if href:
                # Extract LCCN from the URL
                match = re.search(r'/pictures/item/(\d+)/', href)
                if match:
                    result["lccn"] = match.group(1)
        except:
            pass
        
        # Alternative: Find all links to /pictures/item/ if LCCN not found
        if not result["lccn"]:
            links = driver.find_elements(By.XPATH, "//a[contains(@href, '/pictures/item/')]")
            for link in links:
                href = link.get_attribute('href')
                if href:
                    match = re.search(r'/pictures/item/(\d+)/', href)
                    if match:
                        result["lccn"] = match.group(1)
                        break
        
        # Extract all meta tags - store everything as lists for consistency
        meta_tags = driver.find_elements(By.TAG_NAME, "meta")
        for meta in meta_tags:
            name = meta.get_attribute('name')
            content = meta.get_attribute('content')
            
            if name and content:
                # Always use lists to handle repeated meta tags
                if name in result["meta_tags"]:
                    result["meta_tags"][name].append(content)
                else:
                    result["meta_tags"][name] = [content]
            
            # Also check for http-equiv meta tags
            http_equiv = meta.get_attribute('http-equiv')
            if http_equiv and content:
                key = f"http-equiv.{http_equiv}"
                if key in result["meta_tags"]:
                    result["meta_tags"][key].append(content)
                else:
                    result["meta_tags"][key] = [content]
            
            # Check for id attribute (like prop45)
            meta_id = meta.get_attribute('id')
            if meta_id and content:
                key = f"id.{meta_id}"
                if key in result["meta_tags"]:
                    result["meta_tags"][key].append(content)
                else:
                    result["meta_tags"][key] = [content]
        
        # Extract link tags with rel attributes (for canonical, alternate, etc.)
        link_tags = driver.find_elements(By.TAG_NAME, "link")
        for link in link_tags:
            rel = link.get_attribute('rel')
            href = link.get_attribute('href')
            title = link.get_attribute('title')
            
            if rel and href:
                link_info = {"href": href}
                if title:
                    link_info["title"] = title
                
                key = f"link.{rel}"
                # Always use lists for consistency
                if key in result["meta_tags"]:
                    result["meta_tags"][key].append(link_info)
                else:
                    result["meta_tags"][key] = [link_info]
        
        return result
    except Exception as e:
        print(f"    Error extracting data: {e}")
        return result

def fetch_hdl_page(driver, hdl_url: str, retry_count: int = 0) -> Dict:
    """Fetch page using ChromeDriver and extract LCCN and metadata."""
    try:
        driver.get(hdl_url)
        time.sleep(2)
        
        
        # Extract LCCN and metadata
        data = extract_data_from_page(driver)
        return data
        
    except Exception as e:
        if retry_count < RETRY_ATTEMPTS - 1:
            print(f"    Retry {retry_count + 1}/{RETRY_ATTEMPTS - 1} after error: {e}")
            time.sleep(DELAY_BETWEEN_REQUESTS * 2)  # Longer delay for retry
            return fetch_hdl_page(driver, hdl_url, retry_count + 1)
        else:
            print(f"    Failed after {RETRY_ATTEMPTS} attempts: {e}")
            return {"lccn": None, "meta_tags": {}}

def main():
    # Load the no-match HDL URLs
    print(f"Loading HDL URLs from {NO_MATCH_FILE}")
    if not os.path.exists(NO_MATCH_FILE):
        print(f"Error: File not found: {NO_MATCH_FILE}")
        return
    
    with open(NO_MATCH_FILE, 'r', encoding='utf-8') as f:
        hdl_data = json.load(f)
    
    total_hdls = len(hdl_data)
    print(f"Found {total_hdls} HDL URLs to process\n")
    
    # Load checkpoint and existing results
    checkpoint = load_checkpoint()
    results = load_existing_results()
    
    # Determine starting point
    processed_count = len(results)
    if processed_count > 0:
        print(f"Resuming from previous run: {processed_count} HDL URLs already processed")
    
    # Configure Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # Set up the Chrome service
    service = Service(CHROMEDRIVER_PATH)
    
    # Statistics
    success_count = 0
    failure_count = 0
    skip_count = 0
    retry_count = 0
    
    driver = None
    try:
        # Initialize the Chrome driver
        print(f"Initializing Chrome driver...")
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
        print("Chrome driver initialized successfully\n")

        driver.get('https://loc.gov/pictures/resource/ggbain.09681/')
        time.sleep(10)
        
        for idx, (hdl_url, flickr_ids) in enumerate(hdl_data.items(), 1):
            # Check if already processed
            is_retry = False
            if hdl_url in results:
                # Check if it was a failed attempt (no LCCN found)
                existing_result = results[hdl_url]
                if existing_result.get("lccn") is None and existing_result.get("error") == "LCCN not found on page":
                    print(f"[{idx}/{total_hdls}] Retrying previously failed: {hdl_url}")
                    is_retry = True
                    retry_count += 1
                    # Continue processing to retry
                else:
                    print(f"[{idx}/{total_hdls}] Skipping (already processed successfully): {hdl_url}")
                    skip_count += 1
                    continue
            else:
                print(f"[{idx}/{total_hdls}] Processing: {hdl_url}")
            
            # Fetch the page and extract data
            page_data = fetch_hdl_page(driver, hdl_url)
            
            if page_data and page_data.get("lccn"):
                # Check if this was a retry that succeeded
                if is_retry:
                    print(f"    ✓ RETRY SUCCESS! Found LCCN: {page_data['lccn']}")
                else:
                    print(f"    ✓ Found LCCN: {page_data['lccn']}")
                
                results[hdl_url] = {
                    "lccn": page_data["lccn"],
                    "flickr_ids": flickr_ids,
                    "meta_tags": page_data.get("meta_tags", {})
                }
                success_count += 1
                
                # Print some key metadata if available
                if page_data.get("meta_tags"):
                    if "dc.title" in page_data["meta_tags"]:
                        # Handle list format - get first item if it's a list
                        title = page_data['meta_tags']['dc.title']
                        if isinstance(title, list) and title:
                            title = title[0]
                        print(f"      Title: {title}")
            else:
                results[hdl_url] = {
                    "lccn": None,
                    "flickr_ids": flickr_ids,
                    "meta_tags": page_data.get("meta_tags", {}) if page_data else {},
                    "error": "LCCN not found on page"
                }
                if not is_retry:
                    failure_count += 1
                print(f"    ✗ LCCN not found on page")
            
            # Save results after each successful fetch (for resume capability)
            save_results(results)
            
            # Save checkpoint
            checkpoint['last_processed'] = hdl_url
            checkpoint['processed_count'] = len(results)
            save_checkpoint(checkpoint)
            
            # Delay between requests to be respectful
            if idx < total_hdls:
                time.sleep(DELAY_BETWEEN_REQUESTS)
    
    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Progress has been saved.")
        print(f"Processed {len(results)} out of {total_hdls} HDL URLs")
        print("Run the script again to resume from where you left off.")
    
    except Exception as e:
        print(f"\n\nError occurred: {e}")
        print(f"Progress has been saved. Processed {len(results)} out of {total_hdls} HDL URLs")
        print("Run the script again to resume from where you left off.")
    
    finally:
        # Clean up - close the browser
        if driver:
            print("\nClosing browser...")
            driver.quit()
    
    # Clean up checkpoint file on successful completion
    if len(results) == total_hdls and os.path.exists(CHECKPOINT_FILE):
        try:
            os.remove(CHECKPOINT_FILE)
            print("Checkpoint file removed (processing complete)")
        except:
            pass
    
    # Print summary
    print("\n" + "="*60)
    print("PROCESSING COMPLETE")
    print("="*60)
    print(f"Total HDL URLs processed: {len(results)}")
    print(f"Successfully extracted LCCN: {success_count}")
    print(f"Failed to extract LCCN: {failure_count}")
    print(f"Skipped (already processed): {skip_count}")
    print(f"Retried (previously failed): {retry_count}")
    print(f"\nResults saved to: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()