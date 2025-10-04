// Data will be loaded from the JSON file
let data = null;
let currentTab = 'subjects';

// Load the data
async function loadData() {
    try {
        const response = await fetch('../../data/viz_data/subject_collection_popularity.json');
        data = await response.json();
        initialize();
    } catch (error) {
        console.error('Error loading data:', error);
        document.querySelector('.container').innerHTML = '<p style="color: red; text-align: center;">Error loading data. Please check the console.</p>';
    }
}

function initialize() {
    renderStats();
    renderContent();
    setupEventListeners();
}

function renderStats() {
    const stats = data.summary;
    const statsHtml = `
        <div class="stat-card">
            <span class="stat-label">Photos with LCSH Subject Headings:</span>
            <span class="stat-value">${stats.total_photos_analyzed.toLocaleString()}</span>
        </div>
        <div class="stat-card">
            <span class="stat-label">Tags:</span>
            <span class="stat-value">${stats.total_user_tags.toLocaleString()}</span>
        </div>
        <div class="stat-card">
            <span class="stat-label">Comments:</span>
            <span class="stat-value">${stats.total_user_comments.toLocaleString()}</span>
        </div>
        <div class="stat-card">
            <span class="stat-label">Interactions:</span>
            <span class="stat-value">${stats.total_user_interactions.toLocaleString()}</span>
        </div>
    `;
    document.getElementById('statsOverview').innerHTML = statsHtml;
}

function setupEventListeners() {
    // Tab switching
    document.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', () => {
            const tabName = tab.dataset.tab;
            switchTab(tabName);
        });
    });

    // Sort and filter controls
    document.getElementById('sortBy').addEventListener('change', renderContent);
    document.getElementById('limit').addEventListener('change', renderContent);
    document.getElementById('search').addEventListener('input', renderContent);
}

function switchTab(tabName) {
    currentTab = tabName;

    // Update tab buttons
    document.querySelectorAll('.tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.tab === tabName);
    });

    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    document.getElementById(tabName + 'Tab').classList.add('active');

    renderContent();
}

function renderContent() {
    if (currentTab === 'subjects') {
        renderSubjects();
    } else {
        renderCollections();
    }
}

function renderSubjects() {
    const subjects = data.subjects.top_100;
    const filtered = filterAndSort(subjects, 'subject');
    const html = filtered.map((item, index) => createItemCard(item, index + 1, 'subject')).join('');

    document.getElementById('subjectsList').innerHTML = html || '<div class="no-results">No results found</div>';
}

function renderCollections() {
    const collections = data.collections.top_20;
    const filtered = filterAndSort(collections, 'title');
    const html = filtered.map((item, index) => createItemCard(item, index + 1, 'collection')).join('');

    document.getElementById('collectionsList').innerHTML = html || '<div class="no-results">No results found</div>';
}

function filterAndSort(items, nameField) {
    const searchTerm = document.getElementById('search').value.toLowerCase();
    const sortBy = document.getElementById('sortBy').value;
    const limit = document.getElementById('limit').value;

    // Filter by search
    let filtered = items.filter(item => {
        const name = item[nameField].toLowerCase();
        return name.includes(searchTerm);
    });

    // Sort
    filtered.sort((a, b) => {
        switch (sortBy) {
            case 'total':
                return b.interactions.total - a.interactions.total;
            case 'avg':
                return b.avg_per_photo - a.avg_per_photo;
            case 'photos':
                return b.photos - a.photos;
            case 'comments':
                return b.interactions.comments - a.interactions.comments;
            case 'tags':
                return b.interactions.tags - a.interactions.tags;
            case 'notes':
                return b.interactions.notes - a.interactions.notes;
            default:
                return 0;
        }
    });

    // Limit
    if (limit !== 'all') {
        filtered = filtered.slice(0, parseInt(limit));
    }

    return filtered;
}

function createItemCard(item, rank, type) {
    const name = type === 'subject' ? item.subject : item.title;
    const code = item.code ? `<span style="color: #999; font-size: 12px; font-weight: normal;"> (${item.code})</span>` : '';

    const maxInteraction = Math.max(
        item.interactions.tags,
        item.interactions.comments,
        item.interactions.notes
    );

    return `
        <div class="item-card">
            <div class="item-header">
                <div class="item-title">${name}${code}</div>
                <div class="item-rank">#${rank}</div>
            </div>

            <div class="item-stats">
                <div class="stat">
                    <span class="stat-name">Photos:</span>
                    <span class="stat-num">${item.photos.toLocaleString()}</span>
                </div>
                <div class="stat">
                    <span class="stat-name">Total:</span>
                    <span class="stat-num">${item.interactions.total.toLocaleString()}</span>
                </div>
                <div class="stat">
                    <span class="stat-name">Avg:</span>
                    <span class="stat-num">${item.avg_per_photo.toFixed(1)}</span>
                </div>
            </div>

            <div class="bar-chart">
                ${createBar('Tags', item.interactions.tags, maxInteraction)}
                ${createBar('Comments', item.interactions.comments, maxInteraction)}
                ${createBar('Notes', item.interactions.notes, maxInteraction)}
            </div>
        </div>
    `;
}

function createBar(label, value, max) {
    const percentage = (value / max) * 100;
    return `
        <div class="bar">
            <div class="bar-label">${label}:</div>
            <div class="bar-fill" style="width: ${percentage}%;">
                ${value.toLocaleString()}
            </div>
        </div>
    `;
}

// Initialize the app
loadData();
