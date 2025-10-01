import { Node, Edge, GraphData } from './types';
import { asyncBufferFromUrl, parquetReadObjects } from 'hyparquet';

export class DataLoader {
  async loadParquet(url: string): Promise<GraphData> {
    try {
      // Use hyparquet to load the Parquet file
      // Try absolute path first, fallback to relative path
      let file;
      try {
        file = await asyncBufferFromUrl({ url });
      } catch (error) {
        const relativeUrl = url.startsWith('/') ? '.' + url : url;
        file = await asyncBufferFromUrl({ url: relativeUrl });
      }
      
      // Read all objects from the Parquet file
      const data = await parquetReadObjects({
        file,
        // Don't specify columns to get all columns
      });
      
      const nodes: Node[] = [];
      const edges: Edge[] = [];
      
      // Process each row
      for (const row of data) {
        if (row.type === 'node') {
          nodes.push({
            type: 'node',
            id: String(row.id),
            position_x: Number(row.position_x),
            position_y: Number(row.position_y),
            importance: Number(row.importance || 1),
          });
        } else if (row.type === 'edge') {
          edges.push({
            type: 'edge',
            id: row.id !== undefined && row.id !== null ? row.id : edges.length,
            source: String(row.source),
            target: String(row.target),
            label: row.label ? String(row.label) : undefined,
          });
        }
      }
      
      console.log(`Loaded ${nodes.length} nodes and ${edges.length} edges from Parquet file`);
      return { nodes, edges };
      
    } catch (error) {
      console.error('Error loading Parquet file:', error);
      console.log('Falling back to mock data for development');
      return this.parseMockData();
    }
  }

  private parseMockData(): GraphData {
    // Generate mock data based on your sample
    const nodes: Node[] = [
      { type: 'node', id: 'image_54025797390_Q7451311', position_x: 100, position_y: -200, importance: 10.0 },
      { type: 'node', id: 'Q1204', position_x: -150, position_y: 100, importance: 9.0 },
      { type: 'node', id: 'Q19558910', position_x: 300, position_y: 50, importance: 10.0 },
      { type: 'node', id: 'Q30', position_x: -200, position_y: -150, importance: 8.0 },
    ];

    // Add more nodes for testing with varied importance
    for (let i = 0; i < 10000; i++) {
      const angle = (i / 10000) * Math.PI * 2;
      // Create clusters at different scales
      const clusterRadius = Math.random() < 0.2 ? 100 : Math.random() < 0.5 ? 500 : Math.random() < 0.8 ? 2000 : 5000;
      const radius = clusterRadius + Math.random() * clusterRadius;
      
      // Higher importance for nodes closer to center
      const distanceFromCenter = Math.sqrt(radius);
      const baseImportance = Math.max(0, 10 - distanceFromCenter / 500);
      
      nodes.push({
        type: 'node',
        id: Math.random() > 0.5 ? `image_${i}` : `Q${i}`,
        position_x: Math.cos(angle) * radius + (Math.random() - 0.5) * 100,
        position_y: Math.sin(angle) * radius + (Math.random() - 0.5) * 100,
        importance: baseImportance + Math.random() * 3,
      });
    }

    const edges: Edge[] = [
      { type: 'edge', id: 0, source: 'image_54025797390_Q7451311', target: 'Q1204' },
      { type: 'edge', id: 1, source: 'image_54025797390_Q7451311', target: 'Q19558910' },
      { type: 'edge', id: 2, source: 'image_54025797390_Q7451311', target: 'Q30' },
    ];

    // Add more edges - create a more realistic network structure
    // Each node gets 1-5 connections, with preference for nearby nodes
    for (let i = 0; i < Math.min(5000, nodes.length); i++) {
      const sourceNode = nodes[i];
      const numConnections = Math.floor(Math.random() * 4) + 1;
      
      for (let j = 0; j < numConnections; j++) {
        // Prefer connecting to nearby nodes
        const maxDistance = 500 + Math.random() * 1000;
        const nearbyNodes = nodes.filter((n, idx) => {
          if (idx === i) return false;
          const dx = n.position_x - sourceNode.position_x;
          const dy = n.position_y - sourceNode.position_y;
          return Math.sqrt(dx * dx + dy * dy) < maxDistance;
        });
        
        if (nearbyNodes.length > 0) {
          const targetNode = nearbyNodes[Math.floor(Math.random() * nearbyNodes.length)];
          edges.push({
            type: 'edge',
            id: edges.length,
            source: sourceNode.id,
            target: targetNode.id,
          });
        }
      }
    }

    return { nodes, edges };
  }

  async loadFromFile(file: File): Promise<GraphData> {
    try {
      const arrayBuffer = await file.arrayBuffer();
      
      // Create an async buffer interface for hyparquet
      const asyncBuffer = {
        byteLength: arrayBuffer.byteLength,
        slice: async (start: number, end?: number) => {
          return arrayBuffer.slice(start, end);
        }
      };
      
      // Read all objects from the Parquet file
      const data = await parquetReadObjects({
        file: asyncBuffer,
      });
      
      const nodes: Node[] = [];
      const edges: Edge[] = [];
      
      // Process each row
      for (const row of data) {
        if (row.type === 'node') {
          nodes.push({
            type: 'node',
            id: String(row.id),
            position_x: Number(row.position_x),
            position_y: Number(row.position_y),
            importance: Number(row.importance || 1),
          });
        } else if (row.type === 'edge') {
          edges.push({
            type: 'edge',
            id: row.id !== undefined && row.id !== null ? row.id : edges.length,
            source: String(row.source),
            target: String(row.target),
            label: row.label ? String(row.label) : undefined,
          });
        }
      }
      
      return { nodes, edges };
    } catch (error) {
      console.error('Error loading Parquet file from upload:', error);
      return { nodes: [], edges: [] };
    }
  }
}