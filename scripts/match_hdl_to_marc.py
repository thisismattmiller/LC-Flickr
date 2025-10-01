#!/usr/bin/env python3
"""
Match MARC XML files to Flickr photos using HDL (Handle) URLs.
"""

import json
import os
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional

# Configuration
MARC_FILES_DIR = "../data/marc_files_from_search"
FLICKR_DATA_FILE = "../data/flickr_photos_with_metadata.json"
OUTPUT_FILE = "../data/marc_to_flickr_mapping.json"
NO_MATCH_OUTPUT_FILE = "../data/marc_to_flickr_mapping_no_match.json"

# XML namespace
MARC_NAMESPACE = {'marcxml': 'http://www.loc.gov/MARC21/slim'}

def extract_hdl_from_marc(xml_file_path: str) -> Optional[str]:
    """Extract HDL URL from MARC XML file."""
    try:
        tree = ET.parse(xml_file_path)
        root = tree.getroot()
        
        # Find datafield with tag="856"
        for datafield in root.findall('.//marcxml:datafield[@tag="856"]', MARC_NAMESPACE):
            # Find subfield with code="u"
            for subfield in datafield.findall('marcxml:subfield[@code="u"]', MARC_NAMESPACE):
                hdl_url = subfield.text
                if hdl_url and 'hdl.loc.gov' in hdl_url:
                    return hdl_url.strip()
        
        return None
        
    except ET.ParseError as e:
        print(f"  Error parsing XML file {xml_file_path}: {e}")
        return None
    except Exception as e:
        print(f"  Error processing file {xml_file_path}: {e}")
        return None

def extract_hdl_from_flickr_tags(photo: Dict) -> Optional[str]:
    """Extract HDL URL from Flickr photo tags."""
    try:
        tags = photo.get('metadata', {}).get('photo', {}).get('tags', {}).get('tag', [])
        
        for tag in tags:
            raw_value = tag.get('raw', '')
            # Check if it's a dc:identifier tag with HDL URL
            if raw_value.startswith('dc:identifier=http://hdl.loc.gov'):
                # Extract the URL part after 'dc:identifier='
                hdl_url = raw_value.replace('dc:identifier=', '')
                return hdl_url
            # Also check for direct HDL URLs in tags
            elif raw_value.startswith('http://hdl.loc.gov'):
                return raw_value
        
        return None
        
    except Exception as e:
        print(f"  Error extracting HDL from Flickr tags: {e}")
        return None

