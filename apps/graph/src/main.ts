import { CanvasRenderer } from './canvas-renderer';
import { DataLoader } from './data-loader';
import { CameraControls } from './camera-controls';
import { Node, Edge, Camera } from './types';

class GraphVisualization {
  private renderer!: CanvasRenderer;
  private dataLoader: DataLoader;
  private cameraControls!: CameraControls;
  private canvas: HTMLCanvasElement;
  private tooltip: HTMLElement;
  private imagePanel: HTMLElement;
  private imagePanelTitle: HTMLElement;
  private imageGrid: HTMLElement;
  private imageTooltip: HTMLElement;
  private searchModal: HTMLElement;
  private searchInput: HTMLInputElement;
  private searchResults: HTMLElement;
  private nodes: Node[] = [];
  private edges: Edge[] = [];
  private selectedNodeId: string | null = null;
  private connectedNodeIds: Set<string> = new Set();
  private animationFrameId: number | null = null;
  private currentNodePosition: { x: number; y: number } | null = null;
  private searchDebounceTimer: number | null = null;

  constructor() {
    this.canvas = document.getElementById('canvas') as HTMLCanvasElement;
    this.tooltip = document.getElementById('tooltip') as HTMLElement;
    this.imagePanel = document.getElementById('image-panel') as HTMLElement;
    this.imagePanelTitle = document.getElementById('image-panel-title') as HTMLElement;
    this.imageGrid = document.getElementById('image-grid') as HTMLElement;
    this.imageTooltip = document.getElementById('image-tooltip') as HTMLElement;
    this.searchModal = document.getElementById('search-modal') as HTMLElement;
    this.searchInput = document.getElementById('search-input') as HTMLInputElement;
    this.searchResults = document.getElementById('search-results') as HTMLElement;
    this.dataLoader = new DataLoader();
    
    // Always show loading prompt
    this.showLoadingPrompt();
  }
  
  private isMobileDevice(): boolean {
    // Check for touch capability and screen size
    const hasTouch = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
    const isSmallScreen = window.innerWidth < 768 || window.innerHeight < 600;
    
    // Check user agent for mobile devices
    const mobileRegex = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i;
    const isMobileUA = mobileRegex.test(navigator.userAgent);
    
    return (hasTouch && isSmallScreen) || isMobileUA;
  }
  
  private showLoadingPrompt(): void {
    const loadingModal = document.getElementById('loading-prompt');
    if (loadingModal) {
      // Add mobile class if on mobile device
      if (this.isMobileDevice()) {
        loadingModal.classList.add('mobile');
      }
      
      loadingModal.classList.add('show');
      
      // Set up button handler
      const loadButton = document.getElementById('load-viz');
      
      if (loadButton) {
        loadButton.addEventListener('click', () => {
          loadingModal.classList.remove('show');
          this.init();
        });
      }
    }
  }

  private async init(): Promise<void> {
    try {
      // Set canvas size
      this.resizeCanvas();
      window.addEventListener('resize', () => this.resizeCanvas());

      // Initialize Canvas renderer
      this.renderer = new CanvasRenderer(this.canvas);
      await this.renderer.init();

      // Initialize camera controls
      const initialCamera: Camera = { x: 0, y: 0, zoom: 2 };
      this.cameraControls = new CameraControls(this.canvas, initialCamera);

      // Load data
      await this.loadData();

      // Set up interaction handlers
      this.setupInteractions();
      this.setupImagePanel();
      this.setupSearch();
      
      // Check for URL parameters to auto-zoom
      this.handleUrlParameters();

      // Hide loading indicator
      const loading = document.getElementById('loading');
      if (loading) loading.style.display = 'none';

      // Start render loop
      this.startRenderLoop();
    } catch (error) {
      console.error('Failed to initialize:', error);
      const loading = document.getElementById('loading');
      if (loading) {
        loading.textContent = 'Failed to initialize. Please refresh the page.';
      }
    }
  }

  private async loadData(): Promise<void> {
    try {
      // Load the actual Parquet file from the data directory
      const data = await this.dataLoader.loadParquet('/data/network_data.parquet');
      this.nodes = data.nodes;
      this.edges = data.edges;
      this.renderer.setData(this.nodes, this.edges);
      
      console.log(`Loaded ${this.nodes.length} nodes and ${this.edges.length} edges`);
      
      // If we have nodes, center the camera on the data
      if (this.nodes.length > 0) {
        // Center camera at origin where most of the data is
        this.cameraControls.setCamera({ x: 0, y: 0, zoom: 0.1 });
      }
    } catch (error) {
      console.error('Error loading data:', error);
    }
  }

