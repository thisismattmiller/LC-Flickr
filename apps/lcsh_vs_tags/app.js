// State management
let allMappings = [];
let filteredMappings = [];
let currentSort = 'photos';
const INITIAL_TAGS_SHOW = 15;
const IMAGE_BASE_URL = 'https://thisismattmiller.s3.us-east-1.amazonaws.com/lc-flickr-comments-photos/';
const IMAGES_PER_LOAD = 5;

// Track loaded images per subject
const loadedImagesState = {};

// DOM elements
const loadingEl = document.getElementById('loading');
const gridEl = document.getElementById('subjectsGrid');
const noResultsEl = document.getElementById('noResults');
const searchBox = document.getElementById('searchBox');
const filterButtons = document.querySelectorAll('.filter-btn');

// Stats elements
const totalSubjectsEl = document.getElementById('totalSubjects');
const totalPhotosEl = document.getElementById('totalPhotos');
const photosWithTagsEl = document.getElementById('photosWithTags');

// Load and initialize data
async function loadData() {
    try {
        const response = await fetch('subject_tag_mappings.json');
        const data = await response.json();

        // Update stats
        totalSubjectsEl.textContent = data.summary.total_subjects.toLocaleString();
        totalPhotosEl.textContent = data.summary.total_photos_analyzed.toLocaleString();
        photosWithTagsEl.textContent = data.summary.photos_with_user_tags.toLocaleString();

        // Store mappings
        allMappings = data.mappings;
        filteredMappings = [...allMappings];

        // Initial render
        sortMappings(currentSort);
        renderMappings();

        // Hide loading, show grid
        loadingEl.style.display = 'none';
        gridEl.style.display = 'grid';
    } catch (error) {
        console.error('Error loading data:', error);
        loadingEl.textContent = 'Error loading data. Please refresh the page.';
    }
}

// Sort mappings
function sortMappings(sortType) {
    currentSort = sortType;

    switch (sortType) {
        case 'photos':
            filteredMappings.sort((a, b) => b.total_photos - a.total_photos);
            break;
        case 'tags':
            filteredMappings.sort((a, b) => b.total_unique_tags - a.total_unique_tags);
            break;
        case 'alpha':
            filteredMappings.sort((a, b) => a.subject.localeCompare(b.subject));
            break;
    }
}

// Filter mappings by search
function filterMappings(searchTerm) {
    const term = searchTerm.toLowerCase().trim();

    if (!term) {
        filteredMappings = [...allMappings];
    } else {
        filteredMappings = allMappings.filter(mapping =>
            mapping.subject.toLowerCase().includes(term)
        );
    }

    sortMappings(currentSort);
    renderMappings();
}

// Render all mappings
function renderMappings() {
    if (filteredMappings.length === 0) {
        gridEl.style.display = 'none';
        noResultsEl.style.display = 'block';
        return;
    }

    gridEl.style.display = 'grid';
    noResultsEl.style.display = 'none';

    gridEl.innerHTML = filteredMappings.map(mapping =>
        renderSubjectCard(mapping)
    ).join('');

    // Add event listeners for "show more" buttons
    document.querySelectorAll('.show-more-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const subjectId = e.target.dataset.subject;
            toggleShowMore(subjectId);
        });
    });

    // Add event listeners for "load images" buttons
    document.querySelectorAll('.load-images-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const subjectId = e.target.dataset.subject;
            loadMoreImages(subjectId);
        });
    });
}

