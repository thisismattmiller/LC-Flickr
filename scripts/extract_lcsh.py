#!/usr/bin/env python3
"""
Extract Library of Congress Subject Headings (LCSH) from MARC XML files
and map them to Flickr IDs.
"""

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Any

# MARC21 namespace
MARC_NS = {'marc': 'http://www.loc.gov/MARC21/slim'}

def load_json(file_path: Path) -> dict:
    """Load JSON data from a file."""
    if not file_path.exists():
        print(f"Warning: {file_path} does not exist")
        return {}
    with open(file_path, 'r') as f:
        return json.load(f)

def save_json(data: dict, file_path: Path) -> None:
    """Save data to a JSON file."""
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)

def build_flickr_to_xml_map(marc_to_flickr_data: dict) -> Dict[str, str]:
    """
    Build a mapping from flickr_id to xml_file_name.
    
    Input format:
    {
      "http://hdl.loc.gov/...": [
        {
          "xml_file_name": "20299833.xml",
          "flickr_id": "2786278717"  # Can be a string or list of strings
        }
      ]
    }
    
    Output format:
    {
      "2786278717": "20299833.xml",
      ...
    }
    """
    flickr_to_xml = {}
    
    for hdl_url, entries in marc_to_flickr_data.items():
        if isinstance(entries, list):
            for entry in entries:
                if isinstance(entry, dict):
                    flickr_id = entry.get('flickr_id')
                    xml_file = entry.get('xml_file_name')
                    
                    if flickr_id and xml_file:
                        # Handle both single string and list of strings
                        if isinstance(flickr_id, str):
                            flickr_to_xml[flickr_id] = xml_file
                        elif isinstance(flickr_id, list):
                            # Map each flickr_id in the list to the same xml_file
                            for fid in flickr_id:
                                if isinstance(fid, str):
                                    flickr_to_xml[fid] = xml_file
    
    return flickr_to_xml

def extract_marc_fields(xml_file_path: Path) -> Dict[str, Any]:
    """
    Extract 650 fields (subjects) and 787 subfield t (collection) from a MARC XML file.
    
    Returns a dict with:
    - 'subjects': list of 650 fields, where each field is a list of subfield dicts
    - 'collection': the 787 subfield t value if it exists, None otherwise
    """
    if not xml_file_path.exists():
        return {'subjects': [], 'collection': None}
    
    try:
        tree = ET.parse(xml_file_path)
        root = tree.getroot()
        
        # Extract 650 fields (subjects)
        target_subfields = {'a', 'b', 'c', 'd', 'e', 'g', 'v', 'x', 'y', 'z'}
        all_650_fields = []
        
        for datafield in root.findall('.//marc:datafield[@tag="650"]', MARC_NS):
            field_subfields = []
            
            # Extract relevant subfields in order
            for subfield in datafield.findall('marc:subfield', MARC_NS):
                code = subfield.get('code')
                if code in target_subfields:
                    text = subfield.text
                    if text:  # Only add if there's actual text
                        field_subfields.append({code: text.strip()})
            
            if field_subfields:  # Only add if we found relevant subfields
                all_650_fields.append(field_subfields)
        
        # Extract 787 subfield t (collection name)
        collection = None
        for datafield in root.findall('.//marc:datafield[@tag="787"]', MARC_NS):
            for subfield in datafield.findall('marc:subfield[@code="t"]', MARC_NS):
                if subfield.text:
                    collection = subfield.text.strip()
                    break  # Take the first one if multiple exist
            if collection:
                break
        
        return {'subjects': all_650_fields, 'collection': collection}
        
    except ET.ParseError as e:
        print(f"  Error parsing XML file {xml_file_path}: {e}")
        return {'subjects': [], 'collection': None}
    except Exception as e:
        print(f"  Unexpected error processing {xml_file_path}: {e}")
        return {'subjects': [], 'collection': None}

def main():
    # Define paths
    base_dir = Path(__file__).parent.parent
    mapping_file = base_dir / 'data' / 'marc_to_flickr_mapping.json'
    marc_dir = base_dir / 'data' / 'marc_files_from_search'
    output_file = base_dir / 'data' / 'subject_to_flickr_id_mapping.json'
    
    print("Loading marc_to_flickr_mapping.json...")
    marc_to_flickr_data = load_json(mapping_file)
    
    if not marc_to_flickr_data:
        print("No data found in marc_to_flickr_mapping.json")
        return
    
    # Build flickr_id to xml_file_name mapping
    print("Building Flickr ID to XML file mapping...")
    flickr_to_xml = build_flickr_to_xml_map(marc_to_flickr_data)
    print(f"Found {len(flickr_to_xml)} Flickr ID to XML file mappings")
    
    # Process each XML file and extract subjects and collection
    print(f"\nProcessing {len(flickr_to_xml)} MARC XML files...")
    
    flickr_subject_mapping = {}
    processed = 0
    missing_files = 0
    
    for flickr_id, xml_filename in flickr_to_xml.items():
        xml_path = marc_dir / xml_filename
        
        if not xml_path.exists():
            print(f"  Warning: XML file not found: {xml_filename}")
            missing_files += 1
            continue
        
        # Extract 650 fields and 787 subfield t
        marc_data = extract_marc_fields(xml_path)
        
        # Build the entry for this flickr_id
        entry = {}
        
        # Add subjects if they exist
        if marc_data['subjects']:
            entry['subject'] = marc_data['subjects']
        
        # Add collection if it exists
        if marc_data['collection']:
            entry['collection'] = marc_data['collection']
        
        # Only add to mapping if we have some data
        if entry:
            flickr_subject_mapping[flickr_id] = entry
            processed += 1
            
            # Show progress every 100 files
            if processed % 100 == 0:
                print(f"  Processed {processed} files...")
    
    # Save the results
    print(f"\nSaving results to {output_file.name}...")
    save_json(flickr_subject_mapping, output_file)
    
    # Print summary
    print(f"\n=== Summary ===")
    print(f"Total Flickr IDs in mapping: {len(flickr_to_xml)}")
    print(f"XML files processed: {processed}")
    print(f"XML files not found: {missing_files}")
    print(f"Flickr IDs with subjects: {len(flickr_subject_mapping)}")
    
    # Show a sample of the output
    if flickr_subject_mapping:
        sample_id = next(iter(flickr_subject_mapping))
        sample_data = flickr_subject_mapping[sample_id]
        print(f"\nSample output for Flickr ID {sample_id}:")
        print(json.dumps({sample_id: sample_data}, indent=2)[:500] + "...")
    
    print(f"\nResults saved to: {output_file}")

if __name__ == "__main__":
    main()