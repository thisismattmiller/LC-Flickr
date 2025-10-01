import { Node, Edge, Camera, ViewportBounds } from './types';

export class WebGPURenderer {
  private device!: GPUDevice;
  private context!: GPUCanvasContext;
  private pipeline!: GPURenderPipeline;
  private canvas: HTMLCanvasElement;
  private camera: Camera;
  private nodes: Node[] = [];
  private edges: Edge[] = [];
  private selectedNodeId: string | null = null;
  private connectedNodeIds: Set<string> = new Set();
  
  private vertexBuffer!: GPUBuffer;
  private uniformBuffer!: GPUBuffer;
  private bindGroup!: GPUBindGroup;

  constructor(canvas: HTMLCanvasElement) {
    this.canvas = canvas;
    this.camera = { x: 0, y: 0, zoom: 1 };
  }

  async init(): Promise<void> {
    if (!navigator.gpu) {
      throw new Error('WebGPU not supported');
    }

    const adapter = await navigator.gpu.requestAdapter();
    if (!adapter) {
      throw new Error('No GPU adapter found');
    }

    this.device = await adapter.requestDevice();
    this.context = this.canvas.getContext('webgpu')!;
    
    const format = navigator.gpu.getPreferredCanvasFormat();
    this.context.configure({
      device: this.device,
      format,
      alphaMode: 'premultiplied',
    });

    await this.createPipeline(format);
    this.createBuffers();
  }

  private async createPipeline(format: GPUTextureFormat): Promise<void> {
    const vertexShader = `
      struct Uniforms {
        viewMatrix: mat3x3<f32>,
        resolution: vec2<f32>,
      }
      
      @group(0) @binding(0) var<uniform> uniforms: Uniforms;
      
      struct VertexOutput {
        @builtin(position) position: vec4<f32>,
        @location(0) color: vec3<f32>,
        @location(1) nodeType: f32,
      }
      
      @vertex
      fn main(
        @location(0) position: vec2<f32>,
        @location(1) size: f32,
        @location(2) color: vec3<f32>,
        @location(3) nodeType: f32,
        @builtin(vertex_index) vertexIndex: u32
      ) -> VertexOutput {
        var output: VertexOutput;
        
        let angles = array<f32, 6>(
          0.0, 1.047, 2.094, 3.141, 4.189, 5.236
        );
        
        let angle = angles[vertexIndex];
        let offset = vec2<f32>(cos(angle), sin(angle)) * size;
        let worldPos = position + offset;
        
        let transformed = uniforms.viewMatrix * vec3<f32>(worldPos, 1.0);
        let ndcPos = transformed.xy / uniforms.resolution * 2.0 - 1.0;
        
        output.position = vec4<f32>(ndcPos.x, -ndcPos.y, 0.0, 1.0);
        output.color = color;
        output.nodeType = nodeType;
        
        return output;
      }
    `;

    const fragmentShader = `
      @fragment
      fn main(
        @location(0) color: vec3<f32>,
        @location(1) nodeType: f32
      ) -> @location(0) vec4<f32> {
        return vec4<f32>(color, 1.0);
      }
    `;

    const vertexModule = this.device.createShaderModule({ code: vertexShader });
    const fragmentModule = this.device.createShaderModule({ code: fragmentShader });

    const vertexBufferLayout: GPUVertexBufferLayout = {
      arrayStride: 36, // 2 floats pos + 1 float size + 3 floats color + 1 float type + 2 padding
      stepMode: 'instance',
      attributes: [
        { format: 'float32x2', offset: 0, shaderLocation: 0 }, // position
        { format: 'float32', offset: 8, shaderLocation: 1 }, // size
        { format: 'float32x3', offset: 12, shaderLocation: 2 }, // color
        { format: 'float32', offset: 24, shaderLocation: 3 }, // nodeType
      ],
    };

    const bindGroupLayout = this.device.createBindGroupLayout({
      entries: [
        {
          binding: 0,
          visibility: GPUShaderStage.VERTEX,
          buffer: { type: 'uniform' },
        },
      ],
    });

    const pipelineLayout = this.device.createPipelineLayout({
      bindGroupLayouts: [bindGroupLayout],
    });

    this.pipeline = this.device.createRenderPipeline({
      layout: pipelineLayout,
      vertex: {
        module: vertexModule,
        entryPoint: 'main',
        buffers: [vertexBufferLayout],
      },
      fragment: {
        module: fragmentModule,
        entryPoint: 'main',
        targets: [{ format }],
      },
      primitive: {
        topology: 'triangle-list',
      },
    });
  }