def main():
    # Dictionary to store HDL to records mapping
    hdl_mapping = {}
    
    # Check if MARC files directory exists
    if not os.path.exists(MARC_FILES_DIR):
        print(f"Error: MARC files directory not found: {MARC_FILES_DIR}")
        return
    
    # Process all XML files in MARC directory
    print("Processing MARC XML files...")
    xml_files = [f for f in os.listdir(MARC_FILES_DIR) if f.endswith('.xml')]
    print(f"Found {len(xml_files)} MARC XML files\n")
    
    marc_files_with_hdl = 0
    marc_files_without_hdl = 0
    
    for xml_file in xml_files:
        xml_path = os.path.join(MARC_FILES_DIR, xml_file)
        hdl_url = extract_hdl_from_marc(xml_path)
        
        if hdl_url:
            marc_files_with_hdl += 1
            if hdl_url not in hdl_mapping:
                hdl_mapping[hdl_url] = []
            # Store the XML filename
            hdl_mapping[hdl_url].append({'xml_file_name': xml_file})
            print(f"  ✓ {xml_file}: {hdl_url}")
        else:
            marc_files_without_hdl += 1
            print(f"  ✗ {xml_file}: No HDL URL found")
    
    print(f"\nMARC files with HDL: {marc_files_with_hdl}")
    print(f"MARC files without HDL: {marc_files_without_hdl}")
    print(f"Unique HDL URLs found: {len(hdl_mapping)}\n")
    
    # Load Flickr data
    print(f"Loading Flickr data from {FLICKR_DATA_FILE}")
    with open(FLICKR_DATA_FILE, 'r', encoding='utf-8') as f:
        flickr_data = json.load(f)
    
    print(f"Found {len(flickr_data)} Flickr photos\n")
    
    # Process Flickr photos and match with MARC records
    print("Matching Flickr photos to MARC records...")
    flickr_photos_with_hdl = 0
    flickr_photos_without_hdl = 0
    matches_found = 0
    no_match_hdls = {}  # Dictionary to store HDL URLs with no MARC match
    
    for photo in flickr_data:
        photo_id = photo.get('id', '')
        hdl_url = extract_hdl_from_flickr_tags(photo)
        
        if hdl_url:
            flickr_photos_with_hdl += 1
            
            # Check if we have a matching MARC record
            if hdl_url in hdl_mapping:
                matches_found += 1
                # Add Flickr ID to all matching MARC records
                for marc_record in hdl_mapping[hdl_url]:
                    if 'flickr_id' not in marc_record:
                        marc_record['flickr_id'] = photo_id
                    elif isinstance(marc_record.get('flickr_id'), str):
                        # Convert single ID to list if multiple matches
                        marc_record['flickr_id'] = [marc_record['flickr_id'], photo_id]
                    elif isinstance(marc_record.get('flickr_id'), list):
                        marc_record['flickr_id'].append(photo_id)
                
                print(f"  ✓ Matched Flickr {photo_id} to HDL {hdl_url}")
            else:
                # Store HDL URLs that have no matching MARC record
                if hdl_url not in no_match_hdls:
                    no_match_hdls[hdl_url] = []
                no_match_hdls[hdl_url].append(photo_id)
                print(f"  ! Flickr {photo_id} has HDL {hdl_url} but no matching MARC file")
        else:
            flickr_photos_without_hdl += 1
    
    print(f"\nFlickr photos with HDL: {flickr_photos_with_hdl}")
    print(f"Flickr photos without HDL: {flickr_photos_without_hdl}")
    print(f"Matches found: {matches_found}\n")
    
    # Prune the mapping to only include entries with matches
    print("Pruning mapping to include only matches...")
    final_mapping = {}
    pruned_count = 0
    
    for hdl_url, records in hdl_mapping.items():
        # Filter records to only include those with flickr_id
        matched_records = []
        for record in records:
            if 'flickr_id' in record and record['flickr_id']:
                # Ensure flickr_id is not empty
                if isinstance(record['flickr_id'], list) and len(record['flickr_id']) > 0:
                    matched_records.append(record)
                elif isinstance(record['flickr_id'], str) and record['flickr_id']:
                    matched_records.append(record)
        
        # Only add to final mapping if we have matched records
        if matched_records:
            final_mapping[hdl_url] = matched_records
        else:
            pruned_count += 1
    
    print(f"Pruned {pruned_count} HDL URLs with no matches")
    print(f"Final mapping contains {len(final_mapping)} HDL URLs with matches\n")
    
    # Save the mapping to JSON file
    print(f"Saving mapping to {OUTPUT_FILE}")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(final_mapping, f, indent=2, ensure_ascii=False)
    
    # Save the no-match HDL URLs to JSON file
    print(f"Saving no-match HDL URLs to {NO_MATCH_OUTPUT_FILE}")
    with open(NO_MATCH_OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(no_match_hdls, f, indent=2, ensure_ascii=False)
    
    # Print summary statistics
    print("\n" + "="*60)
    print("MATCHING COMPLETE")
    print("="*60)
    print(f"Total MARC files processed: {len(xml_files)}")
    print(f"MARC files with HDL URLs: {marc_files_with_hdl}")
    print(f"Total Flickr photos processed: {len(flickr_data)}")
    print(f"Flickr photos with HDL URLs: {flickr_photos_with_hdl}")
    print(f"Unique HDL URLs with matches: {len(final_mapping)}")
    
    # Count total matches
    total_marc_records_matched = sum(len(records) for records in final_mapping.values())
    print(f"Total MARC records matched: {total_marc_records_matched}")
    print(f"HDL URLs with no MARC match: {len(no_match_hdls)}")
    
    print(f"\nMapping saved to: {OUTPUT_FILE}")
    print(f"No-match HDL URLs saved to: {NO_MATCH_OUTPUT_FILE}")

if __name__ == "__main__":
    main()