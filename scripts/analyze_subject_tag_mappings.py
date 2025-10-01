#!/usr/bin/env python3
"""
Analyze recurring mappings between Library of Congress subjects and user-generated tags.

This script finds which user tags are frequently associated with specific LC subjects,
helping to understand how the public categorizes and describes archival content.
"""

import json
from pathlib import Path
from collections import defaultdict
from typing import Dict, Set, List


def is_loc_affiliated(authorname: str) -> bool:
    """Check if a tag author is affiliated with Library of Congress."""
    if not authorname:
        return False

    authorname_lower = authorname.lower()
    return (
        "library of congress" in authorname_lower or
        "(loc)" in authorname_lower
    )


def normalize_subject(subject: str) -> str:
    """
    Normalize a subject string by removing trailing punctuation and extra whitespace.
    This helps collapse duplicates like "Waterfalls" and "Waterfalls."
    """
    # Strip leading/trailing whitespace
    normalized = subject.strip()

    # Remove trailing punctuation (period, comma, semicolon, etc.)
    while normalized and normalized[-1] in '.,;:!?':
        normalized = normalized[:-1].strip()

    return normalized


def get_subject_terms(subject_data: List[List[Dict]]) -> Set[str]:
    """Extract all subject terms from subfield 'a' and normalize them."""
    terms = set()
    for subject_group in subject_data:
        for subfield in subject_group:
            if 'a' in subfield:
                normalized = normalize_subject(subfield['a'])
                if normalized:  # Only add non-empty strings
                    terms.add(normalized)
    return terms


def get_user_tags(tags_data: Dict) -> List[str]:
    """Extract tag content from user-generated tags (excluding LOC)."""
    user_tags = []
    tag_list = tags_data.get('tag', [])

    for tag in tag_list:
        authorname = tag.get('authorname', '')
        # Skip LOC-affiliated authors
        if not is_loc_affiliated(authorname):
            # Use the raw tag text
            raw_tag = tag.get('raw', '')
            if raw_tag:
                user_tags.append(raw_tag)

    return user_tags


def main():
    # Set up paths
    base_dir = Path(__file__).parent.parent
    flickr_file = base_dir / 'data' / 'flickr_photos_with_metadata.json'
    subject_file = base_dir / 'data' / 'subject_to_flickr_id_mapping.json'
    output_file = base_dir / 'data' / 'subject_tag_mappings.json'

    print("Loading data files...")

    # Load Flickr metadata
    print(f"  Loading {flickr_file.name}...")
    with open(flickr_file, 'r', encoding='utf-8') as f:
        flickr_photos = json.load(f)

    # Create a lookup by photo ID
    flickr_by_id = {}
    for photo in flickr_photos:
        photo_id = photo.get('id')
        if photo_id:
            flickr_by_id[photo_id] = photo

    print(f"  Loaded {len(flickr_by_id)} photos")

    # Load subject mappings
    print(f"  Loading {subject_file.name}...")
    with open(subject_file, 'r', encoding='utf-8') as f:
        subject_mappings = json.load(f)

    print(f"  Loaded {len(subject_mappings)} subject mappings")

    # Build subject-to-tag co-occurrence map
    print("\nAnalyzing subject-tag mappings...")

    # Structure: subject_tag_counts[subject][tag] = count
    subject_tag_counts = defaultdict(lambda: defaultdict(int))

    # Track which photos have each subject
    subject_photo_counts = defaultdict(int)

    # Process each photo with subject data
    processed_photos = 0
    photos_with_user_tags = 0

    # Track photo IDs for each subject
    subject_photo_ids = defaultdict(list)

    for photo_id, subject_data in subject_mappings.items():
        if photo_id not in flickr_by_id:
            continue

        processed_photos += 1

        # Get subjects for this photo
        subjects = subject_data.get('subject', [])
        subject_terms = get_subject_terms(subjects)

        if not subject_terms:
            continue

        # Get user tags for this photo
        photo = flickr_by_id[photo_id]
        metadata = photo.get('metadata', {}).get('photo', {})
        tags_data = metadata.get('tags', {})
        user_tags = get_user_tags(tags_data)

        if not user_tags:
            continue

        photos_with_user_tags += 1

        # Record co-occurrences and photo IDs
        for subject in subject_terms:
            subject_photo_counts[subject] += 1
            subject_photo_ids[subject].append(photo_id)
            for tag in user_tags:
                subject_tag_counts[subject][tag] += 1

        if processed_photos % 5000 == 0:
            print(f"  Processed {processed_photos} photos...")

    print(f"  Processed {processed_photos} photos total")
    print(f"  Found {photos_with_user_tags} photos with user tags")
    print(f"  Found {len(subject_tag_counts)} subjects with user tag associations")

    # Build output structure
    print("\nBuilding results...")

    MIN_OCCURRENCES = 2  # Minimum number of times a tag must appear with a subject

    results = []

    for subject in sorted(subject_tag_counts.keys()):
        tag_counts = subject_tag_counts[subject]

        # Filter tags that occur at least MIN_OCCURRENCES times
        filtered_tags = {tag: count for tag, count in tag_counts.items() if count >= MIN_OCCURRENCES}

        if not filtered_tags:
            continue  # Skip subjects with no recurring tags

        # Sort tags by count (most frequent first)
        sorted_tags = sorted(
            filtered_tags.items(),
            key=lambda x: x[1],
            reverse=True
        )

        # Get top tags (limit to reasonable number)
        top_tags = [
            {
                'tag': tag,
                'count': count,
                'percentage': round((count / subject_photo_counts[subject]) * 100, 2)
            }
            for tag, count in sorted_tags[:50]  # Top 50 tags per subject
        ]

        results.append({
            'subject': subject,
            'total_photos': subject_photo_counts[subject],
            'total_unique_tags': len(filtered_tags),
            'photo_ids': subject_photo_ids[subject],
            'top_tags': top_tags
        })

    # Sort results by total photos (most common subjects first)
    results.sort(key=lambda x: x['total_photos'], reverse=True)

    # Create output structure
    output_data = {
        'summary': {
            'total_subjects': len(results),
            'total_photos_analyzed': processed_photos,
            'photos_with_user_tags': photos_with_user_tags
        },
        'mappings': results
    }

    # Save results
    print(f"\nSaving results to {output_file.name}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    # Print summary report
    print("\n" + "="*80)
    print("SUBJECT-TAG MAPPING ANALYSIS REPORT")
    print("="*80)

    print(f"\nSUMMARY:")
    print(f"  Total subjects analyzed: {len(results):,}")
    print(f"  Total photos analyzed: {processed_photos:,}")
    print(f"  Photos with user tags: {photos_with_user_tags:,}")

    print(f"\nTOP 10 SUBJECTS BY PHOTO COUNT:")
    print(f"{'Rank':<5} {'Subject':<50} {'Photos':<10} {'Unique Tags':<12}")
    print("-" * 80)
    for i, item in enumerate(results[:10], 1):
        subject_display = item['subject'][:48]
        print(f"{i:<5} {subject_display:<50} {item['total_photos']:<10} {item['total_unique_tags']:<12}")

    print(f"\nEXAMPLE: Top tags for '{results[0]['subject']}':")
    for tag_data in results[0]['top_tags'][:10]:
        print(f"  - {tag_data['tag'][:60]:<62} (count: {tag_data['count']}, {tag_data['percentage']}%)")

    print("\n" + "="*80)
    print(f"Full results saved to: {output_file}")
    print("="*80)


if __name__ == '__main__':
    main()