#!/usr/bin/env python3

import json
import os
import re

def extract_hdl_url(description_text):
    """Extract HDL URL from description text"""
    if not description_text:
        return None
    
    # Look for specific hdl.loc.gov URLs (not the generic pp.print)
    # Pattern looks for URLs like http://hdl.loc.gov/loc.pnp/mrg.04827
    hdl_pattern = r'http://hdl\.loc\.gov/loc\.pnp/[a-zA-Z0-9]+\.[0-9]+'
    matches = re.findall(hdl_pattern, description_text)
    
    if matches:
        # Return the first specific HDL URL found (not pp.print)
        for url in matches:
            if 'pp.print' not in url:
                return url
    
    # Also check for other HDL patterns that might exist
    # Like ppmsc.08005 or other collection identifiers
    other_hdl_pattern = r'http://hdl\.loc\.gov/loc\.pnp/[a-zA-Z]+\.[0-9]+'
    other_matches = re.findall(other_hdl_pattern, description_text)
    
    if other_matches:
        for url in other_matches:
            if 'pp.print' not in url:
                return url
    
    return None

def extract_google_maps_urls(text):
    """Extract all Google Maps URLs from text"""
    if not text:
        return []
    
    # Patterns to match various Google Maps URL formats
    patterns = [
        r'https?://maps\.google\.com[^\s<>"{}|\\^`\[\]]+',
        r'https?://[a-z]+\.google\.com/maps[^\s<>"{}|\\^`\[\]]+',
        r'https?://goo\.gl/maps/[^\s<>"{}|\\^`\[\]]+',
        r'https?://maps\.app\.goo\.gl/[^\s<>"{}|\\^`\[\]]+',
    ]
    
    all_urls = []
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        all_urls.extend(matches)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_urls = []
    for url in all_urls:
        if url not in seen:
            seen.add(url)
            unique_urls.append(url)
    
    return unique_urls

def extract_lat_lng_from_url(url):
    """Extract latitude and longitude from Google Maps URL"""
    if not url:
        return None, None
    
    # Try to extract from different Google Maps URL formats
    
    # Format: @lat,lng,zoom
    at_pattern = r'@(-?\d+\.?\d*),(-?\d+\.?\d*)'
    matches = re.search(at_pattern, url)
    if matches:
        return float(matches.group(1)), float(matches.group(2))
    
    # Format: !3d<lat>!4d<lng>
    coord_pattern = r'!3d(-?\d+\.?\d*)!4d(-?\d+\.?\d*)'
    matches = re.search(coord_pattern, url)
    if matches:
        return float(matches.group(1)), float(matches.group(2))
    
    # Format: ll=lat,lng
    ll_pattern = r'll=(-?\d+\.?\d*),(-?\d+\.?\d*)'
    matches = re.search(ll_pattern, url)
    if matches:
        return float(matches.group(1)), float(matches.group(2))
    
    # Format: q=lat,lng
    q_pattern = r'q=(-?\d+\.?\d*),(-?\d+\.?\d*)'
    matches = re.search(q_pattern, url)
    if matches:
        return float(matches.group(1)), float(matches.group(2))
    
    # Format: place/.../@lat,lng
    place_pattern = r'place/[^/]+/@(-?\d+\.?\d*),(-?\d+\.?\d*)'
    matches = re.search(place_pattern, url)
    if matches:
        return float(matches.group(1)), float(matches.group(2))
    
    # Format for shortened URLs - we might need to check the destination
    # For now, return None if we can't extract coordinates
    return None, None

def clean_text(text):
    """Clean HTML tags from text"""
    if not text:
        return ""
    # Remove HTML tags
    clean = re.sub(r'<[^>]+>', '', text)
    # Replace HTML entities
    clean = clean.replace('&quot;', '"')
    clean = clean.replace('&amp;', '&')
    clean = clean.replace('&lt;', '<')
    clean = clean.replace('&gt;', '>')
    clean = clean.replace('\n', ' ')
    # Remove extra whitespace
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean

