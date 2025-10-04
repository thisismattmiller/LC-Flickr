#!/usr/bin/env python3
"""
Find the top 50 most commented photos from flickr_photos_with_metadata_comments.json
"""

import json

# Load the data
print("Loading data...")
with open('data/flickr_photos_with_metadata_comments.json', 'r') as f:
    photos = json.load(f)

# Count comments for each photo
print("Analyzing comment counts...")
photo_stats = []

for photo in photos:
    # Comments are stored in metadata.photo.comments._content as a string
    try:
        comment_count = int(photo.get('metadata', {}).get('photo', {}).get('comments', {}).get('_content', '0'))
    except (ValueError, TypeError):
        comment_count = 0

    photo_stats.append({
        'id': photo['id'],
        'title': photo.get('title', 'Untitled'),
        'url': f"https://www.flickr.com/photos/library_of_congress/{photo['id']}/",
        'comment_count': comment_count
    })

# Sort by comment count
photo_stats.sort(key=lambda x: x['comment_count'], reverse=True)

# Get top 50
top_50 = photo_stats[:50]

# Print results
print("\n" + "="*100)
print("TOP 50 MOST COMMENTED PHOTOS")
print("="*100)
print(f"{'Rank':<6} {'Comments':<10} {'Photo ID':<20} Title")
print("-"*100)

for i, photo in enumerate(top_50, 1):
    title = photo['title'][:60] + '...' if len(photo['title']) > 60 else photo['title']
    print(f"{i:<6} {photo['comment_count']:<10} {photo['id']:<20} {title}")

print("="*100)
print(f"Total photos analyzed: {len(photos):,}")

# Save to file
output = {
    'generated_at': '2025-10-04',
    'total_photos_analyzed': len(photos),
    'top_50': top_50
}

with open('data/top_50_commented_photos.json', 'w') as f:
    json.dump(output, f, indent=2)

print(f"\nResults saved to data/top_50_commented_photos.json")
