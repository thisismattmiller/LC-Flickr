#!/usr/bin/env python3
"""
Selenium script to search Library of Congress catalog for call numbers from Flickr metadata.
"""

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import json
import os
import re

# Configuration
CHROMEDRIVER_PATH = "/Users/m/Downloads/chromedriver-mac-arm64/chromedriver"
LOC_CATALOG_URL = "https://www.loc.gov/catalog/"
FLICKR_DATA_FILE = "../data/flickr_photos_with_metadata.json"
OUTPUT_DIR = "../data/lc_catalog_scrape"

def extract_call_number(description):
    """Extract call number from description text."""
    if not description:
        return None
    
    # Look for pattern: <b>Call Number:</b> followed by the call number
    match = re.search(r'<b>Call Number:</b>\s*([^<\n]+)', description)
    if match:
        call_number = match.group(1).strip()
        return call_number
    return None

def search_and_save(driver, photo_id, call_number):
    """Search for call number and save HTML if MARC record found."""
    try:
        # Navigate to catalog page
        print(f"  Navigating to catalog...")
        driver.get(LOC_CATALOG_URL)
        time.sleep(1)
        
        # Find and fill search box
        wait = WebDriverWait(driver, 10)
        search_box = wait.until(EC.presence_of_element_located((By.ID, "quick-search")))
        
        print(f"  Searching for: {call_number}")
        search_box.clear()
        search_box.send_keys(call_number)
        search_box.send_keys(Keys.RETURN)
        
        # Wait for results to load
        time.sleep(2.5)
        
        # Check if there's a MARC record link
        try:
            # Look for li elements containing "MARC record"
            marc_elements = driver.find_elements(By.XPATH, "//li[contains(., 'MARC record')]")
            
            if marc_elements:
                print(f"  ✓ Found MARC record!")
                
                # Save the HTML
                page_html = driver.page_source
                output_file = os.path.join(OUTPUT_DIR, f"{photo_id}.json")
                
                data = {
                    "photo_id": photo_id,
                    "call_number": call_number,
                    "url": driver.current_url,
                    "html": page_html
                }
                
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                
                print(f"  ✓ Saved to {output_file}")
                return True
            else:
                print(f"  ✗ No MARC record found")
                return False
                
        except Exception as e:
            print(f"  ✗ Error checking for MARC record: {e}")
            return False
            
    except Exception as e:
        print(f"  ✗ Error during search: {e}")
        return False

def main():
    # Create output directory if it doesn't exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Load Flickr data
    print(f"Loading Flickr data from {FLICKR_DATA_FILE}")
    with open(FLICKR_DATA_FILE, 'r', encoding='utf-8') as f:
        flickr_data = json.load(f)
    
    print(f"Found {len(flickr_data)} photos\n")
    
    # Configure Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # Set up the Chrome service
    service = Service(CHROMEDRIVER_PATH)
    
    # Track statistics
    total_processed = 0
    found_marc = 0
    no_call_number = 0
    no_marc = 0
    
    try:
        # Initialize the Chrome driver
        print(f"Initializing Chrome driver...\n")
        driver = webdriver.Chrome(service=service, options=chrome_options)
        

        print(f"  Navigating to catalog...")
        driver.get(LOC_CATALOG_URL)
        time.sleep(10)
        


        # Process each photo
        for i, photo in enumerate(flickr_data, 1):
            photo_id = photo.get('id', '')
            print(f"[{i}/{len(flickr_data)}] Processing photo {photo_id}")
            
            # Check if already processed
            output_file = os.path.join(OUTPUT_DIR, f"{photo_id}.json")
            if os.path.exists(output_file):
                print(f"  ⏭ Already processed, skipping")
                continue
            
            # Extract call number from description
            try:
                description = photo.get('metadata', {}).get('photo', {}).get('description', {}).get('_content', '')
                call_number = extract_call_number(description)
                
                if not call_number:
                    print(f"  ✗ No call number found in description")
                    no_call_number += 1
                    continue
                
                # Search and save
                if search_and_save(driver, photo_id, call_number):
                    found_marc += 1
                else:
                    no_marc += 1
                
                total_processed += 1
                
                # Small delay between searches to be polite
                time.sleep(1)
                
            except Exception as e:
                print(f"  ✗ Error processing photo: {e}")
                continue
        
        # Print summary
        print("\n" + "="*60)
        print("SCRAPING COMPLETE")
        print("="*60)
        print(f"Total photos: {len(flickr_data)}")
        print(f"Processed: {total_processed}")
        print(f"Found MARC records: {found_marc}")
        print(f"No call number: {no_call_number}")
        print(f"No MARC record: {no_marc}")
        print(f"\nResults saved to: {OUTPUT_DIR}")
        
    except Exception as e:
        print(f"Fatal error: {e}")
    
    finally:
        # Clean up - close the browser
        if 'driver' in locals():
            print("\nClosing browser...")
            driver.quit()

if __name__ == "__main__":
    main()