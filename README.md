# flickr-lc-comments

## Scripts

### Comment Analysis
- **extract_random_comments.py** - Extracts a random selection of comments from the Flickr dataset for sampling and analysis.
- **count_comments_by_day.py** - Counts and aggregates comments by day to analyze temporal patterns in commenting activity.
- **count_comments_by_tag.py** - Counts comments associated with each tag to understand tag usage and engagement.
- **build_comments_for_embedding.py** - Prepares and extracts comment text data for use in machine learning embeddings.
- **build_embeddings.py** - Generates vector embeddings for comments using Google's Gemini API for semantic analysis.
- **umap_embeddings.py** - Reduces high-dimensional comment embeddings to 2D coordinates using UMAP for visualization.
- **cluster_embeddings.py** - Applies clustering algorithms (KMeans, DBSCAN, Agglomerative) to group similar comments together.
- **add_cluster_categories.py** - Adds cluster assignments from clustered data back to the original comment records.
- **sample_comments_by_category.py** - Samples representative comments from each cluster category while removing duplicates.

### Data Processing
- **jsonl_to_parquet.py** - Converts JSONL files to Parquet format for more efficient storage and querying.
- **make_histogram_data.py** - Generates weekly histogram data of comment counts grouped by year for time-series visualization.

### LLM Classification
- **test_llm.py** - Tests LLM API connection and response format for comment classification tasks.
- **llm_category_classification.py** - Uses Gemini LLM to automatically classify comment clusters into semantic categories.

### Geographic Data
- **extract_google_maps_urls.py** - Extracts Google Maps URLs from photo descriptions and comments.
- **extract_data_from_google_maps_images.py** - Extracts HDL URLs and geographic data from photo metadata.
- **expand_google_urls.py** - Expands shortened Google Maps URLs to their full form to extract coordinates.
- **extract_locations_from_expanded_urls.py** - Parses latitude and longitude coordinates from expanded Google Maps URLs.
- **flip_geojson_coords.py** - Flips GeoJSON coordinate order between [lat, lon] and [lon, lat] formats.
- **rewind_geojson.py** - Fixes GeoJSON polygon winding order using the geojson-rewind library.

### Library of Congress Integration
- **fix_incomplete_hdl_urls.py** - Repairs incomplete or malformed HDL URLs in photo descriptions.
- **download_loc_images.py** - Downloads thumbnail images from Library of Congress based on HDL URLs.
- **search_and_download_marc.py** - Searches LOC catalog by photo title and downloads matching MARC records.
- **chrome_scrape.py** - Uses Selenium to scrape LOC catalog search results for additional metadata.
- **download_marc_from_title_search.py** - Downloads MARC XML files from LOC based on title search results.
- **match_hdl_to_marc.py** - Matches MARC records to Flickr photos using HDL URLs as the linking identifier.
- **get_lccn_from_hdl.py** - Scrapes LCCN numbers from HDL URL pages using ChromeDriver.
- **get_lccn_from_hdl_part_2.py** - Processes unmapped HDL URLs to capture their redirect locations for LCCN extraction.
- **download_marc_from_lccn_mappings.py** - Downloads MARC XML files using LCCN numbers from mapping files.
- **extract_lcsh.py** - Extracts Library of Congress Subject Headings from MARC XML files and maps them to Flickr IDs.

### Subject and Tag Analysis
- **analyze_subject_collection_popularity.py** - Analyzes photo interactions (comments, tags, notes) by LC subject and collection.
- **augment_subjects_with_loc_data.py** - Enriches subject mappings with LOC authority data including variant labels.
- **analyze_subject_tag_mappings.py** - Finds recurring associations between LC subjects and user-generated tags.

### User Activity Analysis
- **analyze_20_80_rule.py** - Analyzes the Pareto principle in user participation for tags and comments to identify power users.

### Wikipedia/Wikidata Integration
- **extract_wiki_info.py** - Extracts Wikipedia and Wikidata links from photo comments and notes.
- **expand_wiki_to_data.py** - Expands Wikipedia URLs to Wikidata QIDs using Wikipedia API for entity resolution.
- **wiki_download_data.py** - Downloads Wikidata statements and builds index/label lookups for entities.
- **wiki_find_relationships.py** - Finds items that share Wikidata properties to build relationship networks.
- **wiki_build_gexf.py** - Constructs a GEXF graph file from Wikidata relationships for network visualization.
- **wiki_graph_render.py** - Renders the Wikipedia/Wikidata network graph using ForceAtlas2 layout algorithm.
- **extract_image_labels.py** - Extracts Flickr IDs from network graph nodes and matches them with photo titles.
- **extract_network_labels.py** - Fetches English labels for Wikidata entities (Q-IDs) in the network graph.
- **download_wiki_images.py** - Downloads and processes images from Wikipedia for entities in the network.
- **resize_wiki_images.py** - Resizes Wikipedia images to target dimensions and file sizes for web display.
- **test_image_resize.py** - Tests image resizing functionality on sample images.
- **convert_network_to_parquet.py** - Converts GEXF network file with layout positions to Parquet format for web visualization.
- **debug_gexf.py** - Debugging tool for inspecting GEXF file parsing and node extraction.
