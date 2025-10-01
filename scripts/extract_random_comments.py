#!/usr/bin/env python3

import json
import random
from pathlib import Path

# Load the data
input_file = Path(__file__).parent.parent / 'data' / 'flickr_photos_with_metadata_comments.json'
output_file = Path(__file__).parent.parent / 'data' / 'random_selection.json'

print(f"Loading data from {input_file}...")
with open(input_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Extract all comments with their metadata
all_comments = []
for item in data:
    if 'comments' in item and 'comments' in item['comments']:
        comments_data = item['comments']['comments']
        if 'comment' in comments_data:
            for comment in comments_data['comment']:
                if '_content' in comment and 'authorname' in comment and 'id' in comment:
                    all_comments.append({
                        'comment': comment['_content'],
                        'author': comment['authorname'],
                        'id': comment['id']
                    })

print(f"Found {len(all_comments)} total comments")

# Select random samples
num_samples = min(1000, len(all_comments))
random_selection = random.sample(all_comments, num_samples)

print(f"Selected {num_samples} random comments")

# Write to output file
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(random_selection, f, indent=2, ensure_ascii=False)

print(f"Written to {output_file}")
print(f"Sample of first 3 comments:")
for i, comment in enumerate(random_selection[:3]):
    print(f"\n{i+1}. Author: {comment['author']}")
    print(f"   ID: {comment['id']}")
    print(f"   Comment: {comment['comment'][:100]}..." if len(comment['comment']) > 100 else f"   Comment: {comment['comment']}")