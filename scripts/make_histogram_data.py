#!/usr/bin/env python3
"""
Generate histogram data for visualizing comments over time.

This script processes Flickr photo metadata and creates a JSON file with weekly
counts of comments grouped by year and week number.
"""

import json
from datetime import datetime
from collections import defaultdict
from pathlib import Path


def get_year_week(timestamp):
    """Convert Unix timestamp to (year, week_number) tuple."""
    dt = datetime.fromtimestamp(int(timestamp))
    # isocalendar() returns (year, week, weekday)
    iso = dt.isocalendar()
    return (iso[0], iso[1])


def process_photos(input_file):
    """Process photos and aggregate comment data by year and week."""
    # Structure: data[year][week] = count
    data = defaultdict(lambda: defaultdict(int))

    with open(input_file, 'r', encoding='utf-8') as f:
        photos = json.load(f)

    print(f"Processing {len(photos)} photos...")

    for photo in photos:
        # Process comments
        comments_data = photo.get('comments', {}).get('comments', {})
        comment_list = comments_data.get('comment', [])
        if comment_list:
            for comment in comment_list:
                datecreate = comment.get('datecreate')
                if datecreate:
                    year, week = get_year_week(datecreate)
                    data[year][week] += 1

    return data


def format_output_data(data):
    """Convert nested defaultdict to a structured list format."""
    output = []

    for year in sorted(data.keys()):
        year_data = {
            'year': year,
            'weeks': []
        }

        for week in sorted(data[year].keys()):
            week_data = {
                'week': week,
                'comments': data[year][week]
            }
            year_data['weeks'].append(week_data)

        output.append(year_data)

    return output


def main():
    # Set up paths
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    input_file = project_root / 'data' / 'flickr_photos_with_metadata_comments.json'
    output_dir = project_root / 'data' / 'viz_data'
    output_file = output_dir / 'histogram_data.json'

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Process the data
    print(f"Reading from: {input_file}")
    histogram_data = process_photos(input_file)

    # Format for output
    formatted_data = format_output_data(histogram_data)

    # Calculate summary statistics
    total_comments = sum(w['comments'] for y in formatted_data for w in y['weeks'])

    # Create final output structure
    output_data = {
        'generated_at': datetime.now().isoformat(),
        'summary': {
            'total_comments': total_comments
        },
        'data': formatted_data
    }

    # Write output
    print(f"Writing to: {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"\nSummary:")
    print(f"  Total comments: {total_comments:,}")
    print(f"  Years covered: {len(formatted_data)}")
    print(f"\nHistogram data saved to: {output_file}")


if __name__ == '__main__':
    main()