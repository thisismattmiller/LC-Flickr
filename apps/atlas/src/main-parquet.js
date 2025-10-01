import { coordinator, DuckDBWASMConnector } from '@uwdata/mosaic-core';
import { loadParquet, sql } from '@uwdata/mosaic-sql';
import { EmbeddingViewMosaic } from 'embedding-atlas';

// Initialize DuckDB WASM connector
async function initializeDuckDB() {
    console.log('Initializing DuckDB WASM...');
    
    try {
        // Create DuckDB WASM connector
        const wasm = new DuckDBWASMConnector({ 
            log: false  // Enable logging for debugging
        });
        
        // Set the connector for the coordinator
        coordinator().databaseConnector(wasm);
        
        console.log('DuckDB WASM initialized successfully');
        return wasm;
    } catch (error) {
        console.error('Failed to initialize DuckDB WASM:', error);
        throw error;
    }
}

// Load the Parquet file into DuckDB
async function loadData() {
    console.log('Loading Parquet data...');

    try {
        // Try loading with absolute path first (for dev)
        let dataPath = '/data/data.parquet';
        try {
            await coordinator().exec([
                loadParquet("comments", dataPath)
            ]);
            console.log('Parquet data loaded successfully from', dataPath);
        } catch (error) {
            // If absolute path fails, construct full URL (for GitHub Pages)
            console.log('Failed to load from absolute path, trying full URL...');
            const baseUrl = window.location.href.replace(/\/[^\/]*$/, '/');
            dataPath = `${baseUrl}data/data.parquet`;
            console.log('Trying to load from:', dataPath);
            await coordinator().exec([
                loadParquet("comments", dataPath)
            ]);
            console.log('Parquet data loaded successfully from', dataPath);
        }
        
        // Query to get table info
        const tableInfo = await coordinator().query(
            sql`SELECT COUNT(*) as count FROM comments`
        );
        
        console.log('Table info:', tableInfo);
        
        // Get column information
        const columns = await coordinator().query(
            sql`DESCRIBE comments`
        );
        
        console.log('Columns:', columns);
        
        // Sample a few rows
        const sampleData = await coordinator().query(
            sql`SELECT * FROM comments LIMIT 5`
        );
        
        console.log('Sample data:', sampleData);
        
        return true;
    } catch (error) {
        console.error('Failed to load Parquet data:', error);
        throw error;
    }
}

const categoryLabels = {
"0": "Historical Context and Identification with Links",
"1": "Aesthetic Praise and Admiration",
"2": "Biographical & Historical Wikimedia Contributions",
"3": "Factual Historical Annotation",
"4": "Historical Detail Identification and Contextualization",
"5": "Explore Congratulations",
"6": "See Also",
"7": "Historical Subject Identification and Details",
"8": "Location and Status Verification",
"9": "Aesthetic Feedback",
"10": "LC Staff Thanks for Metadata Improvement",
"11": "Non-English Compliments",
"12": "Flickr Group Invitations",
"13": "Crowdsourced Historical Data Refinement",
"14": "Historical Performing Artist Biographical Documentation",
"15": "Sourced Historical Details and Context",
"16": "Flickr Group Invitations",
"17": "Flickr Group Invitations",
"18": "Location Verification and Contemporary Comparison",
"19": "Cross-referencing and Linked Information",
"20": "External Content Feature Notification",
"21": "Observations on Period Appearance",
"22": "LC Staff Thanks for Contributions",
"23": "Wikidata Zone 💪",
"24": "Factual Correction and Archival Enhancement",
"25": "Historical Factual Identification and Context",
"26": "Historical Baseball Identification and Contextualization",
"27": "Flickr Group Invitations",
"28": "Factual contributions and corrections",
"29": "Factual Identification and Historical Context",
"30": "Group Invitations",
"31": "Identification and Biographical Information of Historical Figures",
"32": "Historical Photo Annotation",
"33": "Biographical and Genealogical Identification",
"34": "Flickr Group Invitations",
"35": "Praise",
"36": "Historical Annotation",
"37": "Compliments"
}

// Custom Tooltip Component
class CustomTooltip {
    constructor(target, props) {
        this.target = target;
        this.tooltipElement = null;
        this.mouseMoveHandler = null;
        this.createTooltip();
        this.update(props);
    }
    
