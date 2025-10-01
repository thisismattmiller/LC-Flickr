#!/usr/bin/env python3
"""
Extract Wikipedia and Wikidata links from Flickr photo comments and notes.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Set, Optional
from urllib.parse import urlparse, unquote

def load_json(file_path: Path) -> dict:
    """Load JSON data from a file."""
    if not file_path.exists():
        print(f"Warning: {file_path} does not exist")
        return {}
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(data: dict, file_path: Path) -> None:
    """Save data to a JSON file."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def extract_hdl_url(tags: List[dict]) -> Optional[str]:
    """Extract HDL URL from tags."""
    for tag in tags:
        if tag.get('authorname') == 'The Library of Congress':
            raw = tag.get('raw', '')
            if raw.startswith('dc:identifier=http://hdl.loc.gov/'):
                return raw.replace('dc:identifier=', '')
    return None

def extract_wiki_links(text: str) -> List[str]:
    """
    Extract Wikipedia and Wikidata URLs from text.
    Handles various formats including HTML links and URLs with parentheses.
    """
    if not text:
        return []
    
    wiki_links = []
    
    # First, extract URLs from HTML anchor tags (most reliable for complex URLs)
    # Look for both single and double quotes
    href_patterns = [
        r'href="(https?://(?:[a-z]+\.wikipedia\.org|(?:www\.)?wikidata\.org)/[^"]+)"',
        r"href='(https?://(?:[a-z]+\.wikipedia\.org|(?:www\.)?wikidata\.org)/[^']+)'",
    ]
    
    for pattern in href_patterns:
        href_matches = re.findall(pattern, text, re.IGNORECASE)
        wiki_links.extend(href_matches)
    
    # Then look for standalone URLs (not in href attributes)
    # Remove href attributes first to avoid double-matching
    text_without_hrefs = text
    for pattern in href_patterns:
        text_without_hrefs = re.sub(pattern, '', text_without_hrefs, flags=re.IGNORECASE)
    
    # Pattern for standalone URLs - include apostrophes and other valid URL characters
    # Wikipedia URLs can contain: letters, numbers, parentheses, apostrophes, commas, hyphens, underscores, periods, colons, etc.
    standalone_patterns = [
        # Match Wikipedia/Wikidata URLs - use negative lookahead to stop at whitespace or HTML tags
        r'(https?://[a-z]+\.wikipedia\.org/wiki/[^\s<>"]+)',
        r'(https?://[a-z]+\.m\.wikipedia\.org/wiki/[^\s<>"]+)',
        r'(https?://(?:www\.)?wikidata\.org/[^\s<>"]+)',
        # Generic pattern for other Wikipedia pages (not /wiki/)
        r'(https?://[a-z]+\.wikipedia\.org/[^\s<>"]+)',
    ]
    
    for pattern in standalone_patterns:
        matches = re.findall(pattern, text_without_hrefs, re.IGNORECASE)
        wiki_links.extend(matches)
    
    # Clean up and validate URLs
    cleaned_links = []
    for url in wiki_links:
        # Remove any HTML entities
        url = url.replace('&amp;', '&')
        url = url.replace('&lt;', '<')
        url = url.replace('&gt;', '>')
        url = url.replace('&quot;', '"')
        
        # Handle URLs that might end with punctuation not part of the URL
        # But be careful with parentheses that ARE part of the URL
        # Wikipedia URLs can have parentheses in them, e.g., /wiki/Example_(disambiguation)
        
        # Count parentheses to see if they're balanced
        open_parens = url.count('(')
        close_parens = url.count(')')
        
        # If there are more closing parens, remove trailing ones
        while close_parens > open_parens and url.endswith(')'):
            url = url[:-1]
            close_parens -= 1
        
        # Remove other trailing punctuation that's definitely not part of URL
        url = re.sub(r'[.,;:!?]+$', '', url)
        
        # Remove trailing quotes or brackets if present
        url = url.rstrip('"\'>')
        
        # Validate it's a proper wiki URL
        if ('wikipedia.org' in url or 'wikidata.org' in url) and url.startswith('http'):
            cleaned_links.append(url)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_links = []
    for link in cleaned_links:
        if link not in seen:
            seen.add(link)
            unique_links.append(link)
    
    return unique_links

