import { Node, Edge, Camera, ViewportBounds } from './types';

export class CanvasRenderer {
  private canvas: HTMLCanvasElement;
  private ctx: CanvasRenderingContext2D;
  private camera: Camera;
  private nodes: Node[] = [];
  private edges: Edge[] = [];
  private selectedNodeId: string | null = null;
  private connectedNodeIds: Set<string> = new Set();
  private nodeMap: Map<string, Node> = new Map();
  private imageCache: Map<string, HTMLImageElement> = new Map();
  private loadingImages: Set<string> = new Set();
  private imagesLoadedThisFrame: number = 0;
  private lastCameraState: string = '';
  private nodeLabels: Map<string, { label: string; instanceOf?: string }> = new Map();
  private imageLabels: Map<string, string> = new Map();
  private instanceOfColors: Map<string, string> = new Map();
  private colorPalette: string[] = [
    '#8b9dc3', '#dba3a3', '#a3c9a3', '#d4a3d4', '#a3c9d4', '#d4d4a3',
    '#b8a3d4', '#dbb8a3', '#a3d4b8', '#dba3b8', '#a3b8db', '#b8d4a3',
    '#c7a3db', '#e0c7a3', '#a3dbc7', '#dba3c7', '#a3c7e0', '#c7dba3',
    '#9fa8d4', '#d4a8a8', '#a8d4a8', '#d4a8d4', '#a8d4d4', '#d4d4a8',
    '#bca8d4', '#d4bca8', '#a8d4bc', '#d4a8bc', '#a8bcd4', '#bcd4a8',
    '#aab5cc', '#ccaab5', '#b5ccaa', '#ccaacc', '#aacccc', '#ccccaa'
  ];