  private resizeCanvas(): void {
    this.canvas.width = window.innerWidth;
    this.canvas.height = window.innerHeight;
    
    if (this.renderer) {
      this.renderer.resize(this.canvas.width, this.canvas.height);
    }
  }

  private setupInteractions(): void {
    // Mouse move for hover tooltips
    this.canvas.addEventListener('mousemove', (e) => {
      const rect = this.canvas.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      
      const worldPos = this.renderer.screenToWorld(x, y);
      const node = this.renderer.findNodeAt(worldPos.x, worldPos.y);
      
      if (node) {
        this.showTooltip(node, e.clientX, e.clientY);
        this.canvas.style.cursor = 'pointer';
      } else {
        this.hideTooltip();
        if (!this.cameraControls['isDragging']) {
          this.canvas.style.cursor = 'grab';
        }
      }
    });

    // Click for selection
    this.canvas.addEventListener('click', (e) => {
      const rect = this.canvas.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      
      const worldPos = this.renderer.screenToWorld(x, y);
      const node = this.renderer.findNodeAt(worldPos.x, worldPos.y);
      
      if (node) {
        this.selectNode(node);
      } else {
        this.clearSelection();
      }
    });

    // Mouse leave to hide tooltip
    this.canvas.addEventListener('mouseleave', () => {
      this.hideTooltip();
    });
  }

  private showTooltip(node: Node, x: number, y: number): void {
    const isImageNode = node.id.startsWith('image_');
    
    if (isImageNode) {
      // For image nodes, show the image name and relationships
      const imageLabel = this.renderer.getImageLabel(node.id);
      const imageInfo = this.renderer.getImageRelationships(node.id);
      
      // Build tooltip content with proper HTML line breaks
      let tooltipLines: string[] = [];
      
      // Add image name, removing (LOC) suffix if present
      let imageName = imageLabel || node.id;
      imageName = imageName.replace(/\s*\(LOC\)\s*$/i, '').trim();
      tooltipLines.push(imageName);
      
      if (imageInfo) {
        // Add linked Q node info
        tooltipLines.push('');
        tooltipLines.push(`Linked to ${imageInfo.linkedQ}: ${imageInfo.linkedQLabel}`);
        
        // Add relationships
        if (imageInfo.relationships.length > 0) {
          tooltipLines.push('');
          tooltipLines.push('Relationships:');
          for (const rel of imageInfo.relationships.slice(0, 10)) { // Increased to 10 relationships
            tooltipLines.push(`${rel.edgeLabel} → ${rel.targetQLabel}`);
          }
          if (imageInfo.relationships.length > 10) {
            tooltipLines.push(`... and ${imageInfo.relationships.length - 10} more`);
          }
        }
      }
      
      // Set innerHTML instead of textContent to preserve line breaks
      this.tooltip.innerHTML = tooltipLines.join('<br>');
    } else {
      // For Q nodes, show the label, instance_of (if exists), and the Q ID
      const label = this.renderer.getNodeLabel(node.id);
      const instanceOf = this.renderer.getNodeInstanceOf(node.id);
      
      let tooltipLines: string[] = [];
      
      if (label !== node.id) {
        tooltipLines.push(label);
      }
      if (instanceOf) {
        tooltipLines.push(`(${instanceOf})`);
      }
      tooltipLines.push(`ID: ${node.id}`);
      
      this.tooltip.innerHTML = tooltipLines.join('<br>');
    }
    this.tooltip.style.display = 'block';
    
    // Position tooltip near cursor
    const tooltipRect = this.tooltip.getBoundingClientRect();
    const offsetX = 10;
    const offsetY = 10;
    
    let left = x + offsetX;
    let top = y + offsetY;
    
    // Keep tooltip within viewport
    if (left + tooltipRect.width > window.innerWidth) {
      left = x - tooltipRect.width - offsetX;
    }
    if (top + tooltipRect.height > window.innerHeight) {
      top = y - tooltipRect.height - offsetY;
    }
    
    this.tooltip.style.left = `${left}px`;
    this.tooltip.style.top = `${top}px`;
  }

