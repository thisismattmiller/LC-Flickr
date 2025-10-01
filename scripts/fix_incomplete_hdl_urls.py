#!/usr/bin/env python3

import json
import re
import os

def extract_hdl_from_description(description, collection_prefix):
    """
    Extract HDL URL from description field
    Looking for patterns like: 
    - hdl.loc.gov/loc.pnp/fsac.1a34853
    - hdl.loc.gov/loc.pnp/cph.3c12345
    - hdl.loc.gov/loc.pnp/pan.6a12345
    """
    if not description:
        return None
    
    # Pattern to match HDL URLs in description for the specific collection
    # Matches variations like:
    # hdl.loc.gov/loc.pnp/fsac.1a34853
    # hdl.loc.gov/loc.pnp/cph.3c12345
    # hdl.loc.gov/loc.pnp/pan.6a12345
    # http://hdl.loc.gov/loc.pnp/...
    # https://hdl.loc.gov/loc.pnp/...
    patterns = [
        rf'(https?://)?hdl\.loc\.gov/loc\.pnp/{re.escape(collection_prefix)}\.\w+',
        rf'hdl\.loc\.gov/loc\.pnp/{re.escape(collection_prefix)}\.\w+'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, description, re.IGNORECASE)
        if match:
            url = match.group(0)
            # Ensure it starts with http://
            if not url.startswith('http'):
                url = 'http://' + url
            return url
    
    return None

def fix_hdl_urls(input_file, output_file):
    """
    Fix incomplete HDL URLs by extracting complete URLs from description
    """
    print(f"Loading data from {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"Loaded {len(data)} records")
    
    fixed_count = 0
    already_complete = 0
    no_description_url = 0
    incomplete_urls = []
    
    # Define incomplete URL patterns to check
    incomplete_patterns = [
        ('/fsac.1', 'fsac'),
        ('/cph.3', 'cph'),
        ('/pan.6', 'pan')
    ]
    
    for record in data:
        hdl_url = record.get('hdl_url', '')
        description = record.get('description', '')
        photo_id = record.get('photo_id', 'unknown')
        
        # Check each incomplete pattern
        url_is_incomplete = False
        collection_to_fix = None
        
        for pattern, collection in incomplete_patterns:
            if hdl_url and pattern in hdl_url:
                # Check if it's actually incomplete (not followed by more characters)
                if not re.search(rf'{re.escape(pattern)}[a-zA-Z0-9]+', hdl_url):
                    url_is_incomplete = True
                    collection_to_fix = collection
                    break
                else:
                    # URL appears to be complete
                    already_complete += 1
                    break
        
        if url_is_incomplete and collection_to_fix:
            # This URL is incomplete
            print(f"\nFound incomplete URL for photo {photo_id}:")
            print(f"  Current HDL: {hdl_url}")
            
            # Try to extract complete URL from description
            complete_url = extract_hdl_from_description(description, collection_to_fix)
            
            if complete_url:
                print(f"  ✅ Found complete URL in description: {complete_url}")
                record['hdl_url'] = complete_url
                record['hdl_url_fixed'] = True  # Mark that we fixed this
                fixed_count += 1
            else:
                print(f"  ❌ Could not find complete URL in description")
                print(f"  Description preview: {description[:200]}...")
                incomplete_urls.append({
                    'photo_id': photo_id,
                    'current_hdl': hdl_url,
                    'description': description[:500]
                })
                no_description_url += 1
    
    # Save the updated data
    print(f"\n📝 Saving updated data to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    # Print summary
    print("\n" + "=" * 80)
    print("📊 FIX SUMMARY")
    print("=" * 80)
    print(f"Total records processed: {len(data)}")
    print(f"✅ Fixed incomplete URLs: {fixed_count}")
    print(f"✓  Already complete URLs: {already_complete}")
    print(f"❌ Could not fix (no URL in description): {no_description_url}")
    
    # Save report of unfixed URLs
    if incomplete_urls:
        report_file = input_file.replace('.json', '_incomplete_urls_report.json')
        print(f"\n📄 Saving report of unfixed URLs to {report_file}")
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(incomplete_urls, f, indent=2, ensure_ascii=False)
        
        print(f"\nExamples of unfixed URLs:")
        for item in incomplete_urls[:3]:  # Show first 3 examples
            print(f"  Photo ID: {item['photo_id']}")
            print(f"  Current HDL: {item['current_hdl']}")
            print(f"  Description: {item['description'][:150]}...")
            print()

def main():
    """Main function to fix incomplete HDL URLs"""
    
    # File paths
    input_file = os.path.join('..', 'data', 'mapping_data_with_locations.json')
    output_file = os.path.join('..', 'data', 'mapping_data_with_locations_fixed.json')
    
    # Check if input file exists
    if not os.path.exists(input_file):
        print(f"❌ Error: Input file {input_file} not found!")
        print("Make sure you're running this script from the scripts/ directory")
        return
    
    # Fix the URLs
    fix_hdl_urls(input_file, output_file)
    
    print(f"\n✨ Done! Fixed data saved to {output_file}")
    print("You can now use this file for further processing or rename it to replace the original.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Script interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()