def process_photo(photo_data: dict) -> Optional[dict]:
    """
    Process a single photo to extract wiki links from comments and notes.
    Returns a dict with flickr_id, hdl_url, and wiki references, or None if no wiki links found.
    """
    flickr_id = photo_data.get('id')
    if not flickr_id:
        return None
    
    # Extract HDL URL
    metadata = photo_data.get('metadata', {}).get('photo', {})
    tags = metadata.get('tags', {}).get('tag', [])
    hdl_url = extract_hdl_url(tags)
    
    wiki_references = []
    
    # Process comments
    comments = photo_data.get('comments', {}).get('comments', {}).get('comment', [])
    for comment in comments:
        comment_text = comment.get('_content', '')
        wiki_links = extract_wiki_links(comment_text)
        
        if wiki_links:
            wiki_references.append({
                'type': 'comment',
                'author': comment.get('authorname', 'Unknown'),
                'author_id': comment.get('author', ''),
                'date': comment.get('datecreate', ''),
                'text': comment_text,
                'wiki_links': wiki_links
            })
    
    # Process notes
    notes = metadata.get('notes', {}).get('note', [])
    for note in notes:
        note_text = note.get('_content', '')
        wiki_links = extract_wiki_links(note_text)
        
        if wiki_links:
            wiki_references.append({
                'type': 'note',
                'author': note.get('authorname', 'Unknown'),
                'author_id': note.get('author', ''),
                'text': note_text,
                'wiki_links': wiki_links
            })
    
    # Only return if we found wiki references
    if wiki_references:
        return {
            'flickr_id': flickr_id,
            'hdl_url': hdl_url,
            'wiki_references': wiki_references
        }
    
    return None

def main():
    # Define paths
    base_dir = Path(__file__).parent.parent
    input_file = base_dir / 'data' / 'flickr_photos_with_metadata_comments.json'
    output_file = base_dir / 'data' / 'wiki_links.json'
    
    print("Loading Flickr photos data...")
    flickr_data = load_json(input_file)
    
    if not flickr_data:
        print("No Flickr data found!")
        return
    
    print(f"Processing {len(flickr_data)} photos to extract Wikipedia/Wikidata links...")
    
    # Process each photo
    results = []
    total_wiki_links = 0
    wiki_domains = set()
    
    for i, photo in enumerate(flickr_data, 1):
        if i % 1000 == 0:
            print(f"  Processed {i}/{len(flickr_data)} photos...")
        
        photo_result = process_photo(photo)
        if photo_result:
            results.append(photo_result)
            
            # Count links and track domains for statistics
            for ref in photo_result['wiki_references']:
                total_wiki_links += len(ref['wiki_links'])
                for link in ref['wiki_links']:
                    parsed = urlparse(link)
                    wiki_domains.add(parsed.netloc)
    
    # Save results
    print(f"\nSaving results to {output_file.name}...")
    save_json(results, output_file)
    
    # Print summary
    print("\n" + "="*60)
    print("WIKIPEDIA/WIKIDATA LINK EXTRACTION SUMMARY")
    print("="*60)
    print(f"Total photos processed: {len(flickr_data):,}")
    print(f"Photos with wiki links: {len(results):,}")
    print(f"Total wiki links found: {total_wiki_links:,}")
    
    if results:
        # Count by type
        comment_count = sum(1 for r in results for ref in r['wiki_references'] if ref['type'] == 'comment')
        note_count = sum(1 for r in results for ref in r['wiki_references'] if ref['type'] == 'note')
        
        print(f"\nReferences by type:")
        print(f"  Comments with wiki links: {comment_count}")
        print(f"  Notes with wiki links: {note_count}")
        
        print(f"\nWiki domains found:")
        for domain in sorted(wiki_domains):
            domain_count = sum(
                1 for r in results 
                for ref in r['wiki_references'] 
                for link in ref['wiki_links'] 
                if urlparse(link).netloc == domain
            )
            print(f"  {domain}: {domain_count} links")
        
        # Show sample
        print(f"\nSample entry:")
        sample = results[0]
        print(f"  Flickr ID: {sample['flickr_id']}")
        print(f"  HDL URL: {sample.get('hdl_url', 'None')}")
        print(f"  Wiki references: {len(sample['wiki_references'])}")
        if sample['wiki_references']:
            ref = sample['wiki_references'][0]
            print(f"    Type: {ref['type']}")
            print(f"    Author: {ref['author']}")
            print(f"    Wiki links: {ref['wiki_links'][:2]}")  # Show first 2 links
    
    print(f"\nResults saved to: {output_file}")
    print("="*60)

if __name__ == "__main__":
    main()