    createTooltip() {
        this.tooltipElement = document.createElement('div');
        this.tooltipElement.style.cssText = `
            position: fixed;
            background: rgba(20, 20, 20, 0.98);
            color: white;
            padding: 16px 18px;
            border-radius: 12px;
            max-width: 450px;
            font-size: 14px;
            pointer-events: none;
            z-index: 10000;
            box-shadow: 0 8px 32px rgba(0,0,0,0.5), 0 0 0 1px rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
            line-height: 1.6;
            opacity: 0;
            transform: translateY(-5px);
            transition: opacity 0.2s ease, transform 0.2s ease;
        `;
        document.body.appendChild(this.tooltipElement);
    }
    
    sanitizeHtml(html) {
        // Create a temporary div to parse the HTML
        const temp = document.createElement('div');
        temp.innerHTML = html;
        
        // Remove dangerous elements
        const dangerous = temp.querySelectorAll('script, iframe, object, embed, form, style, link');
        dangerous.forEach(el => el.remove());
        
        // Remove on* event handlers
        temp.querySelectorAll('*').forEach(el => {
            Array.from(el.attributes).forEach(attr => {
                if (attr.name.startsWith('on')) {
                    el.removeAttribute(attr.name);
                }
            });
        });
        
        // Style all links
        temp.querySelectorAll('a').forEach(link => {
            link.style.cssText = 'color: #58a6ff; text-decoration: underline; text-underline-offset: 2px;';
            link.target = '_blank';
            link.rel = 'noopener noreferrer';
        });
        
        // Style all images
        temp.querySelectorAll('img').forEach(img => {
            img.style.cssText = 'max-width: 100%; height: auto; border-radius: 6px; margin: 8px 0;';
        });
        
        return temp.innerHTML;
    }
    
    update(props) {
        if (!props.tooltip) {
            this.tooltipElement.style.opacity = '0';
            this.tooltipElement.style.transform = 'translateY(-5px)';
            this.mouseMoveHandler = null;
            return;
        }
        
        const { x, y, text, identifier, category } = props.tooltip;
        
        // Truncate very long comments for tooltip
        let displayText = text || '';
        const maxLength = 500;
        let truncated = false;
        if (displayText.length > maxLength) {
            displayText = displayText.substring(0, maxLength);
            truncated = true;
        }
        
        // Get category label


        const categoryLabel = categoryLabels[category] || 'Unknown';

        
        // Build tooltip content
        this.tooltipElement.innerHTML = `
            <div style="margin-bottom: 12px; padding-bottom: 12px; border-bottom: 1px solid rgba(255,255,255,0.1);">
                <div style="font-weight: 600; font-size: 18px; color: white; margin-bottom: 2px;">
                    ${categoryLabel}
                </div>

            </div>
            <div style="
                max-height: 250px;
                overflow-y: auto;
                padding-right: 8px;
                scrollbar-width: thin;
                scrollbar-color: rgba(255,255,255,0.2) transparent;
            ">
                <div style="color: #e0e0e0; font-size: 13px;">
                    ${this.sanitizeHtml(displayText)}
                    ${truncated ? '<span style="color: #888; font-style: italic;">... (truncated)</span>' : ''}
                </div>
            </div>
            <div style="margin-top: 12px; padding-top: 10px; border-top: 1px solid rgba(255,255,255,0.08); font-size: 11px; color: white;">
                💡 Click point to open Flickr
            </div>
        `;
        
        // Custom scrollbar styles for webkit browsers
        const styleElement = this.tooltipElement.querySelector('style') || document.createElement('style');
        styleElement.textContent = `
            div::-webkit-scrollbar {
                width: 6px;
            }
            div::-webkit-scrollbar-track {
                background: transparent;
            }
            div::-webkit-scrollbar-thumb {
                background: rgba(255,255,255,0.2);
                border-radius: 3px;
            }
            div::-webkit-scrollbar-thumb:hover {
                background: rgba(255,255,255,0.3);
            }
        `;
        if (!this.tooltipElement.querySelector('style')) {
            this.tooltipElement.appendChild(styleElement);
        }
        
        // Remove old mouse handler if it exists
        if (this.mouseMoveHandler) {
            document.removeEventListener('mousemove', this.mouseMoveHandler);
        }
        
        // Create new mouse move handler for dynamic positioning
        this.mouseMoveHandler = (e) => {
            const tooltipRect = this.tooltipElement.getBoundingClientRect();
            const tooltipWidth = tooltipRect.width || 450;
            const tooltipHeight = tooltipRect.height || 300;
            
            // Calculate position based on quadrant of screen
            const screenCenterX = window.innerWidth / 2;
            const screenCenterY = window.innerHeight / 2;
            const mouseX = e.clientX;
            const mouseY = e.clientY;
            
            let left, top;
            
            // Horizontal positioning
            if (mouseX < screenCenterX) {
                // Mouse is on left half - show tooltip to the right
                left = mouseX + 15;
                // Check if it goes off-screen
                if (left + tooltipWidth > window.innerWidth - 10) {
                    left = window.innerWidth - tooltipWidth - 10;
                }
            } else {
                // Mouse is on right half - show tooltip to the left
                left = mouseX - tooltipWidth - 15;
                // Check if it goes off-screen
                if (left < 10) {
                    left = 10;
                }
            }
            
            // Vertical positioning
            if (mouseY < screenCenterY) {
                // Mouse is in top half - position tooltip slightly below
                top = mouseY + 10;
                // Make sure it doesn't go off bottom
                if (top + tooltipHeight > window.innerHeight - 10) {
                    top = window.innerHeight - tooltipHeight - 10;
                }
            } else {
                // Mouse is in bottom half - position tooltip above
                top = mouseY - tooltipHeight - 10;
                // Make sure it doesn't go off top
                if (top < 10) {
                    top = mouseY + 10; // Fall back to below cursor
                }
            }
            
            this.tooltipElement.style.left = left + 'px';
            this.tooltipElement.style.top = top + 'px';
        };
        
        // Attach mouse move handler
        document.addEventListener('mousemove', this.mouseMoveHandler);
        
        // Initial position based on current mouse
        if (currentMousePosition) {
            this.mouseMoveHandler({ clientX: currentMousePosition.x, clientY: currentMousePosition.y });
        }
        
        // Show tooltip with animation
        this.tooltipElement.style.opacity = '1';
        this.tooltipElement.style.transform = 'translateY(0)';
    }
    
