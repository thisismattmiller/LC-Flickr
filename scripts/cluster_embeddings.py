#!/usr/bin/env python3
import json
import sys
from pathlib import Path
import numpy as np
from datetime import datetime
from sklearn.cluster import KMeans, DBSCAN, AgglomerativeClustering
from sklearn.metrics import silhouette_score
from collections import Counter
import warnings
warnings.filterwarnings('ignore')

def load_umap_data(filepath):
    """Load UMAP coordinates and metadata from JSONL file."""
    print(f"Loading data from {filepath}...")
    data = []
    coordinates = []
    ids = []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            if line.strip():
                try:
                    comment = json.loads(line)
                    data.append(comment)
                    # Use UMAP coordinates (x, y)
                    coordinates.append([comment['x'], comment['y']])
                    ids.append(comment['comment_id'])
                    
                    if line_num % 10000 == 0:
                        print(f"  Loaded {line_num:,} comments...")
                except json.JSONDecodeError as e:
                    print(f"Error parsing line {line_num}: {e}")
                    continue
    
    coordinates_array = np.array(coordinates)
    print(f"Loaded {len(data):,} comments with 2D UMAP coordinates")
    print(f"  X range: [{coordinates_array[:, 0].min():.2f}, {coordinates_array[:, 0].max():.2f}]")
    print(f"  Y range: [{coordinates_array[:, 1].min():.2f}, {coordinates_array[:, 1].max():.2f}]")
    
    return data, coordinates_array, ids

def find_optimal_k(coordinates, min_k=5, max_k=30, sample_size=10000):
    """Find optimal number of clusters using elbow method and silhouette score."""
    print(f"\nFinding optimal number of clusters (testing k={min_k} to {max_k})...")
    
    # Sample data if too large
    if len(coordinates) > sample_size:
        print(f"  Sampling {sample_size:,} points for optimization...")
        indices = np.random.choice(len(coordinates), sample_size, replace=False)
        sample_coordinates = coordinates[indices]
    else:
        sample_coordinates = coordinates
    
    inertias = []
    silhouette_scores = []
    k_range = range(min_k, max_k + 1)
    
    for k in k_range:
        print(f"  Testing k={k}...", end=' ')
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = kmeans.fit_predict(sample_coordinates)
        
        inertias.append(kmeans.inertia_)
        sil_score = silhouette_score(sample_coordinates, labels, sample_size=min(5000, len(sample_coordinates)))
        silhouette_scores.append(sil_score)
        print(f"silhouette={sil_score:.3f}")
    
    # Find elbow point (maximum second derivative)
    deltas = np.diff(inertias)
    double_deltas = np.diff(deltas)
    elbow_idx = np.argmax(double_deltas) + 1  # +1 because diff reduces array size
    elbow_k = list(k_range)[elbow_idx]
    
    # Also consider best silhouette score
    best_sil_idx = np.argmax(silhouette_scores)
    best_sil_k = list(k_range)[best_sil_idx]
    
    print(f"\n  Elbow method suggests k={elbow_k}")
    print(f"  Best silhouette score at k={best_sil_k} (score={silhouette_scores[best_sil_idx]:.3f})")
    
    # Use average of both methods, biased toward silhouette score
    optimal_k = int((elbow_k + 2 * best_sil_k) / 3)
    print(f"  → Recommended k={optimal_k}")
    
    return optimal_k

def perform_clustering(coordinates, method='kmeans', n_clusters=15):
    """Perform clustering on UMAP coordinates."""
    print(f"\nPerforming {method} clustering with {n_clusters} clusters...")
    
    if method == 'kmeans':
        clusterer = KMeans(n_clusters=n_clusters, random_state=42, n_init=10, verbose=1)
        labels = clusterer.fit_predict(coordinates)
        
    elif method == 'dbscan':
        # DBSCAN for density-based clustering on 2D coordinates
        # Adjust eps based on coordinate scale
        coord_range = np.ptp(coordinates, axis=0)  # Range of coordinates
        eps = min(coord_range) * 0.02  # 2% of the smaller dimension
        clusterer = DBSCAN(eps=eps, min_samples=50, metric='euclidean', n_jobs=-1)
        labels = clusterer.fit_predict(coordinates)
        n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
        print(f"  DBSCAN found {n_clusters} clusters (and {np.sum(labels == -1)} noise points)")
        print(f"  Using eps={eps:.3f}")
        
    elif method == 'hierarchical':
        # Hierarchical clustering
        clusterer = AgglomerativeClustering(n_clusters=n_clusters)
        labels = clusterer.fit_predict(coordinates)
        
    else:
        raise ValueError(f"Unknown clustering method: {method}")
    
    return labels