  private hideTooltip(): void {
    this.tooltip.style.display = 'none';
  }

  private selectNode(node: Node): void {
    this.selectedNodeId = node.id;
    this.connectedNodeIds.clear();
    this.currentNodePosition = { x: node.position_x, y: node.position_y };
    
    // Find all connected nodes
    for (const edge of this.edges) {
      if (edge.source === node.id) {
        this.connectedNodeIds.add(edge.target);
      } else if (edge.target === node.id) {
        this.connectedNodeIds.add(edge.source);
      }
    }
    
    this.renderer.setSelection(this.selectedNodeId, this.connectedNodeIds);
    console.log(`Selected node: ${node.id}, Connected nodes: ${this.connectedNodeIds.size}`);
    
    // Show appropriate panel based on node type
    if (!node.id.startsWith('image_')) {
      this.showImagePanel(node);
    } else {
      this.showImageRelationshipsPanel(node);
    }
  }

  private clearSelection(): void {
    this.selectedNodeId = null;
    this.connectedNodeIds.clear();
    this.currentNodePosition = null;
    this.renderer.setSelection(null, this.connectedNodeIds);
    this.hideImagePanel();
  }

  private startRenderLoop(): void {
    const render = () => {
      // Update camera
      const camera = this.cameraControls.getCamera();
      this.renderer.setCamera(camera);
      
      // Render
      this.renderer.render();

      // Update UI
      this.updateStats();
      
      // Continue loop
      this.animationFrameId = requestAnimationFrame(render);
    };
    
    render();
  }

  private updateStats(): void {
    // Stats UI has been removed, keeping method for compatibility
  }

  private setupImagePanel(): void {
    // Close button handler
    const closeBtn = document.getElementById('image-panel-close');
    if (closeBtn) {
      closeBtn.addEventListener('click', () => this.hideImagePanel());
    }
    
    // Copy link button handler
    const copyLinkBtn = document.getElementById('copy-link-btn');
    if (copyLinkBtn) {
      copyLinkBtn.addEventListener('click', () => this.copyNodeLink());
    }
  }
  
  private showImagePanel(node: Node): void {
    // Store the node position for copy link functionality
    this.currentNodePosition = { x: node.position_x, y: node.position_y };
    
    // Get connected images
    const connectedImages = this.renderer.getConnectedImageNodes(node.id);
    
    // Update panel title
    const label = this.renderer.getNodeLabel(node.id);
    this.imagePanelTitle.textContent = `Images for: ${label}`;
    
    // Add Q ID with Wikidata link in subtitle
    const subtitleElement = document.getElementById('image-panel-subtitle');
    if (subtitleElement) {
      const qId = node.id.replace('Q', '');
      subtitleElement.innerHTML = `<a href="https://www.wikidata.org/wiki/Q${qId}" target="_blank">${node.id}</a>`;
    }
    
    // Clear and populate image grid
    this.imageGrid.innerHTML = '';
    
    connectedImages.forEach(imageInfo => {
      const imageItem = document.createElement('div');
      imageItem.className = 'image-item';
      
      // Create photo container
      const photoContainer = document.createElement('div');
      photoContainer.className = 'image-item-photo';
      photoContainer.dataset.photoId = imageInfo.photoId;
      photoContainer.dataset.label = imageInfo.label.replace(/\s*\(LOC\)\s*$/i, '').trim();
      
      const img = document.createElement('img');
      img.src = `https://thisismattmiller.s3.us-east-1.amazonaws.com/lc-flickr-comments-photos/${imageInfo.photoId}.jpg`;
      img.alt = imageInfo.label;
      img.loading = 'lazy';
      
      // Click handler to open Flickr page
      photoContainer.addEventListener('click', () => {
        window.open(`https://www.flickr.com/photos/library_of_congress/${imageInfo.photoId}/`, '_blank');
      });
      
      // Hover handlers for tooltip
      photoContainer.addEventListener('mouseenter', (e) => {
        const target = e.currentTarget as HTMLElement;
        const label = target.dataset.label || '';
        this.imageTooltip.textContent = label;
        this.imageTooltip.style.display = 'block';
      });
      
      photoContainer.addEventListener('mousemove', (e) => {
        this.imageTooltip.style.left = `${e.clientX + 10}px`;
        this.imageTooltip.style.top = `${e.clientY + 10}px`;
      });
      
      photoContainer.addEventListener('mouseleave', () => {
        this.imageTooltip.style.display = 'none';
      });
      
      photoContainer.appendChild(img);
      imageItem.appendChild(photoContainer);
      
      // Extract Q ID from image node ID and add label
      // Image node ID format: image_54025797390_Q7451311
      const parts = imageInfo.nodeId.split('_');
      if (parts.length >= 3 && parts[2].startsWith('Q')) {
        const qId = parts[2];
        const qLabel = this.renderer.getNodeLabel(qId);
        
        const labelDiv = document.createElement('div');
        labelDiv.className = 'image-item-label';
        
        const qIdNum = qId.replace('Q', '');
        labelDiv.innerHTML = `
          <a href="https://www.wikidata.org/wiki/Q${qIdNum}" target="_blank">${qLabel}</a>
          <div style="font-size: 11px; color: #666; margin-top: 2px; font-style: italic;">${imageInfo.edgeLabel}</div>
        `;
        
        imageItem.appendChild(labelDiv);
      }
      
      this.imageGrid.appendChild(imageItem);
    });
    
    // Show panel
    this.imagePanel.classList.add('open');
  }
  