    destroy() {
        if (this.mouseMoveHandler) {
            document.removeEventListener('mousemove', this.mouseMoveHandler);
            this.mouseMoveHandler = null;
        }
        if (this.tooltipElement) {
            this.tooltipElement.remove();
            this.tooltipElement = null;
        }
    }
}

// Create the embedding visualization
let embeddingComponent = null;
let currentMousePosition = { x: 0, y: 0 };
let currentViewportState = null; // Track viewport state
let hasActiveSelection = false; // Track if we have an active selection

// Track mouse position for tooltip positioning
document.addEventListener('mousemove', (e) => {
    currentMousePosition = { x: e.clientX, y: e.clientY };
});

// Handle window focus to reset selection
window.addEventListener('focus', () => {
    if (hasActiveSelection && embeddingComponent) {
        console.log("Window regained focus, resetting selection...");
        
        // Store current viewport state before destroying
        const tempViewport = currentViewportState;
        
        // Destroy the component
        embeddingComponent.destroy();
        embeddingComponent = null;
        
        // Recreate after a brief delay
        setTimeout(async () => {
            currentViewportState = tempViewport; // Restore viewport state
            await createEmbeddingVisualization();
            hasActiveSelection = false;
        }, 100);
    }
});

async function createEmbeddingVisualization() {
    const container = document.getElementById('container');
    if (!container) {
        console.error('Container element not found');
        return;
    }
    
    // // First, we need to add a category column to our data
    // // Create categories based on comment length for now
    // console.log('Creating category column based on comment length...');
    // await coordinator().exec(sql`
    //     CREATE OR REPLACE TABLE comments_with_category AS
    //     SELECT *,
    //         CASE 
    //             WHEN LENGTH(comment_content) < 50 THEN 0
    //             WHEN LENGTH(comment_content) < 100 THEN 1
    //             WHEN LENGTH(comment_content) < 200 THEN 2
    //             WHEN LENGTH(comment_content) < 500 THEN 3
    //             ELSE 4
    //         END as category
    //     FROM comments
    // `);
    
    // Configure the embedding view props
    const props = {
        coordinator: coordinator(),
        table: "comments",
        x: "x",
        y: "y",
        category: "category",
        text: "comment_content",
        identifier: "comment_id",
        width: window.innerWidth,
        height: window.innerHeight,
        pixelRatio: window.devicePixelRatio || 1,
        mode: "density", // Start in density mode for large dataset
        automaticLabels: false, // Enable automatic labels
        colorScheme: "light",
        theme: {
            fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
            statusBar: true,
            statusBarTextColor: "#333",
            statusBarBackgroundColor: "rgba(255, 255, 255, 0.9)",
            brandingLink: null
        },
        // Restore viewport state if available
        viewportState: currentViewportState,
        // Track viewport changes
        onViewportState: (viewport) => {
            currentViewportState = viewport;
        },
        // Use custom tooltip
        customTooltip: {
            class: CustomTooltip,
            props: { 
                mousePosition: currentMousePosition 
            }
        },
        onTooltip: (value) => {
            // Update mouse position for custom tooltip
            if (embeddingComponent && embeddingComponent.update) {
                embeddingComponent.update({
                    customTooltip: {
                        class: CustomTooltip,
                        props: { 
                            mousePosition: currentMousePosition 
                        }
                    }
                });
            }
        },
        onSelection: (value) => {
            if (value && value.length > 0) {
                console.log('Selection:', value);
                hasActiveSelection = true; // Mark that we have an active selection
                
                // Open Flickr URL on click
                const point = value[0];
                if (point.identifier) {
                    const flickrUrl = buildFlickrUrl(point.identifier);
                    if (flickrUrl) {
                        window.open(flickrUrl, '_blank');
                        
                        // Force clear selection after a delay
                        setTimeout(() => {
                            if (embeddingComponent) {
                                // Store viewport and recreate to clear selection
                                const tempViewport = currentViewportState;
                                embeddingComponent.destroy();
                                embeddingComponent = null;
                                
                                setTimeout(async () => {
                                    currentViewportState = tempViewport;
                                    await createEmbeddingVisualization();
                                    hasActiveSelection = false;
                                }, 50);
                            }
                        }, 200);
                    }
                }
            } else {
                // Selection cleared
                hasActiveSelection = false;
            }
        }
    };
    
    // Create the embedding view component
    console.log('Creating EmbeddingViewMosaic component...');
    embeddingComponent = new EmbeddingViewMosaic(container, props);
    
    console.log('Embedding visualization created successfully!');
    
    // Add info overlay
    const infoDiv = document.createElement('div');
    infoDiv.style.cssText = `
        position: absolute;
        top: 10px;
        left: 10px;
        background: rgba(255, 255, 255, 0.95);
        padding: 10px 15px;
        border-radius: 6px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        font-size: 14px;
        z-index: 1000;
    `;

    
}