def analyze_clusters(labels, ids, data):
    """Analyze clustering results and create summary."""
    print("\nAnalyzing clusters...")
    
    clusters = {}
    cluster_counts = Counter(labels)
    
    # Organize comments by cluster
    for idx, (label, comment_id) in enumerate(zip(labels, ids)):
        cluster_id = int(label)
        if cluster_id not in clusters:
            clusters[cluster_id] = {
                'cluster_id': cluster_id,
                'comment_ids': [],
                'count': 0,
                'sample_comments': []
            }
        
        clusters[cluster_id]['comment_ids'].append(comment_id)
        clusters[cluster_id]['count'] += 1
        
        # Add sample comments (first 3 from each cluster)
        if len(clusters[cluster_id]['sample_comments']) < 3:
            comment_text = data[idx].get('comment_content', '')
            if comment_text:
                # Clean up HTML and truncate
                import re
                clean_text = re.sub('<[^<]+?>', '', comment_text)  # Remove HTML tags
                clean_text = clean_text.strip()[:200]  # Truncate to 200 chars
                if clean_text:
                    clusters[cluster_id]['sample_comments'].append(clean_text)
    
    # Sort clusters by size
    sorted_clusters = sorted(clusters.values(), key=lambda x: x['count'], reverse=True)
    
    # Calculate statistics
    total_comments = sum(c['count'] for c in sorted_clusters)
    noise_points = cluster_counts.get(-1, 0)  # For DBSCAN
    valid_clusters = [c for c in sorted_clusters if c['cluster_id'] != -1]
    
    # Create summary
    summary = {
        'total_comments': total_comments,
        'total_clusters': len(valid_clusters),
        'noise_points': noise_points,
        'average_cluster_size': np.mean([c['count'] for c in valid_clusters]) if valid_clusters else 0,
        'median_cluster_size': np.median([c['count'] for c in valid_clusters]) if valid_clusters else 0,
        'largest_cluster': {
            'id': valid_clusters[0]['cluster_id'] if valid_clusters else None,
            'size': valid_clusters[0]['count'] if valid_clusters else 0,
            'percentage': (valid_clusters[0]['count'] / total_comments * 100) if valid_clusters else 0
        },
        'smallest_cluster': {
            'id': valid_clusters[-1]['cluster_id'] if valid_clusters else None,
            'size': valid_clusters[-1]['count'] if valid_clusters else 0,
            'percentage': (valid_clusters[-1]['count'] / total_comments * 100) if valid_clusters else 0
        },
        'cluster_size_distribution': []
    }
    
    # Add size distribution
    for c in valid_clusters[:10]:  # Top 10 clusters
        summary['cluster_size_distribution'].append({
            'cluster_id': c['cluster_id'],
            'size': c['count'],
            'percentage': round(c['count'] / total_comments * 100, 2)
        })
    
    return sorted_clusters, summary

