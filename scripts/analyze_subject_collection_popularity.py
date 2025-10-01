#!/usr/bin/env python3
"""
Analyze Flickr photo interactions (comments, tags, notes) by subject and collection.
Generate report and visualization data.
"""

import json
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict
import re

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

def is_loc_affiliated(username: str, realname: str = "") -> bool:
    """Check if a user is affiliated with Library of Congress."""
    username_lower = username.lower() if username else ""
    realname_lower = realname.lower() if realname else ""
    
    return (
        "library of congress" in username_lower or
        "libraryofcongress" in username_lower or
        "loc" in username_lower or
        "library of congress" in realname_lower or
        "loc" in realname_lower
    )

def extract_hdl_and_collection(tags: List[dict]) -> Tuple[str, str]:
    """
    Extract HDL URL and collection code from tags.
    Returns (hdl_url, collection_code)
    """
    hdl_url = None
    collection_code = None
    
    for tag in tags:
        # Look for dc:identifier tags from Library of Congress
        if tag.get('authorname') == 'The Library of Congress':
            raw = tag.get('raw', '')
            if raw.startswith('dc:identifier=http://hdl.loc.gov/'):
                hdl_url = raw.replace('dc:identifier=', '')
                # Extract collection code from URL
                # Format: http://hdl.loc.gov/loc.pnp/fsac.1a35296
                parts = hdl_url.split('/')
                if len(parts) > 4:
                    collection_part = parts[4]  # e.g., "fsac.1a35296"
                    collection_code = collection_part.split('.')[0]
                break
    
    return hdl_url, collection_code

def count_user_interactions(photo_data: dict) -> Dict[str, int]:
    """
    Count user-generated tags, notes, and comments (excluding LOC-affiliated users).
    Returns dict with counts for each interaction type.
    """
    counts = {
        'tags': 0,
        'notes': 0,
        'comments': 0,
        'total': 0
    }
    
    # Count tags (excluding LOC)
    metadata = photo_data.get('metadata', {}).get('photo', {})
    tags = metadata.get('tags', {}).get('tag', [])
    for tag in tags:
        author_name = tag.get('authorname', '')
        if not is_loc_affiliated(author_name):
            counts['tags'] += 1
    
    # Count notes (excluding LOC)
    notes = metadata.get('notes', {}).get('note', [])
    for note in notes:
        author_name = note.get('authorname', '')
        author_realname = note.get('authorrealname', '')
        if not is_loc_affiliated(author_name, author_realname):
            counts['notes'] += 1
    
    # Count comments (excluding LOC)
    comments = photo_data.get('comments', {}).get('comments', {}).get('comment', [])
    for comment in comments:
        author_name = comment.get('authorname', '')
        author_realname = comment.get('realname', '')
        if not is_loc_affiliated(author_name, author_realname):
            counts['comments'] += 1
    
    counts['total'] = counts['tags'] + counts['notes'] + counts['comments']
    return counts

def get_subject_terms(subjects: List[List[Dict[str, str]]]) -> Set[str]:
    """Extract all 'a' subfield values from subject data."""
    terms = set()
    for subject_group in subjects:
        for subfield in subject_group:
            if 'a' in subfield:
                terms.add(subfield['a'])
    return terms