  private hideImagePanel(): void {
    this.imagePanel.classList.remove('open');
    this.imageTooltip.style.display = 'none';
  }
  
  private showImageRelationshipsPanel(node: Node): void {
    // Store the node position for copy link functionality  
    this.currentNodePosition = { x: node.position_x, y: node.position_y };
    
    // Extract photo ID and Q ID from image node ID
    // Format: image_54025797390_Q7451311
    const parts = node.id.split('_');
    if (parts.length < 3) return;
    
    const photoId = parts[1];
    const linkedQId = parts[2];
    
    // Get image label and linked Q label
    const imageLabel = this.renderer.getImageLabel(node.id) || node.id;
    const cleanImageLabel = imageLabel.replace(/\s*\(LOC\)\s*$/i, '').trim();
    const linkedQLabel = this.renderer.getNodeLabel(linkedQId);
    
    // Update panel title
    this.imagePanelTitle.textContent = 'Image Details';
    
    // Add subtitle with Flickr and Wikidata links
    const subtitleElement = document.getElementById('image-panel-subtitle');
    if (subtitleElement) {
      const qIdNum = linkedQId.replace('Q', '');
      subtitleElement.innerHTML = `
        <a href="https://www.flickr.com/photos/library_of_congress/${photoId}/" target="_blank">View on Flickr</a> | 
        Linked to: <a href="https://www.wikidata.org/wiki/Q${qIdNum}" target="_blank">${linkedQLabel} (${linkedQId})</a>
      `;
    }
    
    // Clear image grid and populate with relationships
    this.imageGrid.innerHTML = '';
    
    // Create a container for the image title and relationships
    const contentContainer = document.createElement('div');
    contentContainer.style.cssText = 'display: flex; flex-direction: column; gap: 16px;';
    
    // Add image title section
    const titleSection = document.createElement('div');
    titleSection.style.cssText = 'background: #f0f4f8; padding: 12px; border-radius: 6px; border-left: 3px solid #2c5aa0;';
    
    const titleLabel = document.createElement('div');
    titleLabel.style.cssText = 'font-size: 12px; color: #666; margin-bottom: 4px; font-weight: 500;';
    titleLabel.textContent = 'Image Title';
    
    const titleContent = document.createElement('div');
    titleContent.style.cssText = 'font-size: 15px; color: #222; line-height: 1.4;';
    titleContent.textContent = cleanImageLabel;
    
    titleSection.appendChild(titleLabel);
    titleSection.appendChild(titleContent);
    contentContainer.appendChild(titleSection);
    
    // Create a relationships list
    const relationshipsContainer = document.createElement('div');
    relationshipsContainer.style.cssText = 'display: flex; flex-direction: column; gap: 12px;';
    
    // Get all relationships for this image
    const imageInfo = this.renderer.getImageRelationships(node.id);
    
    if (imageInfo && imageInfo.relationships.length > 0) {
      // Group relationships by edge label
      const groupedRelationships = new Map<string, Array<{targetQ: string; targetQLabel: string}>>();
      
      for (const rel of imageInfo.relationships) {
        if (!groupedRelationships.has(rel.edgeLabel)) {
          groupedRelationships.set(rel.edgeLabel, []);
        }
        groupedRelationships.get(rel.edgeLabel)!.push({
          targetQ: rel.targetQ,
          targetQLabel: rel.targetQLabel
        });
      }
      
      // Display grouped relationships
      groupedRelationships.forEach((targets, edgeLabel) => {
        const relationshipGroup = document.createElement('div');
        relationshipGroup.style.cssText = 'background: #f8f8f8; padding: 12px; border-radius: 6px; border-left: 3px solid #0066cc;';
        
        const labelDiv = document.createElement('div');
        labelDiv.style.cssText = 'font-weight: bold; margin-bottom: 8px; color: #333;';
        labelDiv.textContent = edgeLabel;
        relationshipGroup.appendChild(labelDiv);
        
        const targetsList = document.createElement('div');
        targetsList.style.cssText = 'display: flex; flex-direction: column; gap: 4px;';
        
        targets.forEach(target => {
          const targetDiv = document.createElement('div');
          targetDiv.style.cssText = 'font-size: 14px;';
          
          const qIdNum = target.targetQ.replace('Q', '');
          targetDiv.innerHTML = `
            <a href="https://www.wikidata.org/wiki/Q${qIdNum}" target="_blank" style="color: #0066cc; text-decoration: none;">
              ${target.targetQLabel} <span style="color: #666; font-size: 12px;">(${target.targetQ})</span>
            </a>
          `;
          
          targetsList.appendChild(targetDiv);
        });
        
        relationshipGroup.appendChild(targetsList);
        relationshipsContainer.appendChild(relationshipGroup);
      });
    } else {
      const noRelationships = document.createElement('div');
      noRelationships.style.cssText = 'padding: 20px; text-align: center; color: #666;';
      noRelationships.textContent = 'No relationships found for this image.';
      relationshipsContainer.appendChild(noRelationships);
    }
    
    contentContainer.appendChild(relationshipsContainer);
    this.imageGrid.appendChild(contentContainer);
    
    // Show panel
    this.imagePanel.classList.add('open');
  }
  