// Render a single subject card
function renderSubjectCard(mapping) {
    const subjectId = mapping.subject.replace(/[^a-zA-Z0-9]/g, '_');
    const showAllTags = mapping.showAll || false;
    const tagsToShow = showAllTags ? mapping.top_tags : mapping.top_tags.slice(0, INITIAL_TAGS_SHOW);
    const hasMore = mapping.top_tags.length > INITIAL_TAGS_SHOW;

    // LOC authority data
    const locAuth = mapping.loc_authority || {};
    // Remove duplicates from variant labels
    const uniqueVariantLabels = locAuth.variant_labels ?
        [...new Set(locAuth.variant_labels)] : [];
    const hasLocData = locAuth.uri || uniqueVariantLabels.length > 0;

    return `
        <div class="subject-card">
            <div class="subject-header">
                <h2 class="subject-title">${escapeHtml(mapping.subject)}</h2>
                <div class="subject-meta">
                    <div class="meta-item">
                        <span class="meta-label">Photos</span>
                        <span class="meta-value">${mapping.total_photos.toLocaleString()}</span>
                    </div>
                    <div class="meta-item">
                        <span class="meta-label">Unique Tags</span>
                        <span class="meta-value">${mapping.total_unique_tags.toLocaleString()}</span>
                    </div>
                </div>
            </div>

            ${hasLocData ? `
                <div class="loc-info">
                    ${locAuth.uri ? `
                        <div class="loc-uri">
                            <span class="loc-uri-label">LOC Authority:</span>
                            <a href="${locAuth.uri}" target="_blank" rel="noopener noreferrer" class="loc-uri-link">
                                ${locAuth.uri}
                            </a>
                        </div>
                    ` : ''}
                    ${uniqueVariantLabels.length > 0 ? `
                        <div class="variant-labels">
                            <div class="variant-labels-header">Variant Forms:</div>
                            <div class="variant-labels-list">
                                ${uniqueVariantLabels.map(label => `
                                    <span class="variant-label">${escapeHtml(label)}</span>
                                `).join('')}
                            </div>
                        </div>
                    ` : ''}
                </div>
            ` : ''}

            <div class="tags-section">
                <div class="tags-header">Top User Tags (count & % of photos)</div>
                <div class="tags-list">
                    ${tagsToShow.map(tag => `
                        <div class="tag">
                            <span class="tag-name">${escapeHtml(tag.tag)}</span>
                            <span class="tag-count">${tag.count}</span>
                            <span class="tag-percentage">${tag.percentage}%</span>
                        </div>
                    `).join('')}
                </div>
                ${hasMore ? `
                    <button class="show-more-btn" data-subject="${subjectId}">
                        ${showAllTags ? 'Show Less' : `Show All ${mapping.top_tags.length} Tags`}
                    </button>
                ` : ''}
            </div>

            ${mapping.photo_ids && mapping.photo_ids.length > 0 ? `
                <div class="images-section">
                    <div class="images-header">
                        <div class="images-title">Example Images</div>
                        <button class="load-images-btn" data-subject="${subjectId}">
                            Load Example Images
                        </button>
                    </div>
                    <div class="images-grid" id="images-${subjectId}"></div>
                </div>
            ` : ''}
        </div>
    `;
}

// Toggle show more/less tags
function toggleShowMore(subjectId) {
    const index = filteredMappings.findIndex(m =>
        m.subject.replace(/[^a-zA-Z0-9]/g, '_') === subjectId
    );

    if (index !== -1) {
        filteredMappings[index].showAll = !filteredMappings[index].showAll;
        renderMappings();
    }
}

