import pandas as pd
import pyarrow.parquet as pq

# Read the parquet file
df = pd.read_parquet('data/network_data.parquet')

print(f"Total rows: {len(df)}")
print(f"Columns: {df.columns.tolist()}")
print(f"\nData types:")
print(df.dtypes)

# Count nodes and edges
nodes_df = df[df['type'] == 'node']
edges_df = df[df['type'] == 'edge']

print(f"\nNodes: {len(nodes_df)}")
print(f"Edges: {len(edges_df)}")

print(f"\nFirst 5 nodes:")
print(nodes_df.head())

print(f"\nFirst 5 edges:")
print(edges_df.head())

print(f"\nImportance range for nodes:")
if 'importance' in nodes_df.columns:
    print(f"Min: {nodes_df['importance'].min()}, Max: {nodes_df['importance'].max()}")

print(f"\nPosition ranges:")
if 'position_x' in nodes_df.columns:
    print(f"X: {nodes_df['position_x'].min()} to {nodes_df['position_x'].max()}")
    print(f"Y: {nodes_df['position_y'].min()} to {nodes_df['position_y'].max()}")