#!/usr/bin/env python3

import json
import os
import time
import requests
from urllib.parse import urlparse

def is_shortened_url(url):
    """Check if URL is a shortened Google Maps URL"""
    if not url:
        return False
    
    shortened_patterns = [
        'goo.gl/maps/',
        'maps.app.goo.gl/'
    ]
    
    return any(pattern in url for pattern in shortened_patterns)

def get_redirect_url(url, timeout=10):
    """Get the redirect URL from headers without following the redirect"""
    try:
        # Make request with redirect disabled
        response = requests.head(url, allow_redirects=False, timeout=timeout)
        
        # Check if it's a redirect (3xx status code)
        if response.status_code in [301, 302, 303, 307, 308]:
            # Get the redirect URL from Location header
            redirect_url = response.headers.get('Location')
            if redirect_url:
                # Handle relative URLs (shouldn't happen with Google Maps, but just in case)
                if not redirect_url.startswith('http'):
                    parsed = urlparse(url)
                    redirect_url = f"{parsed.scheme}://{parsed.netloc}{redirect_url}"
                return redirect_url
        
        return None
        
    except requests.exceptions.RequestException as e:
        print(f"    Error getting redirect for {url}: {e}")
        return None

def save_data(data, output_file):
    """Save data to JSON file"""
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def expand_google_urls():
    """Expand shortened Google Maps URLs to their full versions"""
    
    # Input and output paths
    input_file = os.path.join('..', 'data', 'mapping_data.json')
    output_file = os.path.join('..', 'data', 'mapping_data.json')  # Same file for in-place update
    
    # Load the JSON data
    print(f"Loading data from {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"Loaded {len(data)} records")
    
    # Count statistics
    total_shortened = 0
    already_expanded = 0
    newly_expanded = 0
    failed_expansion = 0
    
    # Process each record
    for idx, record in enumerate(data, 1):
        google_maps_url = record.get('google_maps_url', '')
        
        # Check if this URL needs expansion
        if is_shortened_url(google_maps_url):
            total_shortened += 1
            
            # Check if already expanded
            if 'google_maps_url_expanded' in record and record['google_maps_url_expanded']:
                already_expanded += 1
                print(f"[{idx}/{len(data)}] Already expanded: {record.get('photo_id', 'unknown')}")
                continue
            
            # Try to expand the URL
            print(f"[{idx}/{len(data)}] Expanding URL for photo {record.get('photo_id', 'unknown')}:")
            print(f"    Original: {google_maps_url}")
            
            expanded_url = get_redirect_url(google_maps_url)
            
            if expanded_url:
                record['google_maps_url_expanded'] = expanded_url
                newly_expanded += 1
                print(f"    ✅ Expanded: {expanded_url[:100]}...")
            else:
                # Mark as attempted but failed (so we don't retry on resume)
                record['google_maps_url_expanded'] = None
                failed_expansion += 1
                print(f"    ❌ Failed to expand")
            
            # Save after each expansion for crash recovery
            save_data(data, output_file)
            print(f"    💾 Saved progress to {output_file}")
            
            # Wait 5 seconds between requests to be respectful
            if idx < len(data):  # Don't wait after the last item
                print(f"    ⏳ Waiting 5 seconds before next request...")
                time.sleep(5)
        
        elif 'google_maps_url_expanded' in record:
            # URL doesn't need expansion but has the field (cleanup)
            if record['google_maps_url_expanded'] == record['google_maps_url']:
                # Remove redundant field
                del record['google_maps_url_expanded']
    
    # Final save to ensure everything is written
    save_data(data, output_file)
    
    # Print summary statistics
    print("\n" + "=" * 60)
    print("📊 Summary:")
    print(f"  Total records: {len(data)}")
    print(f"  Shortened URLs found: {total_shortened}")
    print(f"  Already expanded (resumed): {already_expanded}")
    print(f"  Newly expanded: {newly_expanded}")
    print(f"  Failed to expand: {failed_expansion}")
    
    if newly_expanded > 0:
        print(f"\n✅ Successfully expanded {newly_expanded} URLs")
    
    if failed_expansion > 0:
        print(f"\n⚠️  Failed to expand {failed_expansion} URLs")
        print("These have been marked with null values and won't be retried on resume")
    
    print(f"\n💾 All changes saved to {output_file}")

if __name__ == "__main__":
    try:
        expand_google_urls()
    except KeyboardInterrupt:
        print("\n\n⚠️  Script interrupted by user")
        print("Progress has been saved. You can resume by running the script again.")
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        print("Progress has been saved. You can resume by running the script again.")