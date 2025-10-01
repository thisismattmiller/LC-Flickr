export interface Node {
  type: 'node';
  id: string;
  position_x: number;
  position_y: number;
  importance: number;
}

export interface Edge {
  type: 'edge';
  id: string | number;
  source: string;
  target: string;
  label?: string;
  position_x?: number;
  position_y?: number;
  importance?: number;
}

export interface GraphData {
  nodes: Node[];
  edges: Edge[];
}

export interface Camera {
  x: number;
  y: number;
  zoom: number;
}

export interface ViewportBounds {
  minX: number;
  maxX: number;
  minY: number;
  maxY: number;
}