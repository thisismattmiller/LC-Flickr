#!/usr/bin/env python3
"""
Render the wiki graph using ForceAtlas2 layout algorithm
"""

import networkx as nx
from fa2_modified import ForceAtlas2
import matplotlib.pyplot as plt
from pathlib import Path
import json


def main():
    # Load the GEXF file
    input_file = Path(__file__).parent.parent / 'data' / 'wiki_graph.gexf'
    print(f"Loading graph from {input_file}...")

    # print the first few lines of the file for verification
    with open(input_file, 'r', encoding='utf-8') as f:
        for _ in range(5):
            print(f.readline().strip())
    
    # Load the graph from GEXF file
    G = nx.read_gexf(input_file, version='1.2draft')
    print(f"Loaded graph with {G.number_of_nodes()} nodes and {G.number_of_edges()} edges")
    
    positions = nx.forceatlas2_layout(G, gravity=0,scaling_ratio=5, max_iter=500, dissuade_hubs=False,linlog=True)

    # forceatlas2 = ForceAtlas2(
    #                         # Behavior alternatives
    #                         outboundAttractionDistribution=True,  # Dissuade hubs
    #                         linLogMode=False,  # NOT IMPLEMENTED
    #                         adjustSizes=False,  # Prevent overlap (NOT IMPLEMENTED)
    #                         edgeWeightInfluence=0,

    #                         # Performance
    #                         jitterTolerance=1.0,  # Tolerance
    #                         barnesHutOptimize=False,
    #                         barnesHutTheta=1.2,
    #                         multiThreaded=False,  # NOT IMPLEMENTED

    #                         # Tuning
    #                         scalingRatio=0.5,
    #                         strongGravityMode=False,
    #                         gravity=0.1,

    #                         # Log
    #                         verbose=True)


    
    # # Compute positions using ForceAtlas2
    # print("Computing ForceAtlas2 layout...")
    # positions = forceatlas2.forceatlas2_networkx_layout(G, pos=None, iterations=500)
    
    # # Save positions to file
    # positions_file = Path(__file__).parent.parent / 'data' / 'wiki_graph_positions.json'
    # print(f"Saving positions to {positions_file}...")
    
    # # Convert positions dict to JSON-serializable format
    # positions_data = {node: {'x': float(pos[0]), 'y': float(pos[1])} for node, pos in positions.items()}
    
    # with open(positions_file, 'w', encoding='utf-8') as f:
    #     json.dump(positions_data, f, indent=2)
    # print(f"Saved {len(positions_data)} node positions")
    # # Draw with NetworkX


    # nx.draw(G, pos=positions)

    # print("Drawing graph with NetworkX...")
    plt.figure(figsize=(12, 12))
    
    # Color nodes differently based on type (image nodes vs entity nodes)
    node_colors = []
    node_sizes = []
    for node in G.nodes():
        if node.startswith('image_'):
            node_colors.append('red')
            node_sizes.append(30)
        else:
            node_colors.append('blue')
            node_sizes.append(20)
    
    nx.draw_networkx_nodes(G, positions, node_size=node_sizes,
                          node_color=node_colors, alpha=0.6)
    nx.draw_networkx_edges(G, positions, edge_color="gray", alpha=0.2, arrows=True, 
                          arrowsize=5, arrowstyle='->')
    
    # Optionally draw labels for some nodes (e.g., only highly connected ones)
    # labels = {}
    # for node in G.nodes():
    #     if G.degree(node) > 10:  # Only label nodes with more than 10 connections
    #         labels[node] = G.nodes[node].get('label', node)[:20]  # Truncate long labels
    # nx.draw_networkx_labels(G, positions, labels, font_size=8)
    
    # plt.axis('off')
    # plt.title(f"Wiki Graph Visualization ({G.number_of_nodes()} nodes, {G.number_of_edges()} edges)")
    
    # Save the figure
    output_file = Path(__file__).parent.parent / 'data' / 'wiki_graph_visualization.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Saved visualization to {output_file}")
    
    plt.show()
    
    # # Alternative: igraph rendering
    # print("\nAlternative igraph rendering...")
    # try:
    #     import igraph
        
    #     # Convert networkx graph to igraph
    #     # Note: igraph needs edges as tuples
    #     edges = list(G.edges())
    #     ig = igraph.Graph.TupleList(edges, directed=True)
        
    #     # Apply ForceAtlas2 layout
    #     layout = forceatlas2.forceatlas2_igraph_layout(ig, pos=None, iterations=2000)
        
    #     # Create visual style
    #     visual_style = {
    #         "vertex_size": 10,
    #         "vertex_color": "lightblue",
    #         "edge_arrow_size": 0.5,
    #         "edge_color": "gray",
    #         "layout": layout,
    #         "bbox": (800, 800),
    #         "margin": 20
    #     }
        
    #     # Plot
    #     plot = igraph.plot(ig, **visual_style)
        
    #     # Save igraph visualization
    #     output_file_ig = Path(__file__).parent.parent / 'data' / 'wiki_graph_visualization_igraph.png'
    #     plot.save(output_file_ig)
    #     print(f"Saved igraph visualization to {output_file_ig}")
        
    #     plot.show()
        
    # except ImportError:
    #     print("igraph not installed. Skipping igraph visualization.")
    #     print("Install with: pip install python-igraph")


if __name__ == '__main__':
    main()