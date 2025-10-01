#!/usr/bin/env python3

import json
import re
from pathlib import Path
from collections import defaultdict

# Load the data
input_file = Path(__file__).parent.parent / 'data' / 'flickr_photos_with_metadata_comments.json'
output_file = Path(__file__).parent.parent / 'data' / 'comments_by_tag.json'

print(f"Loading data from {input_file}...")
with open(input_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Count tags
tag_counts = defaultdict(int)
total_photos = 0
photos_with_tags = 0
filtered_tags = 0

# Patterns to filter out
url_pattern = re.compile(r'https?://|www\.|\.com|\.org|\.gov|\.net', re.IGNORECASE)
loc_pattern = re.compile(r'library\s*of\s*congress|loc\.gov|hdl\.loc\.gov', re.IGNORECASE)

for item in data:
    total_photos += 1
    if 'metadata' in item and 'photo' in item['metadata']:
        photo_data = item['metadata']['photo']
        if 'tags' in photo_data and 'tag' in photo_data['tags']:
            photos_with_tags += 1
            tags = photo_data['tags']['tag']
            for tag in tags:
                if 'raw' in tag:
                    tag_raw = tag['raw']
                    
                    # Skip if contains URL or Library of Congress reference
                    if url_pattern.search(tag_raw) or loc_pattern.search(tag_raw):
                        filtered_tags += 1
                        continue
                    
                    # Also skip machine tags (contain colons like dc:identifier)
                    if ':' in tag_raw and '=' in tag_raw:
                        filtered_tags += 1
                        continue
                    
                    tag_counts[tag_raw] += 1

# Convert to list of dictionaries and sort by count descending
result = [
    {'tag': tag, 'count': count} 
    for tag, count in tag_counts.items()
]
result.sort(key=lambda x: x['count'], reverse=True)

print(f"\nStatistics:")
print(f"Total photos: {total_photos}")
print(f"Photos with tags: {photos_with_tags}")
print(f"Unique tags (after filtering): {len(result)}")
print(f"Tags filtered out: {filtered_tags}")
print(f"Total tag occurrences: {sum(item['count'] for item in result)}")

print(f"\nTop 20 most common tags:")
for i, item in enumerate(result[:20], 1):
    print(f"  {i:2}. {item['tag']}: {item['count']} occurrences")

# Write to output file
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(result, f, indent=2, ensure_ascii=False)

print(f"\nWritten to {output_file}")