  constructor(canvas: HTMLCanvasElement) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d')!;
    this.camera = { x: 0, y: 0, zoom: 1 };
    this.loadNodeLabels();
    this.loadImageLabels();
  }
  
  private async loadNodeLabels(): Promise<void> {
    try {
      const response = await fetch('/data/node_labels.json');
      const data = await response.json();
      for (const [qid, nodeData] of Object.entries(data)) {
        const info = nodeData as any;
        if (typeof info === 'string') {
          // Old format - just a string label
          this.nodeLabels.set(qid, { label: info });
        } else {
          // New format - object with label and instance_of
          this.nodeLabels.set(qid, {
            label: info.label,
            instanceOf: info.instance_of?.label
          });
        }
      }
      console.log(`Loaded ${this.nodeLabels.size} node labels`);
      
      // Build color index for instance_of values
      this.buildInstanceOfColorIndex();
    } catch (error) {
      console.error('Failed to load node labels:', error);
    }
  }
  
  private buildInstanceOfColorIndex(): void {
    // Collect all unique instance_of values
    const instanceOfValues = new Set<string>();
    
    this.nodeLabels.forEach(labelInfo => {
      if (labelInfo.instanceOf) {
        instanceOfValues.add(labelInfo.instanceOf);
      }
    });
    
    // Sort instance_of values to ensure consistent ordering
    const sortedInstanceOf = Array.from(instanceOfValues).sort();
    
    // Assign colors from palette
    sortedInstanceOf.forEach((instanceOf, index) => {
      const colorIndex = index % this.colorPalette.length;
      this.instanceOfColors.set(instanceOf, this.colorPalette[colorIndex]);
    });
    
    console.log(`Created color index for ${this.instanceOfColors.size} instance_of values`);
  }
  
  private async loadImageLabels(): Promise<void> {
    try {
      const response = await fetch('/data/image_labels.json');
      const data = await response.json();
      for (const [photoId, label] of Object.entries(data)) {
        this.imageLabels.set(photoId, label as string);
      }
      console.log(`Loaded ${this.imageLabels.size} image labels`);
    } catch (error) {
      console.error('Failed to load image labels:', error);
    }
  }

  async init(): Promise<void> {
    // Canvas 2D doesn't need async init
    return Promise.resolve();
  }

  setData(nodes: Node[], edges: Edge[]): void {
    this.nodes = nodes;
    this.edges = edges;
    this.nodeMap.clear();
    nodes.forEach(node => this.nodeMap.set(node.id, node));
  }

  private getPhotoIdFromNodeId(nodeId: string): string | null {
    // Extract photo ID from format: image_54025797390_Q7451311
    if (nodeId.startsWith('image_')) {
      const parts = nodeId.split('_');
      if (parts.length >= 2) {
        return parts[1]; // Return the middle part (photo ID)
      }
    }
    return null;
  }

  private loadImage(photoId: string): void {
    if (this.imageCache.has(photoId) || this.loadingImages.has(photoId)) {
      return;
    }

    this.loadingImages.add(photoId);
    const img = new Image();
    img.onload = () => {
      this.imageCache.set(photoId, img);
      this.loadingImages.delete(photoId);
    };
    img.onerror = () => {
      this.loadingImages.delete(photoId);
      // Could add a failed images set to avoid retrying
    };
    img.src = `https://thisismattmiller.s3.us-east-1.amazonaws.com/lc-flickr-comments-photos/${photoId}.jpg`;
  }

  setCamera(camera: Camera): void {
    this.camera = camera;
  }

  setSelection(nodeId: string | null, connectedIds: Set<string>): void {
    this.selectedNodeId = nodeId;
    this.connectedNodeIds = connectedIds;
  }

  getViewportBounds(): ViewportBounds {
    const halfWidth = this.canvas.width / (2 * this.camera.zoom);
    const halfHeight = this.canvas.height / (2 * this.camera.zoom);
    
    return {
      minX: this.camera.x - halfWidth,
      maxX: this.camera.x + halfWidth,
      minY: this.camera.y - halfHeight,
      maxY: this.camera.y + halfHeight,
    };
  }

  private getVisibleNodes(): Node[] {
    // Use screen space for more accurate filtering
    const visibleNodes: Node[] = [];
    
    for (const node of this.nodes) {
      // Convert to screen coordinates
      const screenX = (node.position_x - this.camera.x) * this.camera.zoom + this.canvas.width / 2;
      const screenY = (node.position_y - this.camera.y) * this.camera.zoom + this.canvas.height / 2;
      
      // Check if node is in screen bounds with some padding
      const padding = 100;
      if (screenX < -padding || screenX > this.canvas.width + padding ||
          screenY < -padding || screenY > this.canvas.height + padding) {
        continue;
      }
      
      // Importance-based filtering by zoom level
      const minImportance = this.camera.zoom <= 0.01 ? 10 : 
                           this.camera.zoom <= 0.05 ? 8 :
                           this.camera.zoom <= 0.1 ? 6 :
                           this.camera.zoom <= 0.5 ? 3 :
                           this.camera.zoom >= 1 ? 0 : 1;
      
      if (node.importance >= minImportance) {
        visibleNodes.push(node);
      }
    }
    
    return visibleNodes;
  }


  private getVisibleEdges(visibleNodeIds: Set<string>): Edge[] {
    const visibleEdges: Edge[] = [];
    const selectedEdges = new Set<Edge>();
    
    // Always show edges connected to selected node, regardless of zoom
    if (this.selectedNodeId) {
      for (const edge of this.edges) {
        if (edge.source === this.selectedNodeId || edge.target === this.selectedNodeId) {
          visibleEdges.push(edge);
          selectedEdges.add(edge);
        }
      }
    }
    
    // Determine max edges based on zoom level for performance
    let maxEdges = Infinity;
    if (this.camera.zoom < 0.05) {
      maxEdges = 0; // No edges when very zoomed out
    } else if (this.camera.zoom < 0.1) {
      maxEdges = 50; // Very few edges
    } else if (this.camera.zoom < 0.25) {
      maxEdges = 200;
    } else if (this.camera.zoom < 0.5) {
      maxEdges = 500;
    } else if (this.camera.zoom < 1) {
      maxEdges = 2000;
    } else if (this.camera.zoom < 2) {
      maxEdges = 5000;
    }
    // No limit at zoom >= 2
    
    let edgeCount = visibleEdges.length;
    
    // Show edges based on zoom level
    if (this.camera.zoom >= 0.5) {
      // At zoom >= 0.5, show edge if at least one connected node is visible (importance-filtered)
      for (const edge of this.edges) {
        if (edgeCount >= maxEdges) break;
        
        // Skip if already added (connected to selected node)
        if (selectedEdges.has(edge)) {
          continue;
        }
        
        // Show edge if at least one of its nodes is actually rendered (in visibleNodeIds)
        if (visibleNodeIds.has(edge.source) || visibleNodeIds.has(edge.target)) {
          visibleEdges.push(edge);
          edgeCount++;
        }
      }
    } else if (this.camera.zoom >= 0.05) {
      // When zoomed out (0.05 <= zoom < 0.5), only show edges where both nodes are visible
      for (const edge of this.edges) {
        if (edgeCount >= maxEdges) break;
        
        // Skip if already added (connected to selected node)
        if (selectedEdges.has(edge)) {
          continue;
        }
        
        if (visibleNodeIds.has(edge.source) && visibleNodeIds.has(edge.target)) {
          visibleEdges.push(edge);
          edgeCount++;
        }
      }
    }
    // When zoom < 0.05, no edges except selected node's edges
    
    return visibleEdges;
  }

  private worldToScreen(x: number, y: number): { x: number; y: number } {
    return {
      x: (x - this.camera.x) * this.camera.zoom + this.canvas.width / 2,
      y: (y - this.camera.y) * this.camera.zoom + this.canvas.height / 2,
    };
  }

  render(): { nodesVisible: number; edgesVisible: number } {
    // Check if camera has moved/zoomed
    const currentCameraState = `${this.camera.x},${this.camera.y},${this.camera.zoom}`;
    if (currentCameraState !== this.lastCameraState) {
      // Reset counter when camera changes
      this.imagesLoadedThisFrame = 0;
      this.lastCameraState = currentCameraState;
    }
    
    // Clear canvas
    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    this.ctx.fillStyle = '#f5f5f5';
    this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

    const visibleNodes = this.getVisibleNodes();
    const visibleNodeIds = new Set(visibleNodes.map(n => n.id));

    const visibleEdges = this.getVisibleEdges(visibleNodeIds);

    // Draw edges first (so they appear behind nodes)
    visibleEdges.forEach(edge => {
      const sourceNode = this.nodeMap.get(edge.source);
      const targetNode = this.nodeMap.get(edge.target);
      
      // Skip if we can't find one of the nodes
      if (!sourceNode || !targetNode) {
        return;
      }
      
      const source = this.worldToScreen(sourceNode.position_x, sourceNode.position_y);
      const target = this.worldToScreen(targetNode.position_x, targetNode.position_y);
        
        // Highlight edges connected to selected node
        if (this.selectedNodeId && 
            (edge.source === this.selectedNodeId || edge.target === this.selectedNodeId)) {
          // Draw a glow effect for selected edges
          this.ctx.save();
          this.ctx.shadowColor = '#00ff00';
          this.ctx.shadowBlur = 5;
          this.ctx.strokeStyle = '#00ff00';
          this.ctx.lineWidth = 3;
        } else {
          this.ctx.strokeStyle = 'rgba(180, 180, 180, 0.3)';
          this.ctx.lineWidth = 1;
        }
        
        this.ctx.beginPath();
        this.ctx.moveTo(source.x, source.y);
        this.ctx.lineTo(target.x, target.y);
        this.ctx.stroke();
        
        // Draw edge label along the edge line if it exists
        if (edge.label && this.camera.zoom >= 7) {
          // Calculate angle of the edge
          const dx = target.x - source.x;
          const dy = target.y - source.y;
          const edgeAngle = Math.atan2(dy, dx);
          
          // Determine if text needs to be flipped
          const needsFlip = edgeAngle > Math.PI / 2 || edgeAngle < -Math.PI / 2;
          const textAngle = needsFlip ? edgeAngle + Math.PI : edgeAngle;
          
          // Position label starting from source node (use original angle for positioning)
          const offset = 100 * Math.min(this.camera.zoom, 2); // Much larger offset from source node
          const labelX = source.x + Math.cos(edgeAngle) * offset;
          const labelY = source.y + Math.sin(edgeAngle) * offset;
          
          // Set up text styling
          this.ctx.save();
          
          // Translate to label position and rotate
          this.ctx.translate(labelX, labelY);
          this.ctx.rotate(textAngle);
          
          // Font size that increases with zoom
          const fontSize = 10 * Math.min(1.8, Math.max(1, Math.sqrt(this.camera.zoom / 2)));
          this.ctx.font = `${fontSize}px Arial`;
          
          // Add semi-transparent white background for readability
          const metrics = this.ctx.measureText(edge.label);
          const padding = 2;
          this.ctx.fillStyle = 'rgba(255, 255, 255, 0.7)';
          const rectX = needsFlip ? -metrics.width - padding : -padding;
          this.ctx.fillRect(
            rectX,
            -fontSize / 2 - padding,
            metrics.width + padding * 2,
            fontSize + padding * 2
          );
          
          // Draw the text - always use the same color regardless of selection
          this.ctx.fillStyle = 'rgba(60, 60, 60, 1)';
          this.ctx.textAlign = needsFlip ? 'right' : 'left';
          this.ctx.textBaseline = 'middle';
          this.ctx.fillText(edge.label, 0, 0);
          this.ctx.restore();
        }
        
        if (this.selectedNodeId && 
            (edge.source === this.selectedNodeId || edge.target === this.selectedNodeId)) {
          this.ctx.restore();
        }
    });

    // Draw nodes
    visibleNodes.forEach(node => {
      const pos = this.worldToScreen(node.position_x, node.position_y);
      const isImageNode = node.id.startsWith('image_');
      const photoId = isImageNode ? this.getPhotoIdFromNodeId(node.id) : null;
      
      // Only load and show photos at zoom >= 0.5
      if (isImageNode && this.camera.zoom >= 0.5 && photoId) {
        // Scale images based on zoom level
        // Different scaling for different zoom ranges
        let width: number;
        let height: number;
        
        if (this.camera.zoom >= 3) {
          // At zoom 3+, use larger scaling
          const scaleFactor = Math.min(this.camera.zoom / 3, 3); // Cap at 3x scale
          width = 60 * scaleFactor;
          height = 90 * scaleFactor;
        } else if (this.camera.zoom >= 1) {
          // Zoom 1-3: moderate size
          const scaleFactor = this.camera.zoom;
          width = 40 * scaleFactor;
          height = 60 * scaleFactor;
        } else {
          // Zoom 0.5-1: small thumbnails
          const scaleFactor = this.camera.zoom * 2;
          width = 20 * scaleFactor;
          height = 30 * scaleFactor;
        }
        
        // Check if image is loaded
        const img = this.imageCache.get(photoId);
        
        if (img) {
          // Draw the photo
          this.ctx.save();
          
          // Draw image centered at node position
          const x = pos.x - width / 2;
          const y = pos.y - height / 2;
          
          // Draw highlight effect for selected node
          if (node.id === this.selectedNodeId) {
            // Draw glowing background
            this.ctx.shadowColor = '#ffff00';
            this.ctx.shadowBlur = 15;
            this.ctx.fillStyle = '#ffff00';
            this.ctx.fillRect(x - 4, y - 4, width + 8, height + 8);
            this.ctx.shadowBlur = 0;
          }
          
          // Clip to rectangle for clean edges
          this.ctx.beginPath();
          this.ctx.rect(x, y, width, height);
          this.ctx.clip();
          
          // Draw the image
          this.ctx.drawImage(img, x, y, width, height);
          
          this.ctx.restore();
          
          // Draw border
          if (node.id === this.selectedNodeId) {
            this.ctx.strokeStyle = '#ffff00';
            this.ctx.lineWidth = 4;
          } else if (this.connectedNodeIds.has(node.id)) {
            this.ctx.strokeStyle = '#00ff00';
            this.ctx.lineWidth = 3;
          } else {
            this.ctx.strokeStyle = 'rgba(0, 0, 0, 0.5)';
            this.ctx.lineWidth = 1;
          }
          this.ctx.strokeRect(x, y, width, height);
        } else {
          // Image not loaded yet - only load if actually in viewport
          // Check if node is visible in screen space (more accurate at all zoom levels)
          const screenX = (node.position_x - this.camera.x) * this.camera.zoom + this.canvas.width / 2;
          const screenY = (node.position_y - this.camera.y) * this.camera.zoom + this.canvas.height / 2;
          
          const padding = 100; // Screen space padding
          const nodeInView = screenX >= -padding && 
                            screenX <= this.canvas.width + padding &&
                            screenY >= -padding && 
                            screenY <= this.canvas.height + padding;
          
          if (nodeInView && this.imagesLoadedThisFrame < 100) {
            // Only load image if node is actually visible in current viewport AND we haven't loaded too many
            this.loadImage(photoId);
            this.imagesLoadedThisFrame++;
          }
          
          let width: number;
          let height: number;
          
          if (this.camera.zoom >= 3) {
            const scaleFactor = Math.min(this.camera.zoom / 3, 3);
            width = 60 * scaleFactor;
            height = 90 * scaleFactor;
          } else if (this.camera.zoom >= 1) {
            const scaleFactor = this.camera.zoom;
            width = 40 * scaleFactor;
            height = 60 * scaleFactor;
          } else {
            const scaleFactor = this.camera.zoom * 2;
            width = 20 * scaleFactor;
            height = 30 * scaleFactor;
          }
          const x = pos.x - width / 2;
          const y = pos.y - height / 2;
          
          // Draw white background
          this.ctx.fillStyle = '#ffffff';
          this.ctx.fillRect(x, y, width, height);
          
          // Draw dotted border for loading state
          this.ctx.save();
          this.ctx.setLineDash([2, 4]);
          
          if (node.id === this.selectedNodeId) {
            this.ctx.strokeStyle = '#ffff00';
            this.ctx.lineWidth = 3;
          } else if (this.connectedNodeIds.has(node.id)) {
            this.ctx.strokeStyle = '#00ff00';
            this.ctx.lineWidth = 2;
          } else {
            this.ctx.strokeStyle = 'rgba(0, 0, 0, 0.4)';
            this.ctx.lineWidth = 1.5;
          }
          
          this.ctx.strokeRect(x, y, width, height);
          this.ctx.restore();
        }
      } else if (isImageNode) {
        // Draw dotted rectangle for image nodes when photos aren't shown
        const width = 20 * this.camera.zoom;
        const height = 30 * this.camera.zoom;
        const x = pos.x - width / 2;
        const y = pos.y - height / 2;
        
        // Draw white background
        this.ctx.fillStyle = '#ffffff';
        this.ctx.fillRect(x, y, width, height);
        
        // Draw dotted border with more dots
        this.ctx.save();
        this.ctx.setLineDash([1, 3]);
        
        if (node.id === this.selectedNodeId) {
          this.ctx.strokeStyle = '#ffff00';
          this.ctx.lineWidth = 2;
        } else if (this.connectedNodeIds.has(node.id)) {
          this.ctx.strokeStyle = '#00ff00';
          this.ctx.lineWidth = 1.5;
        } else {
          this.ctx.strokeStyle = 'rgba(0, 0, 0, 0.3)';
          this.ctx.lineWidth = 1;
        }
        
        this.ctx.strokeRect(x, y, width, height);
        this.ctx.restore();
      } else {
        // Draw Q nodes as colored circles based on instance_of
        const size = Math.sqrt(node.importance) * 5 * Math.min(this.camera.zoom, 2);
          
          let color: string;
          if (node.id === this.selectedNodeId) {
            color = '#ffff00'; // Yellow for selected
          } else if (this.connectedNodeIds.has(node.id)) {
            color = '#00ff00'; // Green for connected
          } else {
            // Get color based on instance_of value
            const labelInfo = this.nodeLabels.get(node.id);
            if (labelInfo?.instanceOf && this.instanceOfColors.has(labelInfo.instanceOf)) {
              color = this.instanceOfColors.get(labelInfo.instanceOf)!;
            } else {
              color = '#999999'; // Default gray for nodes without instance_of
            }
          }
          
          // Draw node circle
          this.ctx.fillStyle = color;
          this.ctx.strokeStyle = 'rgba(0, 0, 0, 0.5)';
          this.ctx.lineWidth = 1;
          
          this.ctx.beginPath();
          this.ctx.arc(pos.x, pos.y, size, 0, Math.PI * 2);
          this.ctx.fill();
          this.ctx.stroke();
          
          // Draw node label if zoomed in enough
          if (this.camera.zoom >= 1) {
            // Scale font size with zoom, but cap the growth
            const fontSize = Math.min(10 + (this.camera.zoom - 1) * 2, 18);
            this.ctx.font = `bold ${fontSize}px sans-serif`;
            this.ctx.textAlign = 'center';
            
            // Get label info
            const labelInfo = this.nodeLabels.get(node.id);
            const displayLabel = labelInfo?.label || node.id;
            const label = displayLabel.length > 25 ? displayLabel.substring(0, 25) + '...' : displayLabel;
            
            // Draw main label
            this.ctx.textBaseline = 'middle';
            let labelY = pos.y;
            
            // If we have instance_of, adjust position to make room
            if (labelInfo?.instanceOf) {
              labelY = pos.y - fontSize * 0.6;
            }
            
            // Draw black stroke (outline) for main label
            this.ctx.strokeStyle = 'black';
            this.ctx.lineWidth = 3;
            this.ctx.lineJoin = 'round';
            this.ctx.strokeText(label, pos.x, labelY);
            
            // Draw white fill for main label
            this.ctx.fillStyle = 'white';
            this.ctx.fillText(label, pos.x, labelY);
            
            // Draw instance_of label if it exists
            if (labelInfo?.instanceOf) {
              const instanceFontSize = fontSize * 0.8;
              this.ctx.font = `${instanceFontSize}px sans-serif`;
              const instanceLabel = `(${labelInfo.instanceOf})`;
              const instanceY = pos.y + fontSize * 0.6;
              
              // Draw black stroke for instance label
              this.ctx.strokeStyle = 'black';
              this.ctx.lineWidth = 2;
              this.ctx.strokeText(instanceLabel, pos.x, instanceY);
              
              // Draw white fill for instance label
              this.ctx.fillStyle = 'white';
              this.ctx.fillText(instanceLabel, pos.x, instanceY);
            }
          }
      }
    });

    return {
      nodesVisible: visibleNodes.length,
      edgesVisible: visibleEdges.length,
    };
  }

  resize(width: number, height: number): void {
    this.canvas.width = width;
    this.canvas.height = height;
  }

  screenToWorld(screenX: number, screenY: number): { x: number; y: number } {
    const x = (screenX - this.canvas.width / 2) / this.camera.zoom + this.camera.x;
    const y = (screenY - this.canvas.height / 2) / this.camera.zoom + this.camera.y;
    return { x, y };
  }

  getNodeLabel(nodeId: string): string {
    // Don't use labels for image nodes
    if (nodeId.startsWith('image_')) {
      return nodeId;
    }
    // Return the label if we have it, otherwise return the Q ID
    const labelInfo = this.nodeLabels.get(nodeId);
    return labelInfo?.label || nodeId;
  }
  
  getNodeInstanceOf(nodeId: string): string | undefined {
    if (nodeId.startsWith('image_')) {
      return undefined;
    }
    return this.nodeLabels.get(nodeId)?.instanceOf;
  }
  
  getImageLabel(nodeId: string): string | undefined {
    if (!nodeId.startsWith('image_')) {
      return undefined;
    }
    // Extract photo ID from format: image_54025797390_Q7451311
    const parts = nodeId.split('_');
    if (parts.length >= 2) {
      const photoId = parts[1];
      return this.imageLabels.get(photoId);
    }
    return undefined;
  }
  
  getConnectedImageNodes(qNodeId: string): Array<{ nodeId: string; photoId: string; label: string; edgeLabel: string }> {
    const connectedImages: Array<{ nodeId: string; photoId: string; label: string; edgeLabel: string }> = [];
    
    // Find all edges where the Q node is the target
    for (const edge of this.edges) {
      if (edge.target === qNodeId && edge.source.startsWith('image_')) {
        const parts = edge.source.split('_');
        if (parts.length >= 2) {
          const photoId = parts[1];
          const label = this.imageLabels.get(photoId) || edge.source;
          connectedImages.push({
            nodeId: edge.source,
            photoId: photoId,
            label: label,
            edgeLabel: edge.label || 'connected to'
          });
        }
      }
    }
    
    return connectedImages;
  }
  
  getImageRelationships(nodeId: string): { linkedQ: string; linkedQLabel: string; relationships: Array<{ edgeLabel: string; targetQ: string; targetQLabel: string }> } | undefined {
    if (!nodeId.startsWith('image_')) {
      return undefined;
    }
    
    // Extract the linked Q ID from format: image_54025797390_Q7451311
    const parts = nodeId.split('_');
    if (parts.length < 3) {
      return undefined;
    }
    
    const linkedQId = parts[2];
    const linkedQLabel = this.nodeLabels.get(linkedQId)?.label || linkedQId;
    
    // Find all edges from this image node
    const relationships: Array<{ edgeLabel: string; targetQ: string; targetQLabel: string }> = [];
    
    for (const edge of this.edges) {
      if (edge.source === nodeId && edge.target !== linkedQId) {
        const targetLabel = this.nodeLabels.get(edge.target)?.label || edge.target;
        relationships.push({
          edgeLabel: edge.label || 'connected to',
          targetQ: edge.target,
          targetQLabel: targetLabel
        });
      }
    }
    
    return {
      linkedQ: linkedQId,
      linkedQLabel: linkedQLabel,
      relationships: relationships
    };
  }
  
  findNodeAt(worldX: number, worldY: number): Node | null {
    const visibleNodes = this.getVisibleNodes();
    
    // Build a list of nodes with their hit areas and z-order
    const nodeHits: { node: Node; zOrder: number }[] = [];
    
    visibleNodes.forEach((node, index) => {
      const isImageNode = node.id.startsWith('image_');
      
      if (isImageNode) {
        // Check rectangular bounds for image nodes
        let width: number, height: number;
        if (this.camera.zoom >= 0.5) {
          // Use same scaling as rendering
          if (this.camera.zoom >= 3) {
            const scaleFactor = Math.min(this.camera.zoom / 3, 3);
            width = 60 * scaleFactor;
            height = 90 * scaleFactor;
          } else if (this.camera.zoom >= 1) {
            const scaleFactor = this.camera.zoom;
            width = 40 * scaleFactor;
            height = 60 * scaleFactor;
          } else {
            const scaleFactor = this.camera.zoom * 2;
            width = 20 * scaleFactor;
            height = 30 * scaleFactor;
          }
        } else {
          // Small rectangles when zoomed out
          width = 20 / this.camera.zoom;
          height = 30 / this.camera.zoom;
        }
        
        const halfWidth = width / 2;
        const halfHeight = height / 2;
        
        if (worldX >= node.position_x - halfWidth &&
            worldX <= node.position_x + halfWidth &&
            worldY >= node.position_y - halfHeight &&
            worldY <= node.position_y + halfHeight) {
          // For high zoom levels, prioritize nodes closer to click point
          if (this.camera.zoom >= 3) {
            const dx = worldX - node.position_x;
            const dy = worldY - node.position_y;
            const distance = Math.sqrt(dx * dx + dy * dy);
            // Use negative distance as z-order so closer nodes have higher priority
            nodeHits.push({ node, zOrder: -distance });
          } else {
            // Use render order for lower zoom levels
            nodeHits.push({ node, zOrder: index });
          }
        }
      } else {
        // Check circular bounds for Q nodes
        const size = Math.sqrt(node.importance) * 5;
        const dx = worldX - node.position_x;
        const dy = worldY - node.position_y;
        const distance = Math.sqrt(dx * dx + dy * dy);
        
        if (distance <= size) {
          if (this.camera.zoom >= 3) {
            nodeHits.push({ node, zOrder: -distance });
          } else {
            nodeHits.push({ node, zOrder: index });
          }
        }
      }
    });
    
    // Sort by z-order and return the topmost node
    if (nodeHits.length > 0) {
      nodeHits.sort((a, b) => b.zOrder - a.zOrder);
      return nodeHits[0].node;
    }
    
    return null;
  }
}