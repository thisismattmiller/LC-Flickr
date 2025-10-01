#!/usr/bin/env python3

import json
import os
import re

def has_google_maps_url(text):
    """Check if text contains a Google Maps URL"""
    if not text:
        return False
    
    # Pattern to match various Google Maps URL formats
    patterns = [
        r'maps\.google\.com',
        r'google\.com/maps',
        r'goo\.gl/maps',
        r'maps\.app\.goo\.gl'
    ]
    
    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False

def extract_records_with_google_maps():
    """Extract records that have Google Maps URLs in comments"""
    
    # Input and output paths
    input_file = os.path.join('..', 'data', 'flickr_photos_with_metadata_comments.json')
    output_dir = os.path.join('..', 'data')
    output_file = os.path.join(output_dir, 'flickr_photos_with_google_maps.json')
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Load the JSON data
    print(f"Loading data from {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Filter records with Google Maps URLs
    filtered_records = []
    
    for record in data:
        # Check if record has comments
        if 'comments' in record and record['comments']:
            # Navigate to the actual comments array
            if 'comments' in record['comments'] and 'comment' in record['comments']['comments']:
                comments_list = record['comments']['comments']['comment']
                
                # Ensure it's a list
                if not isinstance(comments_list, list):
                    comments_list = [comments_list]
                
                # Check each comment for Google Maps URLs
                has_maps_url = False
                for comment in comments_list:
                    # Check _content field
                    if '_content' in comment and has_google_maps_url(comment['_content']):
                        has_maps_url = True
                        break
                
                if has_maps_url:
                    filtered_records.append(record)
    
    # Save filtered records
    print(f"Found {len(filtered_records)} records with Google Maps URLs")
    print(f"Saving to {output_file}...")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(filtered_records, f, indent=2, ensure_ascii=False)
    
    print(f"Successfully saved {len(filtered_records)} records to {output_file}")
    
    # Print some statistics
    if filtered_records:
        print("\nSample of found URLs:")
        sample_count = 0
        for record in filtered_records[:5]:  # Show first 5 examples
            if 'comments' in record and 'comments' in record['comments'] and 'comment' in record['comments']['comments']:
                comments_list = record['comments']['comments']['comment']
                if not isinstance(comments_list, list):
                    comments_list = [comments_list]
                
                for comment in comments_list:
                    comment_text = comment.get('_content', '')
                    if has_google_maps_url(comment_text):
                        # Extract the URL
                        urls = re.findall(r'https?://[^\s<>"{}|\\^`\[\]]+', comment_text)
                        for url in urls:
                            if has_google_maps_url(url):
                                sample_count += 1
                                photo_id = record.get('id', 'unknown')
                                print(f"  Photo {photo_id}: {url[:100]}...")
                                break
                        if sample_count >= 5:
                            break
                if sample_count >= 5:
                    break

if __name__ == "__main__":
    extract_records_with_google_maps()