def save_results(clusters, summary, output_file, method='kmeans'):
    """Save clustering results to JSON file."""
    print(f"\nSaving results to {output_file}...")
    
    output_data = {
        'metadata': {
            'generated_at': datetime.now().isoformat(),
            'source_file': 'comments_with_umap_coords.jsonl',
            'clustering_method': method,
            'clustering_space': '2D UMAP coordinates',
            'total_clusters': summary['total_clusters'],
            'total_comments': summary['total_comments']
        },
        'summary': summary,
        'clusters': clusters
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Results saved to {output_file}")

def print_summary(summary, clusters):
    """Print a nice summary of the clustering results."""
    print("\n" + "="*60)
    print("CLUSTERING SUMMARY")
    print("="*60)
    
    print(f"\n📊 Overall Statistics:")
    print(f"  • Total comments: {summary['total_comments']:,}")
    print(f"  • Total clusters: {summary['total_clusters']}")
    if summary['noise_points'] > 0:
        print(f"  • Noise points: {summary['noise_points']:,}")
    print(f"  • Average cluster size: {summary['average_cluster_size']:.0f}")
    print(f"  • Median cluster size: {summary['median_cluster_size']:.0f}")
    
    print(f"\n🏆 Largest Cluster:")
    print(f"  • Cluster {summary['largest_cluster']['id']}")
    print(f"  • Size: {summary['largest_cluster']['size']:,} comments")
    print(f"  • Percentage: {summary['largest_cluster']['percentage']:.1f}%")
    
    print(f"\n🔍 Top 10 Clusters by Size:")
    for i, dist in enumerate(summary['cluster_size_distribution'], 1):
        bar_length = int(dist['percentage'] * 0.5)  # Scale to max 50 chars
        bar = '█' * bar_length
        print(f"  {i:2d}. Cluster {dist['cluster_id']:3d}: {dist['size']:6,} ({dist['percentage']:5.1f}%) {bar}")
    
    # Show sample comments from top 3 clusters
    print(f"\n💬 Sample Comments from Top 3 Clusters:")
    for cluster in clusters[:3]:
        if cluster['cluster_id'] != -1:  # Skip noise cluster if present
            print(f"\n  Cluster {cluster['cluster_id']} ({cluster['count']:,} comments):")
            for j, comment in enumerate(cluster['sample_comments'][:2], 1):
                # Truncate to 80 chars for display
                display_comment = comment[:80] + '...' if len(comment) > 80 else comment
                print(f"    {j}. \"{display_comment}\"")

def main():
    # Set up paths
    script_dir = Path(__file__).parent
    data_dir = script_dir.parent / 'data'
    
    input_file = data_dir / 'comments_with_umap_coords.jsonl'
    output_file = data_dir / 'umap_clusters.json'
    
    # Check if input file exists
    if not input_file.exists():
        print(f"Error: Input file not found: {input_file}")
        print("Please run umap_embeddings.py first to generate UMAP coordinates.")
        sys.exit(1)
    
    try:
        # Load data
        data, coordinates, ids = load_umap_data(input_file)
        
        # Default clustering method
        method = 'kmeans'
        
        # Check for method specification
        if len(sys.argv) > 2 and sys.argv[2] in ['kmeans', 'dbscan', 'hierarchical']:
            method = sys.argv[2]
            print(f"\n📌 Using clustering method: {method}")
        
        if method == 'dbscan':
            # DBSCAN doesn't need k parameter
            labels = perform_clustering(coordinates, method='dbscan')
        else:
            # Find optimal number of clusters
            optimal_k = find_optimal_k(coordinates, min_k=10, max_k=50)
            
            # Allow override from command line
            if len(sys.argv) > 1:
                try:
                    optimal_k = int(sys.argv[1])
                    print(f"\n📌 Using user-specified k={optimal_k}")
                except ValueError:
                    if sys.argv[1] not in ['kmeans', 'dbscan', 'hierarchical']:
                        print(f"Warning: Invalid k value '{sys.argv[1]}', using optimal k={optimal_k}")
            
            # Perform clustering
            labels = perform_clustering(coordinates, method=method, n_clusters=optimal_k)
        
        # Analyze results
        clusters, summary = analyze_clusters(labels, ids, data)
        
        # Save results
        save_results(clusters, summary, output_file, method=method)
        
        # Print summary
        print_summary(summary, clusters)
        
        print(f"\n✅ Clustering complete!")
        print(f"   Results saved to: {output_file}")
        print(f"\n💡 Usage options:")
        print(f"   python {Path(__file__).name} <k>              # Specify number of clusters for kmeans")
        print(f"   python {Path(__file__).name} <k> dbscan       # Use DBSCAN clustering (k ignored)")
        print(f"   python {Path(__file__).name} <k> hierarchical # Use hierarchical clustering")
        
    except Exception as e:
        print(f"\n❌ Error during clustering: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()