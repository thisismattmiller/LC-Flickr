#!/usr/bin/env python3
import json
import sys
from pathlib import Path
from datetime import datetime

def load_cluster_mapping(clusters_file):
    """Load cluster data and create a mapping of comment_id to cluster_id."""
    print(f"Loading cluster data from {clusters_file}...")
    
    with open(clusters_file, 'r', encoding='utf-8') as f:
        cluster_data = json.load(f)
    
    # Create mapping
    id_to_cluster = {}
    total_mapped = 0
    
    for cluster in cluster_data['clusters']:
        cluster_id = cluster['cluster_id']
        for comment_id in cluster['comment_ids']:
            id_to_cluster[comment_id] = cluster_id
            total_mapped += 1
    
    print(f"  Loaded {len(cluster_data['clusters'])} clusters")
    print(f"  Mapped {total_mapped:,} comment IDs to clusters")
    
    # Print cluster distribution
    print(f"\n  Cluster distribution:")
    for i, cluster in enumerate(cluster_data['clusters'][:10]):  # Show top 10
        print(f"    Cluster {cluster['cluster_id']:3d}: {cluster['count']:6,} comments")
    
    return id_to_cluster, cluster_data

def add_categories_to_comments(input_file, output_file, id_to_cluster):
    """Add category field to each comment based on cluster mapping."""
    print(f"\nProcessing comments from {input_file}...")
    
    processed = 0
    matched = 0
    unmatched = []
    
    with open(input_file, 'r', encoding='utf-8') as infile, \
         open(output_file, 'w', encoding='utf-8') as outfile:
        
        for line_num, line in enumerate(infile, 1):
            if line.strip():
                try:
                    comment = json.loads(line)
                    comment_id = comment['comment_id']
                    
                    # Add category based on cluster mapping
                    if comment_id in id_to_cluster:
                        comment['category'] = id_to_cluster[comment_id]
                        matched += 1
                    else:
                        # If not in any cluster (e.g., noise points in DBSCAN)
                        comment['category'] = -1  # Use -1 for unclustered
                        unmatched.append(comment_id)
                    
                    # Write updated comment
                    outfile.write(json.dumps(comment, ensure_ascii=False) + '\n')
                    processed += 1
                    
                    if processed % 10000 == 0:
                        print(f"  Processed {processed:,} comments...")
                        
                except json.JSONDecodeError as e:
                    print(f"  Warning: Error parsing line {line_num}: {e}")
                    continue
    
    print(f"\n  Total comments processed: {processed:,}")
    print(f"  Comments with cluster assignment: {matched:,} ({matched/processed*100:.1f}%)")
    print(f"  Comments without cluster (category=-1): {len(unmatched):,} ({len(unmatched)/processed*100:.1f}%)")
    
    if unmatched and len(unmatched) <= 10:
        print(f"  Unmatched IDs: {unmatched}")
    
    return processed, matched, unmatched

def verify_output(output_file, sample_size=5):
    """Verify the output file and show sample data."""
    print(f"\nVerifying output file...")
    
    category_counts = {}
    sample_records = []
    
    with open(output_file, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if line.strip():
                record = json.loads(line)
                
                # Count categories
                category = record.get('category', None)
                if category is not None:
                    category_counts[category] = category_counts.get(category, 0) + 1
                
                # Collect samples
                if len(sample_records) < sample_size:
                    sample_records.append({
                        'id': record['comment_id'],
                        'category': category,
                        'x': round(record['x'], 2),
                        'y': round(record['y'], 2),
                        'comment': record['comment_content'][:50] + '...'
                    })
    
    # Show category distribution
    print(f"  Categories found: {len(category_counts)}")
    print(f"\n  Top categories by count:")
    sorted_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
    for cat, count in sorted_categories[:10]:
        cat_label = f"Cluster {cat}" if cat != -1 else "Unclustered"
        print(f"    {cat_label:15s}: {count:6,} comments")
    
    # Show sample records
    print(f"\n  Sample records with categories:")
    for i, record in enumerate(sample_records, 1):
        print(f"    {i}. ID: {record['id'][:30]}...")
        print(f"       Category: {record['category']}, Position: ({record['x']}, {record['y']})")
        print(f"       Comment: \"{record['comment']}\"")
    
    return category_counts

def main():
    # Set up paths
    script_dir = Path(__file__).parent
    data_dir = script_dir.parent / 'data'
    
    clusters_file = data_dir / 'umap_clusters.json'
    input_file = data_dir / 'comments_with_umap_coords.jsonl'
    output_file = data_dir / 'comments_with_categories.jsonl'
    
    # Check if input files exist
    if not clusters_file.exists():
        print(f"Error: Cluster file not found: {clusters_file}")
        print("Please run cluster_embeddings.py first to generate clusters.")
        sys.exit(1)
    
    if not input_file.exists():
        print(f"Error: Input file not found: {input_file}")
        print("Please run umap_embeddings.py first to generate UMAP coordinates.")
        sys.exit(1)
    
    # Check if output file exists
    if output_file.exists():
        response = input(f"Output file {output_file.name} already exists. Overwrite? (y/n): ")
        if response.lower() != 'y':
            print("Operation cancelled.")
            sys.exit(0)
    
    try:
        print("="*60)
        print("ADD CLUSTER CATEGORIES TO COMMENTS")
        print("="*60)
        
        # Load cluster mapping
        id_to_cluster, cluster_data = load_cluster_mapping(clusters_file)
        
        # Add categories to comments
        processed, matched, unmatched = add_categories_to_comments(
            input_file, output_file, id_to_cluster
        )
        
        # Verify output
        category_counts = verify_output(output_file)
        
        print("\n" + "="*60)
        print("✅ CATEGORY ASSIGNMENT COMPLETE")
        print("="*60)
        
        print(f"\n📊 Summary:")
        print(f"  • Input: {input_file.name}")
        print(f"  • Clusters: {clusters_file.name}")
        print(f"  • Output: {output_file.name}")
        print(f"  • Comments processed: {processed:,}")
        print(f"  • Categories assigned: {len(category_counts)}")
        
        if cluster_data.get('metadata'):
            meta = cluster_data['metadata']
            print(f"\n📝 Cluster Info:")
            print(f"  • Clustering method: {meta.get('clustering_method', 'unknown')}")
            print(f"  • Clustering space: {meta.get('clustering_space', 'unknown')}")
            print(f"  • Generated: {meta.get('generated_at', 'unknown')}")
        
        print(f"\n💡 Next steps:")
        print(f"  1. Use {output_file.name} in your visualization")
        print(f"  2. The 'category' field contains the cluster ID")
        print(f"  3. Category -1 indicates unclustered/noise points")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()