  private createBuffers(): void {
    // Uniform buffer for view matrix and resolution
    this.uniformBuffer = this.device.createBuffer({
      size: 64, // mat3x3 (48 bytes) + vec2 (8 bytes) + padding
      usage: GPUBufferUsage.UNIFORM | GPUBufferUsage.COPY_DST,
    });

    this.bindGroup = this.device.createBindGroup({
      layout: this.pipeline.getBindGroupLayout(0),
      entries: [
        {
          binding: 0,
          resource: { buffer: this.uniformBuffer },
        },
      ],
    });
  }

  setData(nodes: Node[], edges: Edge[]): void {
    this.nodes = nodes;
    this.edges = edges;
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
    const bounds = this.getViewportBounds();
    
    return this.nodes.filter(node => {
      // Check if in viewport
      if (node.position_x < bounds.minX || node.position_x > bounds.maxX ||
          node.position_y < bounds.minY || node.position_y > bounds.maxY) {
        return false;
      }
      
      // Importance-based filtering by zoom level
      // At zoom 10 (zoomed out), only show nodes with importance >= 8
      // At zoom 1 (zoomed in), show all nodes
      // Linear interpolation between these extremes
      const minImportance = this.camera.zoom >= 10 ? 8 : 
                           this.camera.zoom <= 1 ? 0 :
                           (this.camera.zoom - 1) * (8 / 9);
      
      return node.importance >= minImportance;
    });
  }

  private getVisibleEdges(visibleNodes: Set<string>): Edge[] {
    return this.edges.filter(edge => 
      visibleNodes.has(edge.source) && visibleNodes.has(edge.target)
    );
  }

  render(): { nodesVisible: number; edgesVisible: number } {
    const visibleNodes = this.getVisibleNodes();
    const visibleNodeIds = new Set(visibleNodes.map(n => n.id));
    const visibleEdges = this.getVisibleEdges(visibleNodeIds);

    // Update uniform buffer
    const viewMatrix = new Float32Array([
      this.camera.zoom, 0, -this.camera.x * this.camera.zoom,
      0, this.camera.zoom, -this.camera.y * this.camera.zoom,
      0, 0, 1,
      this.canvas.width, this.canvas.height, 0, 0, // resolution + padding
    ]);
    this.device.queue.writeBuffer(this.uniformBuffer, 0, viewMatrix);

    // Prepare vertex data
    const vertexData = new Float32Array(visibleNodes.length * 9);
    visibleNodes.forEach((node, i) => {
      const isSelected = node.id === this.selectedNodeId;
      const isConnected = this.connectedNodeIds.has(node.id);
      const isImage = node.id.startsWith('image_');
      
      let color: number[];
      if (isSelected) {
        color = [1, 1, 0]; // Yellow for selected
      } else if (isConnected) {
        color = [0, 1, 0]; // Green for connected
      } else if (isImage) {
        color = [1, 0, 0]; // Red for image nodes
      } else {
        color = [0, 0, 1]; // Blue for Q nodes
      }
      
      const size = Math.sqrt(node.importance) * 5;
      const offset = i * 9;
      
      vertexData[offset] = node.position_x;
      vertexData[offset + 1] = node.position_y;
      vertexData[offset + 2] = size;
      vertexData[offset + 3] = color[0];
      vertexData[offset + 4] = color[1];
      vertexData[offset + 5] = color[2];
      vertexData[offset + 6] = isImage ? 1 : 0;
    });

    if (visibleNodes.length > 0) {
      if (this.vertexBuffer) {
        this.vertexBuffer.destroy();
      }
      
      this.vertexBuffer = this.device.createBuffer({
        size: vertexData.byteLength,
        usage: GPUBufferUsage.VERTEX | GPUBufferUsage.COPY_DST,
      });
      this.device.queue.writeBuffer(this.vertexBuffer, 0, vertexData);
    }

    // Render
    const commandEncoder = this.device.createCommandEncoder();
    const textureView = this.context.getCurrentTexture().createView();
    
    const renderPass = commandEncoder.beginRenderPass({
      colorAttachments: [{
        view: textureView,
        clearValue: { r: 0.95, g: 0.95, b: 0.95, a: 1 },
        loadOp: 'clear',
        storeOp: 'store',
      }],
    });

    if (visibleNodes.length > 0) {
      renderPass.setPipeline(this.pipeline);
      renderPass.setBindGroup(0, this.bindGroup);
      renderPass.setVertexBuffer(0, this.vertexBuffer);
      renderPass.draw(6, visibleNodes.length);
    }

    renderPass.end();
    this.device.queue.submit([commandEncoder.finish()]);

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

  findNodeAt(worldX: number, worldY: number): Node | null {
    const visibleNodes = this.getVisibleNodes();
    
    for (const node of visibleNodes) {
      const size = Math.sqrt(node.importance) * 5;
      const dx = worldX - node.position_x;
      const dy = worldY - node.position_y;
      const distance = Math.sqrt(dx * dx + dy * dy);
      
      if (distance <= size) {
        return node;
      }
    }
    
    return null;
  }
}