#!/usr/bin/env python3

import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Load the data
input_file = Path(__file__).parent.parent / 'data' / 'flickr_photos_with_metadata_comments.json'
output_file = Path(__file__).parent.parent / 'data' / 'comments_by_day.json'

print(f"Loading data from {input_file}...")
with open(input_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Count comments by day
comments_by_day = defaultdict(int)

for item in data:
    if 'comments' in item and 'comments' in item['comments']:
        comments_data = item['comments']['comments']
        if 'comment' in comments_data:
            for comment in comments_data['comment']:
                if 'datecreate' in comment:
                    # Convert timestamp to date
                    timestamp = int(comment['datecreate'])
                    date = datetime.fromtimestamp(timestamp)
                    day_str = date.strftime('%Y-%m-%d')
                    comments_by_day[day_str] += 1

# Convert to list of dictionaries and sort by date
result = [
    {'day': day, 'comment_count': count} 
    for day, count in comments_by_day.items()
]
result.sort(key=lambda x: x['day'])

print(f"Found comments across {len(result)} days")
print(f"Total comments: {sum(item['comment_count'] for item in result)}")
print(f"Date range: {result[0]['day']} to {result[-1]['day']}")

# Show some statistics
print(f"\nTop 5 days with most comments:")
sorted_by_count = sorted(result, key=lambda x: x['comment_count'], reverse=True)[:5]
for item in sorted_by_count:
    print(f"  {item['day']}: {item['comment_count']} comments")

# Write to output file
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(result, f, indent=2)

print(f"\nWritten to {output_file}")