import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import readline from 'readline';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const INPUT_FILE = path.join(__dirname, '../../../data/comments_with_umap_coords.jsonl');
const OUTPUT_DIR = path.join(__dirname, '../public/data');
const CHUNK_SIZE = 5000; // Points per chunk for progressive loading

async function processData() {
    console.log('Starting data processing...');
    
    // Create output directory if it doesn't exist
    if (!fs.existsSync(OUTPUT_DIR)) {
        fs.mkdirSync(OUTPUT_DIR, { recursive: true });
    } else {
        // Delete existing output files if they exist
        console.log('Cleaning up existing output files...');
        const files = fs.readdirSync(OUTPUT_DIR);
        for (const file of files) {
            const filePath = path.join(OUTPUT_DIR, file);
            if (fs.statSync(filePath).isFile()) {
                fs.unlinkSync(filePath);
                console.log(`Deleted: ${file}`);
            }
        }
    }

    // Read and count total lines first
    const fileStream = fs.createReadStream(INPUT_FILE);
    const rl = readline.createInterface({
        input: fileStream,
        crlfDelay: Infinity
    });

    const allData = [];
    let lineCount = 0;

    console.log('Reading JSONL file...');
    for await (const line of rl) {
        if (line.trim()) {
            try {
                const data = JSON.parse(line);
                allData.push(data);
                lineCount++;
                if (lineCount % 10000 === 0) {
                    console.log(`Processed ${lineCount} lines...`);
                }
            } catch (e) {
                console.error(`Error parsing line ${lineCount + 1}:`, e);
            }
        }
    }

    console.log(`Total points: ${allData.length}`);

    // Calculate bounds for normalization
    let minX = Infinity, maxX = -Infinity;
    let minY = Infinity, maxY = -Infinity;
    
    for (const point of allData) {
        minX = Math.min(minX, point.x);
        maxX = Math.max(maxX, point.x);
        minY = Math.min(minY, point.y);
        maxY = Math.max(maxY, point.y);
    }

    console.log(`X range: [${minX}, ${maxX}]`);
    console.log(`Y range: [${minY}, ${maxY}]`);

    // Create metadata file
    const metadata = {
        totalPoints: allData.length,
        chunks: Math.ceil(allData.length / CHUNK_SIZE),
        chunkSize: CHUNK_SIZE,
        bounds: { minX, maxX, minY, maxY }
    };

    fs.writeFileSync(
        path.join(OUTPUT_DIR, 'metadata.json'),
        JSON.stringify(metadata, null, 2)
    );

    // Create chunks with binary data and metadata
    const numChunks = Math.ceil(allData.length / CHUNK_SIZE);
    
    for (let chunkIndex = 0; chunkIndex < numChunks; chunkIndex++) {
        const start = chunkIndex * CHUNK_SIZE;
        const end = Math.min(start + CHUNK_SIZE, allData.length);
        const chunkData = allData.slice(start, end);
        
        // Create Float32Arrays for x and y
        const xArray = new Float32Array(chunkData.length);
        const yArray = new Float32Array(chunkData.length);
        const comments = [];
        const ids = [];
        
        for (let i = 0; i < chunkData.length; i++) {
            // Normalize coordinates to [-1, 1] range for better visualization
            xArray[i] = ((chunkData[i].x - minX) / (maxX - minX)) * 2 - 1;
            yArray[i] = ((chunkData[i].y - minY) / (maxY - minY)) * 2 - 1;
            comments.push(chunkData[i].comment_content);
            ids.push(chunkData[i].comment_id);
        }
        
        // Save binary data
        fs.writeFileSync(
            path.join(OUTPUT_DIR, `chunk_${chunkIndex}_x.bin`),
            Buffer.from(xArray.buffer)
        );
        
        fs.writeFileSync(
            path.join(OUTPUT_DIR, `chunk_${chunkIndex}_y.bin`),
            Buffer.from(yArray.buffer)
        );
        
        // Save metadata for this chunk
        fs.writeFileSync(
            path.join(OUTPUT_DIR, `chunk_${chunkIndex}_meta.json`),
            JSON.stringify({
                comments,
                ids,
                index: chunkIndex,
                size: chunkData.length,
                start,
                end
            })
        );
        
        console.log(`Created chunk ${chunkIndex + 1}/${numChunks} (${chunkData.length} points)`);
    }

    // Create a sample dataset for quick loading (first 1000 points)
    const sampleSize = Math.min(1000, allData.length);
    const sampleData = allData.slice(0, sampleSize);
    
    const sampleX = new Float32Array(sampleSize);
    const sampleY = new Float32Array(sampleSize);
    const sampleComments = [];
    
    for (let i = 0; i < sampleSize; i++) {
        sampleX[i] = ((sampleData[i].x - minX) / (maxX - minX)) * 2 - 1;
        sampleY[i] = ((sampleData[i].y - minY) / (maxY - minY)) * 2 - 1;
        sampleComments.push(sampleData[i].comment_content);
    }
    
    fs.writeFileSync(
        path.join(OUTPUT_DIR, 'sample.json'),
        JSON.stringify({
            x: Array.from(sampleX),
            y: Array.from(sampleY),
            comments: sampleComments
        })
    );

    console.log('\nData processing complete!');
    console.log(`Output directory: ${OUTPUT_DIR}`);
    console.log(`Total chunks created: ${numChunks}`);
    console.log(`Sample dataset: ${sampleSize} points`);
}

processData().catch(console.error);