#!/usr/bin/env python3
import json
from pathlib import Path

def extract_comments():
    input_file = Path(__file__).parent.parent / 'data' / 'flickr_photos_with_metadata_comments.json'
    output_file = Path(__file__).parent.parent / 'data' / 'extracted_comments_for_embedding.json'
    
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    extracted_comments = []
    
    for item in data:
        if 'comments' in item and 'comments' in item['comments']:
            comments_data = item['comments']['comments']
            if 'comment' in comments_data:
                for comment in comments_data['comment']:
                    extracted_comments.append({
                        'comment_id': comment['id'],
                        'comment_content': comment['_content']
                    })
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(extracted_comments, f, indent=2, ensure_ascii=False)
    
    print(f"Extracted {len(extracted_comments)} comments")
    print(f"Saved to: {output_file}")

if __name__ == '__main__':
    extract_comments()