def main():
    # Define paths
    base_dir = Path(__file__).parent.parent
    flickr_file = base_dir / 'data' / 'flickr_photos_with_metadata_comments.json'
    subject_file = base_dir / 'data' / 'subject_to_flickr_id_mapping.json'
    collections_file = base_dir / 'data' / 'collections.json'
    output_file = base_dir / 'data' / 'viz_data' / 'subject_collection_popularity.json'
    
    print("Loading data files...")
    
    # Load data
    print("  Loading Flickr photos data...")
    flickr_data = load_json(flickr_file)
    
    print("  Loading subject mappings...")
    subject_mapping = load_json(subject_file)
    
    print("  Loading collections data...")
    collections_data = load_json(collections_file)
    
    if not flickr_data:
        print("No Flickr data found!")
        return
    
    print(f"\nProcessing {len(flickr_data)} Flickr photos...")
    
    # Process each photo
    photo_interactions = {}  # flickr_id -> interaction counts
    collection_counts = defaultdict(lambda: {'photos': 0, 'tags': 0, 'notes': 0, 'comments': 0, 'total': 0})
    hdl_to_flickr = {}  # hdl_url -> flickr_id mapping
    
    for photo in flickr_data:
        flickr_id = photo.get('id')
        if not flickr_id:
            continue
        
        # Extract HDL URL and collection
        metadata = photo.get('metadata', {}).get('photo', {})
        tags = metadata.get('tags', {}).get('tag', [])
        hdl_url, collection_code = extract_hdl_and_collection(tags)
        
        # Count user interactions
        interaction_counts = count_user_interactions(photo)
        photo_interactions[flickr_id] = {
            'counts': interaction_counts,
            'collection': collection_code,
            'hdl_url': hdl_url
        }
        
        # Track HDL to Flickr mapping
        if hdl_url:
            hdl_to_flickr[hdl_url] = flickr_id
        
        # Aggregate by collection
        if collection_code and interaction_counts['total'] > 0:
            collection_counts[collection_code]['photos'] += 1
            collection_counts[collection_code]['tags'] += interaction_counts['tags']
            collection_counts[collection_code]['notes'] += interaction_counts['notes']
            collection_counts[collection_code]['comments'] += interaction_counts['comments']
            collection_counts[collection_code]['total'] += interaction_counts['total']
    
    print(f"  Found {len(photo_interactions)} photos with interaction data")
    print(f"  Found {len(collection_counts)} collections with user interactions")
    
    # Aggregate by subject
    print("\nAggregating by subject...")
    subject_counts = defaultdict(lambda: {'photos': 0, 'tags': 0, 'notes': 0, 'comments': 0, 'total': 0})
    
    for flickr_id, subject_data in subject_mapping.items():
        if flickr_id in photo_interactions:
            interaction_data = photo_interactions[flickr_id]
            counts = interaction_data['counts']
            
            # Get subjects for this photo
            subjects = subject_data.get('subject', [])
            subject_terms = get_subject_terms(subjects)
            
            # Add counts to each subject
            for term in subject_terms:
                if counts['total'] > 0:  # Only count photos with interactions
                    subject_counts[term]['photos'] += 1
                    subject_counts[term]['tags'] += counts['tags']
                    subject_counts[term]['notes'] += counts['notes']
                    subject_counts[term]['comments'] += counts['comments']
                    subject_counts[term]['total'] += counts['total']
    
    print(f"  Found {len(subject_counts)} subjects with user interactions")
    
    # Sort subjects by total interactions
    sorted_subjects = sorted(
        subject_counts.items(),
        key=lambda x: x[1]['total'],
        reverse=True
    )
    
    # Sort collections by total interactions
    sorted_collections = sorted(
        collection_counts.items(),
        key=lambda x: x[1]['total'],
        reverse=True
    )
    
    # Prepare visualization data
    viz_data = {
        'subjects': {
            'top_100': [
                {
                    'subject': subj,
                    'photos': data['photos'],
                    'interactions': {
                        'tags': data['tags'],
                        'notes': data['notes'],
                        'comments': data['comments'],
                        'total': data['total']
                    },
                    'avg_per_photo': round(data['total'] / data['photos'], 2) if data['photos'] > 0 else 0
                }
                for subj, data in sorted_subjects[:100]
            ],
            'total_subjects': len(subject_counts)
        },
        'collections': {
            'top_20': [
                {
                    'code': coll_code,
                    'title': collections_data.get(coll_code, {}).get('title', f'Unknown ({coll_code})'),
                    'photos': data['photos'],
                    'interactions': {
                        'tags': data['tags'],
                        'notes': data['notes'],
                        'comments': data['comments'],
                        'total': data['total']
                    },
                    'avg_per_photo': round(data['total'] / data['photos'], 2) if data['photos'] > 0 else 0
                }
                for coll_code, data in sorted_collections[:20]
            ],
            'total_collections': len(collection_counts)
        },
        'summary': {
            'total_photos_analyzed': len(flickr_data),
            'photos_with_subjects': len([p for p in photo_interactions.values() if p['counts']['total'] > 0]),
            'total_user_tags': sum(p['counts']['tags'] for p in photo_interactions.values()),
            'total_user_notes': sum(p['counts']['notes'] for p in photo_interactions.values()),
            'total_user_comments': sum(p['counts']['comments'] for p in photo_interactions.values()),
            'total_user_interactions': sum(p['counts']['total'] for p in photo_interactions.values())
        }
    }
    
    # Save visualization data
    print(f"\nSaving visualization data to {output_file.name}...")
    save_json(viz_data, output_file)
    
    # Generate report
    print("\n" + "="*80)
    print("SUBJECT AND COLLECTION POPULARITY ANALYSIS REPORT")
    print("="*80)
    
    print(f"\nSUMMARY:")
    print(f"  Total photos analyzed: {viz_data['summary']['total_photos_analyzed']:,}")
    print(f"  Photos with user interactions: {viz_data['summary']['photos_with_subjects']:,}")
    print(f"  Total user interactions: {viz_data['summary']['total_user_interactions']:,}")
    print(f"    - Tags: {viz_data['summary']['total_user_tags']:,}")
    print(f"    - Notes: {viz_data['summary']['total_user_notes']:,}")
    print(f"    - Comments: {viz_data['summary']['total_user_comments']:,}")
    
    print(f"\nTOP 10 MOST POPULAR SUBJECTS (by user interactions):")
    print(f"{'Rank':<5} {'Subject':<50} {'Photos':<10} {'Total':<10} {'Avg/Photo':<10}")
    print("-" * 85)
    for i, subj_data in enumerate(viz_data['subjects']['top_100'][:10], 1):
        print(f"{i:<5} {subj_data['subject'][:48]:<50} {subj_data['photos']:<10} "
              f"{subj_data['interactions']['total']:<10} {subj_data['avg_per_photo']:<10.2f}")
    
    print(f"\nTOP 10 MOST POPULAR COLLECTIONS (by user interactions):")
    print(f"{'Rank':<5} {'Collection':<50} {'Photos':<10} {'Total':<10} {'Avg/Photo':<10}")
    print("-" * 85)
    for i, coll_data in enumerate(viz_data['collections']['top_20'][:10], 1):
        title = coll_data['title'][:48]
        print(f"{i:<5} {title:<50} {coll_data['photos']:<10} "
              f"{coll_data['interactions']['total']:<10} {coll_data['avg_per_photo']:<10.2f}")
    
    print(f"\nINTERACTION TYPE BREAKDOWN:")
    total_interactions = viz_data['summary']['total_user_interactions']
    if total_interactions > 0:
        tag_pct = (viz_data['summary']['total_user_tags'] / total_interactions) * 100
        note_pct = (viz_data['summary']['total_user_notes'] / total_interactions) * 100
        comment_pct = (viz_data['summary']['total_user_comments'] / total_interactions) * 100
        print(f"  Tags:     {tag_pct:6.2f}% ({viz_data['summary']['total_user_tags']:,})")
        print(f"  Notes:    {note_pct:6.2f}% ({viz_data['summary']['total_user_notes']:,})")
        print(f"  Comments: {comment_pct:6.2f}% ({viz_data['summary']['total_user_comments']:,})")
    
    print("\n" + "="*80)
    print(f"Visualization data saved to: {output_file}")
    print("="*80)

if __name__ == "__main__":
    main()