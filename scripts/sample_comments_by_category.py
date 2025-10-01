#!/usr/bin/env python3
import json
import sys
from pathlib import Path
import random
from collections import defaultdict
from datetime import datetime
import re
import unicodedata

def normalize_text_for_dedup(text):
    """Normalize text for duplicate detection."""
    if not text:
        return ""
    
    # Remove HTML tags
    text = re.sub('<[^<]+?>', '', text)
    
    # Convert to lowercase
    text = text.lower()
    
    # Normalize unicode characters
    text = unicodedata.normalize('NFKD', text)
    
    # Remove URLs
    text = re.sub(r'https?://\S+|www\.\S+', '', text)
    
    # Remove extra whitespace, newlines, tabs
    text = re.sub(r'\s+', ' ', text)
    
    # Remove punctuation but keep alphanumeric and basic spaces
    text = re.sub(r'[^\w\s]', '', text)
    
    # Strip leading/trailing whitespace
    text = text.strip()
    
    return text

def load_and_group_comments(filepath):
    """Load comments and group them by category."""
    print(f"Loading comments from {filepath}...")
    
    comments_by_category = defaultdict(list)
    total_comments = 0
    
    with open(filepath, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            if line.strip():
                try:
                    comment = json.loads(line)
                    category = comment.get('category', -1)  # Default to -1 if no category
                    comments_by_category[category].append(comment)
                    total_comments += 1
                    
                    if total_comments % 10000 == 0:
                        print(f"  Loaded {total_comments:,} comments...")
                        
                except json.JSONDecodeError as e:
                    print(f"  Warning: Error parsing line {line_num}: {e}")
                    continue
    
    print(f"  Total comments loaded: {total_comments:,}")
    print(f"  Categories found: {len(comments_by_category)}")
    
    # Show category distribution
    print("\n  Category distribution:")
    sorted_categories = sorted(comments_by_category.items(), 
                             key=lambda x: len(x[1]), 
                             reverse=True)
    
    for category, comments in sorted_categories[:10]:
        cat_label = f"Category {category}" if category != -1 else "Unclustered (-1)"
        print(f"    {cat_label:20s}: {len(comments):6,} comments")
    
    if len(sorted_categories) > 10:
        print(f"    ... and {len(sorted_categories) - 10} more categories")
    
    return comments_by_category, total_comments

def sample_comments(comments_by_category, max_per_category=500, seed=42):
    """Sample up to max_per_category comments from each category, removing duplicates."""
    print(f"\nSampling up to {max_per_category} comments per category (with deduplication)...")
    
    # Set random seed for reproducibility
    random.seed(seed)
    
    # Global set to track all seen normalized comments
    global_seen_normalized = set()
    
    sampled_data = {}
    total_sampled = 0
    total_duplicates_removed = 0
    categories_sampled = 0
    
    for category, comments in sorted(comments_by_category.items()):
        # Shuffle comments for random sampling
        shuffled_comments = comments.copy()
        random.shuffle(shuffled_comments)
        
        # Sample comments with deduplication
        sample = []
        duplicates_in_category = 0
        
        for comment in shuffled_comments:
            if len(sample) >= max_per_category:
                break
                
            # Normalize comment text for duplicate detection
            comment_text = comment.get('comment_content', '')
            normalized = normalize_text_for_dedup(comment_text)
            
            # Skip if we've seen this normalized text before
            if normalized and normalized in global_seen_normalized:
                duplicates_in_category += 1
                continue
            
            # Skip empty comments
            if not normalized:
                continue
                
            # Add to sample and mark as seen
            sample.append(comment)
            if normalized:
                global_seen_normalized.add(normalized)
        
        # Report sampling results
        if duplicates_in_category > 0:
            print(f"  Category {category:3}: Sampled {len(sample):4} from {len(comments):,} comments ({duplicates_in_category} duplicates skipped)")
        else:
            print(f"  Category {category:3}: Sampled {len(sample):4} from {len(comments):,} comments")
        
        # Store sampled comments
        sampled_data[str(category)] = {
            'category_id': category,
            'total_comments': len(comments),
            'sampled_count': len(sample),
            'duplicates_removed': duplicates_in_category,
            'comments': sample
        }
        
        total_sampled += len(sample)
        total_duplicates_removed += duplicates_in_category
        categories_sampled += 1
    
    print(f"\n  Total comments sampled: {total_sampled:,}")
    print(f"  Total duplicates removed: {total_duplicates_removed:,}")
    print(f"  Categories sampled: {categories_sampled}")
    
    return sampled_data, total_sampled

def add_statistics(sampled_data):
    """Add statistics to the sampled data."""
    stats = {
        'total_categories': len(sampled_data),
        'total_sampled_comments': sum(cat['sampled_count'] for cat in sampled_data.values()),
        'total_original_comments': sum(cat['total_comments'] for cat in sampled_data.values()),
        'total_duplicates_removed': sum(cat.get('duplicates_removed', 0) for cat in sampled_data.values()),
        'categories': []
    }
    
    # Add per-category stats
    for category_id, data in sorted(sampled_data.items(), 
                                   key=lambda x: x[1]['sampled_count'], 
                                   reverse=True):
        stats['categories'].append({
            'category_id': data['category_id'],
            'total_comments': data['total_comments'],
            'sampled_count': data['sampled_count'],
            'sampling_rate': round(data['sampled_count'] / data['total_comments'] * 100, 2)
        })
        
        # Add sample comments preview (first 3)
        sample_texts = []
        for comment in data['comments'][:3]:
            # Clean and truncate comment text
            text = comment.get('comment_content', '')
            # Remove HTML tags
            import re
            text = re.sub('<[^<]+?>', '', text)
            text = text.strip()[:100]  # Truncate to 100 chars
            if text:
                sample_texts.append(text)
        
        data['sample_texts'] = sample_texts
    
    return stats

def save_results(sampled_data, stats, output_file):
    """Save sampled data to JSON file."""
    print(f"\nSaving results to {output_file}...")
    
    output = {
        'metadata': {
            'generated_at': datetime.now().isoformat(),
            'source_file': 'comments_with_categories.jsonl',
            'max_per_category': 500,
            'random_seed': 42
        },
        'statistics': stats,
        'data': sampled_data
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    # Check file size
    file_size = output_file.stat().st_size / (1024 * 1024)  # Size in MB
    print(f"  File size: {file_size:.2f} MB")
    
    return file_size

def save_simplified_results(sampled_data, output_file):
    """Save simplified version with just category and comment texts."""
    print(f"\nSaving simplified results to {output_file}...")
    
    # Create simplified structure
    simplified = []
    
    for category_str, data in sorted(sampled_data.items(), 
                                     key=lambda x: int(x[0]) if x[0] != '-1' else -1):
        category_id = data['category_id']
        
        # Extract just the comment texts
        comment_texts = []
        for comment in data['comments']:
            text = comment.get('comment_content', '')
            if text:
                comment_texts.append(text)
        
        simplified.append({
            'category': category_id,
            'comments': comment_texts
        })
    
    # Save to file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(simplified, f, indent=2, ensure_ascii=False)
    
    # Check file size
    file_size = output_file.stat().st_size / (1024 * 1024)  # Size in MB
    print(f"  File size: {file_size:.2f} MB")
    print(f"  Structure: Array of {len(simplified)} category objects")
    print(f"  Total comments: {sum(len(cat['comments']) for cat in simplified):,}")
    
    return file_size

def print_summary(stats):
    """Print a nice summary of the sampling."""
    print("\n" + "="*60)
    print("SAMPLING SUMMARY")
    print("="*60)
    
    print(f"\n📊 Overall Statistics:")
    print(f"  • Total categories: {stats['total_categories']}")
    print(f"  • Original comments: {stats['total_original_comments']:,}")
    print(f"  • Sampled comments: {stats['total_sampled_comments']:,}")
    print(f"  • Duplicates removed: {stats.get('total_duplicates_removed', 0):,}")
    print(f"  • Overall sampling rate: {stats['total_sampled_comments']/stats['total_original_comments']*100:.1f}%")
    
    print(f"\n🎲 Top 10 Categories by Sample Size:")
    for i, cat_stat in enumerate(stats['categories'][:10], 1):
        cat_id = cat_stat['category_id']
        cat_label = f"Category {cat_id}" if cat_id != -1 else "Unclustered"
        bar_length = int(cat_stat['sampling_rate'] * 0.3)  # Scale to max 30 chars
        bar = '█' * bar_length if bar_length > 0 else '▏'
        
        print(f"  {i:2d}. {cat_label:15s}: {cat_stat['sampled_count']:3d}/{cat_stat['total_comments']:5,} "
              f"({cat_stat['sampling_rate']:5.1f}%) {bar}")

def main():
    # Set up paths
    script_dir = Path(__file__).parent
    data_dir = script_dir.parent / 'data'
    
    input_file = data_dir / 'comments_with_categories.jsonl'
    output_file = data_dir / 'comments_by_category_sample.json'
    simplified_output_file = data_dir / 'comments_by_category_simple.json'
    
    # Check if input file exists
    if not input_file.exists():
        print(f"Error: Input file not found: {input_file}")
        print("Please run add_cluster_categories.py first to generate categorized comments.")
        sys.exit(1)
    
    # Parse command line arguments
    max_per_category = 500
    if len(sys.argv) > 1:
        try:
            max_per_category = int(sys.argv[1])
            print(f"📌 Using custom sample size: {max_per_category} per category")
        except ValueError:
            print(f"Warning: Invalid sample size '{sys.argv[1]}', using default: 500")
    
    # Check if output files exist
    if output_file.exists() or simplified_output_file.exists():
        existing_files = []
        if output_file.exists():
            existing_files.append(output_file.name)
        if simplified_output_file.exists():
            existing_files.append(simplified_output_file.name)
        
        response = input(f"Output file(s) {', '.join(existing_files)} already exist. Overwrite? (y/n): ")
        if response.lower() != 'y':
            print("Operation cancelled.")
            sys.exit(0)
    
    try:
        print("="*60)
        print(f"SAMPLE COMMENTS BY CATEGORY (max {max_per_category} per category)")
        print("="*60)
        
        # Load and group comments
        comments_by_category, total_comments = load_and_group_comments(input_file)
        
        # Sample comments
        sampled_data, total_sampled = sample_comments(
            comments_by_category, 
            max_per_category=max_per_category,
            seed=42  # Fixed seed for reproducibility
        )
        
        # Add statistics
        stats = add_statistics(sampled_data)
        
        # Save results - both full and simplified versions
        file_size = save_results(sampled_data, stats, output_file)
        simplified_file_size = save_simplified_results(sampled_data, simplified_output_file)
        
        # Print summary
        print_summary(stats)
        
        print(f"\n✅ Sampling complete!")
        print(f"   Full output: {output_file}")
        print(f"                Size: {file_size:.2f} MB")
        print(f"   Simplified:  {simplified_output_file}")
        print(f"                Size: {simplified_file_size:.2f} MB")
        
        print(f"\n💡 Output files:")
        print(f"  Full version ({output_file.name}):")
        print(f"    • Contains all comment fields (id, content, x, y, category)")
        print(f"    • Includes metadata and statistics")
        print(f"    • Use 'data' field to access comments by category")
        print(f"  Simplified version ({simplified_output_file.name}):")
        print(f"    • Array of objects with just 'category' and 'comments' fields")
        print(f"    • Comments array contains only the text content")
        print(f"    • Smaller file size, easier to process")
        
        print(f"\n📝 Custom sample size:")
        print(f"   python {Path(__file__).name} <max_per_category>")
        print(f"   Example: python {Path(__file__).name} 1000  # Sample up to 1000 per category")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()