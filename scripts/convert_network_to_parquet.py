#!/usr/bin/env python3
"""
Convert GEXF network file with layout positions to Parquet format for web application.
"""

import xml.etree.ElementTree as ET
import pandas as pd
import numpy as np
from pathlib import Path


def parse_gexf_to_dataframe(gexf_file):
    """
    Parse GEXF file and extract nodes and edges into a unified dataframe.

    Returns:
        DataFrame with columns: type, id, position_x, position_y, importance, source, target, label
    """
    # Register namespaces
    namespaces = {
        'gexf': 'http://gexf.net/1.3',
        'viz': 'http://gexf.net/1.3/viz',
        'gexf12': 'http://gexf.net/1.2draft',
        'viz12': 'http://www.gexf.net/1.2/viz'
    }
    
    # Parse the XML file
    tree = ET.parse(gexf_file)
    root = tree.getroot()
    
    # Detect which namespace version is being used
    if 'http://gexf.net/1.3' in root.tag:
        ns_prefix = 'gexf'
        viz_prefix = 'viz'
    else:
        ns_prefix = 'gexf12'
        viz_prefix = 'viz12'
    
    # List to store all data
    data_rows = []
    
    # Track node connections for importance calculation
    node_connections = {}
    
    # Find the graph element
    graph = root.find(f'.//{{{namespaces[ns_prefix]}}}graph')
    if graph is None:
        # Try without namespace
        graph = root.find('.//graph')
    
    # Process nodes
    nodes_elem = graph.find(f'{{{namespaces[ns_prefix]}}}nodes')
    if nodes_elem is None:
        nodes_elem = graph.find('nodes')
    
    if nodes_elem is not None:
        for node in nodes_elem.findall(f'{{{namespaces[ns_prefix]}}}node'):
            if node is None:
                node = nodes_elem.findall('node')
            
            node_id = node.get('id')
            label = node.get('label', '')
            
            # Get position from viz:position element
            position = node.find(f'{{{namespaces[viz_prefix]}}}position')
            if position is None:
                # Try without namespace
                position = node.find('.//position')
            
            if position is not None:
                x = float(position.get('x', 0))
                y = float(position.get('y', 0))
            else:
                x = 0.0
                y = 0.0
            
            # Initialize connection count for this node
            node_connections[node_id] = 0
            
            data_rows.append({
                'type': 'node',
                'id': node_id,
                'position_x': x,
                'position_y': y,
                'importance': 1,  # Will be updated later
                'source': None,
                'target': None,
                'label': None
            })
    
    # Process edges
    edges_elem = graph.find(f'{{{namespaces[ns_prefix]}}}edges')
    if edges_elem is None:
        edges_elem = graph.find('edges')
    
    if edges_elem is not None:
        for edge in edges_elem.findall(f'{{{namespaces[ns_prefix]}}}edge'):
            if edge is None:
                edge = edges_elem.findall('edge')
            
            edge_id = edge.get('id')
            source = edge.get('source')
            target = edge.get('target')
            label = edge.get('label', '')

            # Count connections for importance calculation
            if source in node_connections:
                node_connections[source] += 1
            if target in node_connections:
                node_connections[target] += 1

            data_rows.append({
                'type': 'edge',
                'id': edge_id,
                'position_x': None,
                'position_y': None,
                'importance': None,
                'source': source,
                'target': target,
                'label': label
            })
    
    # Create DataFrame
    df = pd.DataFrame(data_rows)
    
    # Calculate importance scores (1-10) based on connectivity
    if node_connections:
        # Get connection counts
        counts = list(node_connections.values())
        if len(counts) > 0 and max(counts) > 0:
            # Use percentile-based scaling for better distribution
            percentiles = np.percentile(counts, [10, 20, 30, 40, 50, 60, 70, 80, 90])
            
            # Update importance for each node
            for idx, row in df.iterrows():
                if row['type'] == 'node':
                    node_id = row['id']
                    conn_count = node_connections.get(node_id, 0)
                    
                    # Map connection count to importance score (1-10)
                    if conn_count == 0:
                        importance = 1
                    else:
                        # Find which percentile bucket this node falls into
                        importance = 1
                        for i, percentile in enumerate(percentiles):
                            if conn_count > percentile:
                                importance = i + 2  # 2-10 range
                        
                        # Ensure importance is between 1 and 10
                        importance = min(10, max(1, importance))
                    
                    df.at[idx, 'importance'] = importance
    
    return df


def main():
    # Define paths
    input_file = Path(__file__).parent.parent / 'data' / 'network_layout.gexf'
    output_file = Path(__file__).parent.parent / 'data' / 'network_data.parquet'
    
    print(f"Loading GEXF file from {input_file}...")
    
    # Check if file exists
    if not input_file.exists():
        print(f"Error: Input file {input_file} does not exist!")
        print("Looking for alternative GEXF files...")
        # Try to find any GEXF file in the data directory
        gexf_files = list(Path(__file__).parent.parent.glob('data/*.gexf'))
        if gexf_files:
            print(f"Found {len(gexf_files)} GEXF files:")
            for f in gexf_files:
                print(f"  - {f.name}")
            # Use the first one found
            input_file = gexf_files[0]
            print(f"Using {input_file.name}")
        else:
            print("No GEXF files found in data directory")
            return
    
    # Parse GEXF to DataFrame
    df = parse_gexf_to_dataframe(input_file)
    
    # Print statistics
    print(f"\nData statistics:")
    print(f"  Total rows: {len(df)}")
    print(f"  Nodes: {len(df[df['type'] == 'node'])}")
    print(f"  Edges: {len(df[df['type'] == 'edge'])}")
    
    # Show sample of the data
    print("\nSample of nodes:")
    nodes_sample = df[df['type'] == 'node'].head(3)
    print(nodes_sample.to_string())
    
    print("\nSample of edges:")
    edges_sample = df[df['type'] == 'edge'].head(3)
    print(edges_sample.to_string())
    
    # Save to Parquet
    print(f"\nSaving to Parquet file: {output_file}")
    df.to_parquet(output_file, index=False, compression='snappy')
    
    # Verify the file was created
    if output_file.exists():
        file_size = output_file.stat().st_size / 1024  # Size in KB
        print(f"Successfully created {output_file.name} ({file_size:.2f} KB)")
        
        # Read back and verify
        df_verify = pd.read_parquet(output_file)
        print(f"Verified: Parquet file contains {len(df_verify)} rows")
    else:
        print("Error: Failed to create Parquet file")


if __name__ == '__main__':
    main()