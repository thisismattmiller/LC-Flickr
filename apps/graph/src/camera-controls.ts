import { Camera } from './types';

export class CameraControls {
  private camera: Camera;
  private canvas: HTMLCanvasElement;
  private isDragging = false;
  private lastMouseX = 0;
  private lastMouseY = 0;
  private minZoom = 0.01;
  private maxZoom = 10;
  private zoomLevels = [0.01, 0.05, 0.1, 0.25, 0.5, 0.75, 1, 1.5, 2, 3, 5, 10];
  private currentZoomIndex = 2; // Start at zoom level 0.1

  constructor(canvas: HTMLCanvasElement, camera: Camera) {
    this.canvas = canvas;
    this.camera = camera;
    this.setupEventListeners();
  }

  private setupEventListeners(): void {
    // Mouse events
    this.canvas.addEventListener('mousedown', this.handleMouseDown.bind(this));
    this.canvas.addEventListener('mousemove', this.handleMouseMove.bind(this));
    this.canvas.addEventListener('mouseup', this.handleMouseUp.bind(this));
    this.canvas.addEventListener('mouseleave', this.handleMouseUp.bind(this));
    
    // Wheel event for zooming
    this.canvas.addEventListener('wheel', this.handleWheel.bind(this), { passive: false });
    
    // Touch events for mobile
    this.canvas.addEventListener('touchstart', this.handleTouchStart.bind(this), { passive: false });
    this.canvas.addEventListener('touchmove', this.handleTouchMove.bind(this), { passive: false });
    this.canvas.addEventListener('touchend', this.handleTouchEnd.bind(this));
    
    // Keyboard shortcuts
    window.addEventListener('keydown', this.handleKeyDown.bind(this));
  }

  private handleMouseDown(e: MouseEvent): void {
    if (e.button === 0) { // Left mouse button
      this.isDragging = true;
      this.lastMouseX = e.clientX;
      this.lastMouseY = e.clientY;
      this.canvas.style.cursor = 'grabbing';
    }
  }

  private handleMouseMove(e: MouseEvent): void {
    if (this.isDragging) {
      const deltaX = e.clientX - this.lastMouseX;
      const deltaY = e.clientY - this.lastMouseY;
      
      // Pan the camera (inverted for natural dragging)
      this.camera.x -= deltaX / this.camera.zoom;
      this.camera.y -= deltaY / this.camera.zoom;
      
      this.lastMouseX = e.clientX;
      this.lastMouseY = e.clientY;
    }
  }

  private handleMouseUp(): void {
    this.isDragging = false;
    this.canvas.style.cursor = 'grab';
  }

  private handleWheel(e: WheelEvent): void {
    e.preventDefault();
    
    // Get mouse position in world coordinates before zoom
    const rect = this.canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;
    
    const worldXBefore = (mouseX - this.canvas.width / 2) / this.camera.zoom + this.camera.x;
    const worldYBefore = (mouseY - this.canvas.height / 2) / this.camera.zoom + this.camera.y;
    
    // Calculate zoom change
    const zoomDelta = e.deltaY > 0 ? 0.9 : 1.1;
    const newZoom = Math.max(this.minZoom, Math.min(this.maxZoom, this.camera.zoom * zoomDelta));
    
    // Update zoom
    this.camera.zoom = newZoom;
    
    // Calculate new world position after zoom
    const worldXAfter = (mouseX - this.canvas.width / 2) / this.camera.zoom + this.camera.x;
    const worldYAfter = (mouseY - this.canvas.height / 2) / this.camera.zoom + this.camera.y;
    
    // Adjust camera position to keep mouse position fixed
    this.camera.x -= worldXAfter - worldXBefore;
    this.camera.y -= worldYAfter - worldYBefore;
  }

  private handleTouchStart(e: TouchEvent): void {
    e.preventDefault();
    if (e.touches.length === 1) {
      this.isDragging = true;
      this.lastMouseX = e.touches[0].clientX;
      this.lastMouseY = e.touches[0].clientY;
    }
  }

  private handleTouchMove(e: TouchEvent): void {
    e.preventDefault();
    if (e.touches.length === 1 && this.isDragging) {
      const deltaX = e.touches[0].clientX - this.lastMouseX;
      const deltaY = e.touches[0].clientY - this.lastMouseY;
      
      this.camera.x -= deltaX / this.camera.zoom;
      this.camera.y -= deltaY / this.camera.zoom;
      
      this.lastMouseX = e.touches[0].clientX;
      this.lastMouseY = e.touches[0].clientY;
    }
  }

  private handleTouchEnd(): void {
    this.isDragging = false;
  }

  private handleKeyDown(e: KeyboardEvent): void {
    const panSpeed = 50 / this.camera.zoom;
    
    switch (e.key) {
      case 'ArrowUp':
      case 'w':
        this.camera.y -= panSpeed;
        break;
      case 'ArrowDown':
      case 's':
        this.camera.y += panSpeed;
        break;
      case 'ArrowLeft':
      case 'a':
        this.camera.x -= panSpeed;
        break;
      case 'ArrowRight':
      case 'd':
        this.camera.x += panSpeed;
        break;
      case '+':
      case '=':
        this.zoomIn();
        break;
      case '-':
      case '_':
        this.zoomOut();
        break;
      case '0':
        this.resetView();
        break;
    }
  }

  zoomIn(): void {
    if (this.currentZoomIndex < this.zoomLevels.length - 1) {
      this.currentZoomIndex++;
      this.camera.zoom = this.zoomLevels[this.currentZoomIndex];
    }
  }

  zoomOut(): void {
    if (this.currentZoomIndex > 0) {
      this.currentZoomIndex--;
      this.camera.zoom = this.zoomLevels[this.currentZoomIndex];
    }
  }

  resetView(): void {
    this.camera.x = 0; // Start at origin
    this.camera.y = 0;
    this.camera.zoom = 1;
    this.currentZoomIndex = 4;
  }

  getCamera(): Camera {
    return this.camera;
  }

  setCamera(camera: Camera): void {
    this.camera = camera;
    // Find closest zoom level
    let closestIndex = 0;
    let closestDiff = Math.abs(this.zoomLevels[0] - camera.zoom);
    for (let i = 1; i < this.zoomLevels.length; i++) {
      const diff = Math.abs(this.zoomLevels[i] - camera.zoom);
      if (diff < closestDiff) {
        closestDiff = diff;
        closestIndex = i;
      }
    }
    this.currentZoomIndex = closestIndex;
  }
}