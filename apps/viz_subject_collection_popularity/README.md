# Subject & Collection Popularity Visualization

An interactive web interface to explore the popularity of subjects and collections in the Library of Congress Flickr archive based on user interactions (tags, comments, and notes).

## Features

- **Two Views**: Toggle between top subjects and collections
- **Multiple Sort Options**: Sort by total interactions, average per photo, photo count, comments, tags, or notes
- **Search**: Filter results in real-time
- **Flexible Display**: Show top 10, 20, 50, 100, or all results
- **Visual Charts**: Bar charts show the breakdown of tags, comments, and notes
- **Responsive Design**: Works on desktop and mobile devices
- **Blog-Ready**: Designed to be embedded in blog posts

## Usage

### Standalone

Simply open `index.html` in a web browser. The app will load data from `../../data/viz_data/subject_collection_popularity.json`.

### Embedded in a Blog

You can embed this visualization in a blog post using an iframe:

```html
<iframe
    src="apps/viz_subject_collection_popularity/index.html"
    width="100%"
    height="800"
    frameborder="0"
    style="border: 1px solid #ddd; border-radius: 8px;">
</iframe>
```

## Data Source

The visualization reads from `data/viz_data/subject_collection_popularity.json`, which contains:

- **Subjects**: Top 100 subjects by total interactions
- **Collections**: Top 20 collections by total interactions
- **Summary**: Overall statistics (total photos, tags, comments, notes)

## Files

- `index.html` - Main HTML structure and styles
- `app.js` - JavaScript application logic
- `README.md` - This file

## Browser Compatibility

Works in all modern browsers (Chrome, Firefox, Safari, Edge).