// Helper function to build Flickr URL from comment ID
function buildFlickrUrl(commentId) {
    // Format: "8602872-6892494747-72157629375181103"
    // URL: https://www.flickr.com/photos/library_of_congress/6892494747/#comment72157629375181103
    const parts = commentId.split('-');
    if (parts.length >= 3) {
        const photoId = parts[1];
        const commentPart = parts[2];
        return `https://www.flickr.com/photos/library_of_congress/${photoId}/#comment${commentPart}`;
    }
    return null;
}

// Main initialization
async function main() {
    console.log('Starting Parquet/DuckDB visualization...');

    // Add global styles to prevent overflow
    const globalStyles = document.createElement('style');
    globalStyles.textContent = `
        html, body {
            margin: 0;
            padding: 0;
            width: 100%;
            height: 100%;
            overflow: hidden;
        }
        #container {
            width: 100vw;
            height: 100vh;
            position: relative;
            overflow: hidden;
        }
    `;
    document.head.appendChild(globalStyles);

    try {
        // Show loading state

        // Initialize DuckDB
        await initializeDuckDB();

        // Load the Parquet file
        await loadData();

        // Create the embedding visualization
        await createEmbeddingVisualization();

        // Hide modal after loading
        const modal = document.getElementById('modal');
        if (modal) {
            modal.style.display = 'none';
        }

        // Make coordinator and utilities available globally for testing
        window.mosaic = {
            coordinator: coordinator(),
            component: embeddingComponent,
            query: async (sqlQuery) => {
                const result = await coordinator().query(sqlQuery);
                console.log('Query result:', result);
                return result;
            },
            sql: sql
        };

        console.log('Visualization ready! Available commands:');
        console.log('  window.mosaic.query(window.mosaic.sql`SELECT * FROM comments_with_category LIMIT 10`)');
        console.log('  window.mosaic.component.update({ mode: "points" }) // Switch to points mode');
        console.log('  window.mosaic.component.update({ automaticLabels: true }) // Enable automatic labels');

    } catch (error) {
        console.error('Failed to initialize:', error);
        const container = document.getElementById('container');
        if (container) {
            container.innerHTML = `
                <div style="padding: 20px; color: red; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
                    <h2>Error</h2>
                    <pre>${error.message}</pre>
                    <p>Check the console for more details.</p>
                </div>
            `;
        }
    }
}

// Function to be called when Load button is clicked
window.loadVisualization = function() {
    const modal = document.getElementById('modal');
    if (modal) {
        modal.style.display = 'none';
    }
    main();
}

// Handle window resize
window.addEventListener('resize', () => {
    if (embeddingComponent) {
        embeddingComponent.update({
            width: window.innerWidth,
            height: window.innerHeight
        });
    }
});

// Don't auto-start - wait for user to click Load button

// Export for debugging
export { coordinator, sql };