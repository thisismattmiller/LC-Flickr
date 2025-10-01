#!/usr/bin/env python3
"""
Analyze the 20/80 rule for tags, comments, and notes on Flickr photos.
Determine what percentage of users are responsible for the bulk of activity.
"""

import json
import os
from collections import defaultdict
from typing import Dict, List, Tuple
import math

# Configuration
INPUT_FILE = "../data/flickr_photos_with_metadata_comments.json"
OUTPUT_DIR = "../data/viz_data"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "user_activity_20_80_analysis.json")

def is_loc_account(author_name: str) -> bool:
    """Check if account is Library of Congress or LOC-related."""
    if not author_name:
        return False
    author_lower = author_name.lower()
    # Filter any account with "loc" in the name or the official Library of Congress account
    return author_lower == "the library of congress" or "loc" in author_lower

def analyze_tags(photos: List[Dict]) -> Tuple[Dict, Dict]:
    """Analyze tag contributions by users."""
    tag_counts_by_user = defaultdict(int)
    total_tags = 0
    total_tags_unfiltered = 0
    loc_tags = 0
    
    for photo in photos:
        tags = photo.get('metadata', {}).get('photo', {}).get('tags', {}).get('tag', [])
        
        for tag in tags:
            author_name = tag.get('authorname', '')
            total_tags_unfiltered += 1
            
            # Skip LOC accounts
            if is_loc_account(author_name):
                loc_tags += 1
                continue
            
            if author_name:
                tag_counts_by_user[author_name] += 1
                total_tags += 1
    
    return tag_counts_by_user, {
        'total': total_tags,
        'total_unfiltered': total_tags_unfiltered,
        'loc_tags': loc_tags
    }

def analyze_comments(photos: List[Dict]) -> Tuple[Dict, Dict]:
    """Analyze comment contributions by users."""
    comment_counts_by_user = defaultdict(int)
    total_comments = 0
    total_comments_unfiltered = 0
    loc_comments = 0

    for photo in photos:
        comments = photo.get('comments', {}).get('comments', {}).get('comment', [])

        for comment in comments:
            author_name = comment.get('authorname', '')
            total_comments_unfiltered += 1

            # Skip LOC accounts
            if is_loc_account(author_name):
                loc_comments += 1
                continue

            if author_name:
                comment_counts_by_user[author_name] += 1
                total_comments += 1

    return comment_counts_by_user, {
        'total': total_comments,
        'total_unfiltered': total_comments_unfiltered,
        'loc_comments': loc_comments
    }

def analyze_notes(photos: List[Dict]) -> Tuple[Dict, Dict]:
    """Analyze note contributions by users."""
    note_counts_by_user = defaultdict(int)
    total_notes = 0
    total_notes_unfiltered = 0
    loc_notes = 0

    for photo in photos:
        notes = photo.get('metadata', {}).get('photo', {}).get('notes', {}).get('note', [])

        for note in notes:
            author_name = note.get('authorname', '')
            total_notes_unfiltered += 1

            # Skip LOC accounts
            if is_loc_account(author_name):
                loc_notes += 1
                continue

            if author_name:
                note_counts_by_user[author_name] += 1
                total_notes += 1

    return note_counts_by_user, {
        'total': total_notes,
        'total_unfiltered': total_notes_unfiltered,
        'loc_notes': loc_notes
    }