// Load more images for a subject
async function loadMoreImages(subjectId) {
    const mapping = filteredMappings.find(m =>
        m.subject.replace(/[^a-zA-Z0-9]/g, '_') === subjectId
    );

    if (!mapping || !mapping.photo_ids) return;

    // Initialize state for this subject if not exists
    if (!loadedImagesState[subjectId]) {
        loadedImagesState[subjectId] = {
            availableIds: [...mapping.photo_ids], // IDs we haven't tried yet
            successfullyLoaded: 0
        };
    }

    const state = loadedImagesState[subjectId];

    // Check if we have any IDs left to try
    if (state.availableIds.length === 0) {
        const button = document.querySelector(`.load-images-btn[data-subject="${subjectId}"]`);
        if (button) {
            button.textContent = `All Images Loaded (${state.successfullyLoaded} found)`;
            button.disabled = true;
        }
        return;
    }

    // Get container
    const container = document.getElementById(`images-${subjectId}`);
    if (!container) return;

    // Update button to show loading state
    const button = document.querySelector(`.load-images-btn[data-subject="${subjectId}"]`);
    if (button) {
        button.disabled = true;
        button.textContent = 'Loading...';
    }

    // Try to load images until we get 5 successful ones or run out of IDs
    let successCount = 0;
    let failCount = 0;
    const targetCount = IMAGES_PER_LOAD;
    const failedPhotoIds = [];

    while (successCount < targetCount && state.availableIds.length > 0) {
        // Pick a random ID from available
        const randomIndex = Math.floor(Math.random() * state.availableIds.length);
        const photoId = state.availableIds[randomIndex];

        // Remove from available list
        state.availableIds.splice(randomIndex, 1);

        // Try to load this image
        const success = await tryLoadImage(photoId, container);
        if (success) {
            successCount++;
            state.successfullyLoaded++;
        } else {
            failedPhotoIds.push(photoId);
            failCount++;
        }
    }

    // If we couldn't load 5 images, show fallback links for failed ones
    if (successCount < targetCount && failCount > 0) {
        const neededFallbacks = Math.min(targetCount - successCount, failedPhotoIds.length);
        for (let i = 0; i < neededFallbacks; i++) {
            addFallbackLink(failedPhotoIds[i], container);
        }
    }

    // Update button state
    if (button) {
        button.disabled = false;
        if (state.availableIds.length > 0) {
            button.textContent = `Load More Images (${state.availableIds.length} untried)`;
        } else {
            button.textContent = `All Images Loaded (${state.successfullyLoaded} found)`;
            button.disabled = true;
        }
    }
}

// Try to load a single image
function tryLoadImage(photoId, container) {
    return new Promise((resolve) => {
        const imageUrl = `${IMAGE_BASE_URL}${photoId}.jpg`;
        const flickrUrl = `https://www.flickr.com/photos/library_of_congress/${photoId}/`;

        // Create image element to test loading
        const testImg = new Image();
        let resolved = false;

        testImg.onload = () => {
            if (resolved) return;
            resolved = true;

            // Image loaded successfully, add to grid
            const imageItem = document.createElement('div');
            imageItem.className = 'image-item';
            imageItem.innerHTML = `
                <a href="${flickrUrl}" target="_blank" rel="noopener noreferrer">
                    <img src="${imageUrl}" alt="Flickr photo ${photoId}" loading="lazy">
                </a>
            `;
            container.appendChild(imageItem);
            resolve(true);
        };

        testImg.onerror = () => {
            if (resolved) return;
            resolved = true;
            resolve(false);
        };

        // Set timeout in case image loading hangs
        setTimeout(() => {
            if (resolved) return;
            resolved = true;
            resolve(false);
        }, 5000);

        testImg.src = imageUrl;
    });
}

// Add a fallback link for images that couldn't be loaded
function addFallbackLink(photoId, container) {
    const flickrUrl = `https://www.flickr.com/photos/library_of_congress/${photoId}/`;

    const imageItem = document.createElement('div');
    imageItem.className = 'image-item';
    imageItem.innerHTML = `
        <a href="${flickrUrl}" target="_blank" rel="noopener noreferrer" class="image-fallback">
            <div class="fallback-icon">🔗</div>
            <div class="fallback-text">View on Flickr</div>
        </a>
    `;
    container.appendChild(imageItem);
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Event listeners
searchBox.addEventListener('input', (e) => {
    filterMappings(e.target.value);
});

filterButtons.forEach(btn => {
    btn.addEventListener('click', (e) => {
        // Update active state
        filterButtons.forEach(b => b.classList.remove('active'));
        e.target.classList.add('active');

        // Sort and render
        const sortType = e.target.dataset.sort;
        sortMappings(sortType);
        renderMappings();
    });
});

// Initialize
loadData();