  private copyNodeLink(): void {
    if (!this.selectedNodeId || !this.currentNodePosition) return;
    
    const url = new URL(window.location.href);
    url.searchParams.set('node', this.selectedNodeId);
    url.searchParams.set('x', this.currentNodePosition.x.toFixed(2));
    url.searchParams.set('y', this.currentNodePosition.y.toFixed(2));
    url.searchParams.set('zoom', '5'); // Good zoom level to see node detail
    
    navigator.clipboard.writeText(url.toString()).then(() => {
      const copyBtn = document.getElementById('copy-link-btn');
      if (copyBtn) {
        copyBtn.classList.add('copied');
        setTimeout(() => {
          copyBtn.classList.remove('copied');
        }, 2000);
      }
    }).catch(err => {
      console.error('Failed to copy link:', err);
    });
  }
  
  private handleUrlParameters(): void {
    const params = new URLSearchParams(window.location.search);
    const nodeId = params.get('node');
    const x = params.get('x');
    const y = params.get('y');
    const zoom = params.get('zoom');
    
    if (nodeId && x && y) {
      // Find the node
      const node = this.nodes.find(n => n.id === nodeId);
      if (node) {
        // Set camera to focus on the node
        const targetZoom = zoom ? parseFloat(zoom) : 5;
        this.cameraControls.setCamera({
          x: parseFloat(x),
          y: parseFloat(y),
          zoom: targetZoom
        });
        
        // Select the node after a short delay to ensure rendering is complete
        setTimeout(() => {
          this.selectNode(node);
        }, 500);
      }
    }
  }
  