def calculate_20_80_stats(user_counts: Dict[str, int], activity_type: str) -> Dict:
    """Calculate 20/80 rule statistics."""
    if not user_counts:
        return {
            'activity_type': activity_type,
            'total_users': 0,
            'total_activities': 0,
            'distribution': []
        }
    
    # Sort users by their activity count (descending)
    sorted_users = sorted(user_counts.items(), key=lambda x: x[1], reverse=True)
    total_users = len(sorted_users)
    total_activities = sum(count for _, count in sorted_users)
    
    # Calculate cumulative percentages
    distribution = []
    cumulative_activities = 0
    
    for i, (user, count) in enumerate(sorted_users):
        cumulative_activities += count
        user_percentage = ((i + 1) / total_users) * 100
        activity_percentage = (cumulative_activities / total_activities) * 100
        
        distribution.append({
            'user': user,
            'activity_count': count,
            'user_rank': i + 1,
            'user_percentage': round(user_percentage, 2),
            'cumulative_activity_percentage': round(activity_percentage, 2)
        })
    
    # Find key breakpoints
    breakpoints = {}
    targets = [10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 99]
    
    for target in targets:
        for item in distribution:
            if item['cumulative_activity_percentage'] >= target:
                breakpoints[f'users_for_{target}pct_activity'] = {
                    'user_count': item['user_rank'],
                    'user_percentage': item['user_percentage'],
                    'activity_percentage': target
                }
                break
    
    # Calculate top contributors
    top_users = []
    for i in range(min(20, len(sorted_users))):
        user, count = sorted_users[i]
        percentage = (count / total_activities) * 100
        top_users.append({
            'rank': i + 1,
            'user': user,
            'count': count,
            'percentage': round(percentage, 2)
        })
    
    return {
        'activity_type': activity_type,
        'total_users': total_users,
        'total_activities': total_activities,
        'average_per_user': round(total_activities / total_users, 2) if total_users > 0 else 0,
        'median_activities': sorted_users[total_users // 2][1] if total_users > 0 else 0,
        'breakpoints': breakpoints,
        'top_20_users': top_users,
        'distribution_sample': distribution[:100]  # First 100 users for visualization
    }

def print_analysis(stats: Dict, activity_type: str):
    """Print analysis results to console."""
    print(f"\n{'='*60}")
    print(f"{activity_type.upper()} ANALYSIS")
    print(f"{'='*60}")
    
    if stats['total_users'] == 0:
        print(f"No {activity_type} found after filtering LOC accounts.")
        return
    
    print(f"Total users: {stats['total_users']:,}")
    print(f"Total {activity_type}: {stats['total_activities']:,}")
    print(f"Average per user: {stats['average_per_user']:.2f}")
    print(f"Median activities: {stats['median_activities']}")
    
    print(f"\n20/80 RULE ANALYSIS:")
    print("-" * 40)
    
    breakpoints = stats['breakpoints']
    
    # Find closest to 20% of users
    for key, value in breakpoints.items():
        if '80' in key:
            users_for_80 = value
            print(f"✓ {users_for_80['user_percentage']:.1f}% of users ({users_for_80['user_count']:,} users)")
            print(f"  are responsible for {users_for_80['activity_percentage']}% of all {activity_type}")
            
            if users_for_80['user_percentage'] <= 20:
                print(f"  → CONFIRMS 20/80 rule! (actually {users_for_80['user_percentage']:.1f}/80)")
            elif users_for_80['user_percentage'] <= 30:
                print(f"  → Close to 20/80 rule (actually {users_for_80['user_percentage']:.1f}/80)")
            else:
                print(f"  → Does not follow strict 20/80 rule")
    
    print(f"\nOTHER KEY BREAKPOINTS:")
    print("-" * 40)
    
    for percentage in [50, 90, 95]:
        key = f'users_for_{percentage}pct_activity'
        if key in breakpoints:
            value = breakpoints[key]
            print(f"• {value['user_percentage']:.1f}% of users → {percentage}% of {activity_type}")
    
    print(f"\nTOP 10 CONTRIBUTORS:")
    print("-" * 40)
    
    for user_data in stats['top_20_users'][:10]:
        print(f"{user_data['rank']:2d}. {user_data['user'][:30]:30s} - {user_data['count']:5d} {activity_type} ({user_data['percentage']:.2f}%)")

def main():
    # Create output directory if it doesn't exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Load data
    print(f"Loading data from {INPUT_FILE}")
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        photos = json.load(f)
    
    print(f"Loaded {len(photos)} photos")
    
    # Analyze tags
    print("\nAnalyzing tags...")
    tag_counts, tag_stats = analyze_tags(photos)
    print(f"  Total tags (unfiltered): {tag_stats['total_unfiltered']:,}")
    print(f"  LOC tags filtered: {tag_stats['loc_tags']:,}")
    print(f"  Tags for analysis: {tag_stats['total']:,}")
    tag_analysis = calculate_20_80_stats(tag_counts, 'tags')
    
    # Analyze comments
    print("\nAnalyzing comments...")
    comment_counts, comment_stats = analyze_comments(photos)
    print(f"  Total comments (unfiltered): {comment_stats['total_unfiltered']:,}")
    print(f"  LOC comments filtered: {comment_stats['loc_comments']:,}")
    print(f"  Comments for analysis: {comment_stats['total']:,}")
    comment_analysis = calculate_20_80_stats(comment_counts, 'comments')

    # Analyze notes
    print("\nAnalyzing notes...")
    note_counts, note_stats = analyze_notes(photos)
    print(f"  Total notes (unfiltered): {note_stats['total_unfiltered']:,}")
    print(f"  LOC notes filtered: {note_stats['loc_notes']:,}")
    print(f"  Notes for analysis: {note_stats['total']:,}")
    note_analysis = calculate_20_80_stats(note_counts, 'notes')

    # Print results
    print_analysis(tag_analysis, 'tags')
    print_analysis(comment_analysis, 'comments')
    print_analysis(note_analysis, 'notes')
    
    # Prepare visualization data
    viz_data = {
        'analysis_date': os.popen('date').read().strip(),
        'total_photos': len(photos),
        'tags': tag_analysis,
        'comments': comment_analysis,
        'notes': note_analysis,
        'summary': {
            'tags_follow_20_80': False,
            'comments_follow_20_80': False,
            'notes_follow_20_80': False,
            'tags_concentration': '',
            'comments_concentration': '',
            'notes_concentration': ''
        }
    }
    
    # Determine if 20/80 rule applies
    if 'users_for_80pct_activity' in tag_analysis['breakpoints']:
        tag_80 = tag_analysis['breakpoints']['users_for_80pct_activity']
        viz_data['summary']['tags_follow_20_80'] = tag_80['user_percentage'] <= 30
        viz_data['summary']['tags_concentration'] = f"{tag_80['user_percentage']:.1f}% users → 80% activity"

    if 'users_for_80pct_activity' in comment_analysis['breakpoints']:
        comment_80 = comment_analysis['breakpoints']['users_for_80pct_activity']
        viz_data['summary']['comments_follow_20_80'] = comment_80['user_percentage'] <= 30
        viz_data['summary']['comments_concentration'] = f"{comment_80['user_percentage']:.1f}% users → 80% activity"

    if 'users_for_80pct_activity' in note_analysis['breakpoints']:
        note_80 = note_analysis['breakpoints']['users_for_80pct_activity']
        viz_data['summary']['notes_follow_20_80'] = note_80['user_percentage'] <= 30
        viz_data['summary']['notes_concentration'] = f"{note_80['user_percentage']:.1f}% users → 80% activity"
    
    # Save visualization data
    print(f"\nSaving visualization data to {OUTPUT_FILE}")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(viz_data, f, indent=2, ensure_ascii=False)
    
    # Print final summary
    print("\n" + "="*60)
    print("FINAL SUMMARY")
    print("="*60)

    if viz_data['summary']['tags_follow_20_80']:
        print("✓ TAGS follow the 20/80 rule")
        print(f"  {viz_data['summary']['tags_concentration']}")
    else:
        print("✗ TAGS do not strictly follow the 20/80 rule")
        print(f"  {viz_data['summary']['tags_concentration']}")

    if viz_data['summary']['comments_follow_20_80']:
        print("✓ COMMENTS follow the 20/80 rule")
        print(f"  {viz_data['summary']['comments_concentration']}")
    else:
        print("✗ COMMENTS do not strictly follow the 20/80 rule")
        print(f"  {viz_data['summary']['comments_concentration']}")

    if viz_data['summary']['notes_follow_20_80']:
        print("✓ NOTES follow the 20/80 rule")
        print(f"  {viz_data['summary']['notes_concentration']}")
    else:
        print("✗ NOTES do not strictly follow the 20/80 rule")
        print(f"  {viz_data['summary']['notes_concentration']}")

    print(f"\nVisualization data saved to: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()