def extract_mapping_data():
    """Extract mapping data from Google Maps images"""
    
    # Input and output paths
    input_file = os.path.join('..', 'data', 'flickr_photos_with_google_maps.json')
    output_file = os.path.join('..', 'data', 'mapping_data.json')
    
    # Load the JSON data
    print(f"Loading data from {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Extract mapping data
    mapping_data = []
    no_coords_records = []  # Track records where we couldn't extract coordinates
    
    for record in data:
        try:
            # Extract photo ID
            photo_id = record.get('id', '')
            
            # Extract title
            title = ''
            if 'metadata' in record and 'photo' in record['metadata']:
                if 'title' in record['metadata']['photo']:
                    title = record['metadata']['photo']['title'].get('_content', '')
            if not title and 'title' in record:
                title = record.get('title', '')
            
            # Extract description and HDL URL
            description = ''
            hdl_url = None
            if 'metadata' in record and 'photo' in record['metadata']:
                if 'description' in record['metadata']['photo']:
                    description_raw = record['metadata']['photo']['description'].get('_content', '')
                    description = clean_text(description_raw)
                    hdl_url = extract_hdl_url(description_raw)
                
                # Also check tags for HDL URL (dc:identifier tag)
                if not hdl_url and 'tags' in record['metadata']['photo']:
                    if 'tag' in record['metadata']['photo']['tags']:
                        tags = record['metadata']['photo']['tags']['tag']
                        if not isinstance(tags, list):
                            tags = [tags]
                        for tag in tags:
                            if 'raw' in tag and 'dc:identifier=' in tag['raw']:
                                # Extract URL from dc:identifier tag
                                identifier_url = tag['raw'].replace('dc:identifier=', '')
                                if 'hdl.loc.gov' in identifier_url and 'pp.print' not in identifier_url:
                                    hdl_url = identifier_url
                                    break
            
            # Process comments to find all Google Maps URLs
            if 'comments' in record and record['comments']:
                if 'comments' in record['comments'] and 'comment' in record['comments']['comments']:
                    comments_list = record['comments']['comments']['comment']
                    
                    # Ensure it's a list
                    if not isinstance(comments_list, list):
                        comments_list = [comments_list]
                    
                    # Process all comments and extract all Google Maps URLs
                    for comment in comments_list:
                        comment_text = comment.get('_content', '')
                        google_maps_urls = extract_google_maps_urls(comment_text)
                        
                        # Process each Google Maps URL found in this comment
                        for google_maps_url in google_maps_urls:
                            # Extract coordinates (it's OK if we can't extract them)
                            lat, lng = extract_lat_lng_from_url(google_maps_url)
                            
                            # Create mapping record for each URL (successful even without coordinates)
                            mapping_record = {
                                'photo_id': photo_id,
                                'title': title,
                                'description': description,
                                'hdl_url': hdl_url,
                                'google_maps_url': google_maps_url,
                                'latitude': lat,
                                'longitude': lng,
                                'comment_text': clean_text(comment_text),
                                'comment_permalink': comment.get('permalink', ''),
                                'comment_author': comment.get('authorname', ''),
                                'comment_date': comment.get('datecreate', '')
                            }
                            
                            mapping_data.append(mapping_record)
                            
                            # Track records without coordinates for debugging (optional)
                            if lat is None or lng is None:
                                no_coords_records.append({
                                    'photo_id': photo_id,
                                    'title': title,
                                    'google_maps_url': google_maps_url,
                                    'all_comments': comments_list
                                })
        
        except Exception as e:
            print(f"Error processing record {record.get('id', 'unknown')}: {e}")
            continue
    
    # Save mapping data
    print(f"✅ Successfully extracted {len(mapping_data)} Google Maps URLs")
    print(f"Saving to {output_file}...")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(mapping_data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Successfully saved all {len(mapping_data)} records to {output_file}")
    
    # Print statistics
    coords_found = sum(1 for r in mapping_data if r['latitude'] is not None)
    no_coords_found = sum(1 for r in mapping_data if r['latitude'] is None)
    hdl_found = sum(1 for r in mapping_data if r['hdl_url'] is not None)
    unique_photos = len(set(r['photo_id'] for r in mapping_data))
    
    print(f"\n📊 Statistics:")
    print(f"  - Total Google Maps URLs extracted: {len(mapping_data)}")
    print(f"  - Unique photos with Maps URLs: {unique_photos}")
    print(f"  - URLs with coordinates: {coords_found}")
    print(f"  - URLs without coordinates (still valid): {no_coords_found}")
    print(f"  - Records with HDL URLs: {hdl_found}/{len(mapping_data)}")
    
    if mapping_data:
        print("\nSample records with coordinates:")
        sample_with_coords = [r for r in mapping_data if r['latitude'] is not None][:3]
        for record in sample_with_coords:
            print(f"\n  Photo: {record['title'][:50]}...")
            if record['hdl_url']:
                print(f"  HDL: {record['hdl_url']}")
            if record['latitude'] and record['longitude']:
                print(f"  Coords: {record['latitude']}, {record['longitude']}")
            print(f"  Maps URL: {record['google_maps_url'][:80]}...")
    
    # Print debugging info for records without coordinates (optional - these are still valid records)
    if no_coords_records:
        # Deduplicate by photo_id and google_maps_url
        unique_no_coords = {}
        for record in no_coords_records:
            key = (record['photo_id'], record['google_maps_url'])
            if key not in unique_no_coords:
                unique_no_coords[key] = record
        
        unique_no_coords_list = list(unique_no_coords.values())
        
        print(f"\n\n🔍 Debug Info: {len(unique_no_coords_list)} Google Maps URLs without extractable coordinates")
        print("(These records are still valid and have been saved successfully)")
        print("=" * 80)
        
        for idx, record in enumerate(unique_no_coords_list[:10], 1):  # Show first 10
            print(f"\n{idx}. Photo ID: {record['photo_id']}")
            print(f"   Title: {record['title'][:70]}...")
            print(f"   Google Maps URL: {record['google_maps_url']}")
            print(f"\n   ALL COMMENTS for this photo:")
            
            for comment_idx, comment in enumerate(record['all_comments'], 1):
                comment_text = comment.get('_content', '')
                author = comment.get('authorname', 'Unknown')
                print(f"\n   Comment {comment_idx} by {author}:")
                print(f"   {'-' * 40}")
                print(f"   {comment_text}")
                
                # Try to find any URLs in the comment
                all_urls = re.findall(r'https?://[^\s<>"{}|\\^`\[\]]+', comment_text)
                if all_urls:
                    print(f"\n   URLs found in this comment:")
                    for url in all_urls:
                        print(f"     - {url}")
            
            print("\n" + "=" * 80)
        
        if len(unique_no_coords_list) > 10:
            print(f"\n... and {len(unique_no_coords_list) - 10} more unique URLs without coordinates.")
        
        print("\n💡 Tip: Check these URLs for new patterns that need to be added to extract_lat_lng_from_url()")

if __name__ == "__main__":
    extract_mapping_data()