  private setupSearch(): void {
    // Keyboard shortcut for search
    document.addEventListener('keydown', (e) => {
      // Check for Cmd+F (Mac) or Ctrl+F (Windows/Linux)
      if ((e.metaKey || e.ctrlKey) && e.key === 'f') {
        e.preventDefault();
        this.openSearch();
      }
      // Close on Escape
      if (e.key === 'Escape' && this.searchModal.classList.contains('open')) {
        this.closeSearch();
      }
    });
    
    // Close button
    const closeBtn = document.getElementById('search-close');
    if (closeBtn) {
      closeBtn.addEventListener('click', () => this.closeSearch());
    }
    
    // Search input handler
    this.searchInput.addEventListener('input', () => {
      if (this.searchDebounceTimer) {
        clearTimeout(this.searchDebounceTimer);
      }
      this.searchDebounceTimer = window.setTimeout(() => {
        this.performSearch(this.searchInput.value);
      }, 200);
    });
  }
  
  private openSearch(): void {
    this.searchModal.classList.add('open');
    this.searchInput.focus();
    this.searchInput.select();
  }
  
  private closeSearch(): void {
    this.searchModal.classList.remove('open');
    this.searchInput.value = '';
    this.searchResults.innerHTML = '<div id="search-status">Type to search...</div>';
  }
  
  private performSearch(query: string): void {
    if (!query.trim()) {
      this.searchResults.innerHTML = '<div id="search-status">Type to search...</div>';
      return;
    }
    
    const lowerQuery = query.toLowerCase();
    const results: Array<{ node: Node; label: string; isImage: boolean }> = [];
    
    // Search through all nodes
    for (const node of this.nodes) {
      const isImage = node.id.startsWith('image_');
      let label = '';

      if (isImage) {
        // Get image label
        label = this.renderer.getImageLabel(node.id) || node.id;
        // Remove (LOC) suffix for cleaner display
        label = label.replace(/\s*\(LOC\)\s*$/i, '').trim();
      } else {
        // Get Q node label
        label = this.renderer.getNodeLabel(node.id);
      }
      
      // Check if label or ID matches the query
      if (label.toLowerCase().includes(lowerQuery) || 
          node.id.toLowerCase().includes(lowerQuery)) {
        results.push({ node, label, isImage });
      }
      
      // Limit results to 50 for performance
      if (results.length >= 50) break;
    }
    
    // Display results
    if (results.length === 0) {
      this.searchResults.innerHTML = '<div id="search-status">No results found</div>';
    } else {
      this.searchResults.innerHTML = '';
      
      results.forEach(result => {
        const resultDiv = document.createElement('div');
        resultDiv.className = 'search-result';
        
        const titleDiv = document.createElement('div');
        titleDiv.className = 'search-result-title';
        titleDiv.innerHTML = `
          ${this.highlightMatch(result.label, query)}
          <span class="search-result-type${result.isImage ? ' image' : ''}">
            ${result.isImage ? 'Image' : 'Entity'}
          </span>
        `;
        
        const idDiv = document.createElement('div');
        idDiv.className = 'search-result-id';
        idDiv.textContent = result.node.id;
        
        resultDiv.appendChild(titleDiv);
        resultDiv.appendChild(idDiv);
        
        // Click handler to zoom to node
        resultDiv.addEventListener('click', () => {
          this.zoomToNode(result.node);
          resultDiv.classList.add('active');
          // Remove active class from other results
          this.searchResults.querySelectorAll('.search-result').forEach(el => {
            if (el !== resultDiv) el.classList.remove('active');
          });
        });
        
        this.searchResults.appendChild(resultDiv);
      });
      
      if (results.length === 50) {
        const moreDiv = document.createElement('div');
        moreDiv.id = 'search-status';
        moreDiv.textContent = 'Showing first 50 results...';
        this.searchResults.appendChild(moreDiv);
      }
    }
  }
  
  private highlightMatch(text: string, query: string): string {
    const regex = new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
    return text.replace(regex, '<strong>$1</strong>');
  }
  
  private zoomToNode(node: Node): void {
    // Zoom and pan to the node
    this.cameraControls.setCamera({
      x: node.position_x,
      y: node.position_y,
      zoom: 5
    });
    
    // Select the node to show its panel
    setTimeout(() => {
      this.selectNode(node);
    }, 300);
  }
  
  destroy(): void {
    if (this.animationFrameId !== null) {
      cancelAnimationFrame(this.animationFrameId);
    }
    if (this.searchDebounceTimer !== null) {
      clearTimeout(this.searchDebounceTimer);
    }
  }
}

// Start the application
const app = new GraphVisualization();

// Handle page unload
window.addEventListener('beforeunload', () => {
  app.destroy();
});