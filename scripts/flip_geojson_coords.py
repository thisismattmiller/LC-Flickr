#!/usr/bin/env python3
"""
Flip GeoJSON coordinates from [lat, lon] to [lon, lat] or vice versa.
This fixes incorrectly ordered coordinates in GeoJSON files.

Usage:
    python flip_geojson_coords.py <file_or_directory>
"""

import json
import sys
import os
from pathlib import Path


def flip_coordinates(coords):
    """
    Recursively flip coordinates in a GeoJSON coordinate array.
    Handles nested arrays for Polygons, MultiPolygons, etc.
    """
    if not coords:
        return coords
    
    # Check if this is a coordinate pair [lon, lat] or [lat, lon]
    if len(coords) == 2 and isinstance(coords[0], (int, float)) and isinstance(coords[1], (int, float)):
        # Flip the coordinate pair
        return [coords[1], coords[0]]
    
    # Otherwise, recursively process nested arrays
    return [flip_coordinates(item) for item in coords]


def process_geojson_file(filepath):
    """
    Process a single GeoJSON file and flip its coordinates.
    """
    print(f"Processing: {filepath}")
    
    try:
        # Read the file
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        # Check if it has geometry with coordinates
        if 'geometry' in data and 'coordinates' in data['geometry']:
            # Get original bounds for verification
            orig_coords = data['geometry']['coordinates']
            
            # Sample a coordinate to check current order
            sample_coord = None
            if orig_coords and len(orig_coords) > 0:
                if isinstance(orig_coords[0], list) and len(orig_coords[0]) > 0:
                    if isinstance(orig_coords[0][0], list):
                        sample_coord = orig_coords[0][0]
                    else:
                        sample_coord = orig_coords[0]
            
            if sample_coord:
                print(f"  Original sample coordinate: {sample_coord}")
            
            # Flip the coordinates
            data['geometry']['coordinates'] = flip_coordinates(data['geometry']['coordinates'])
            
            # Sample the flipped coordinate
            flipped_coords = data['geometry']['coordinates']
            if flipped_coords and len(flipped_coords) > 0:
                if isinstance(flipped_coords[0], list) and len(flipped_coords[0]) > 0:
                    if isinstance(flipped_coords[0][0], list):
                        sample_flipped = flipped_coords[0][0]
                    else:
                        sample_flipped = flipped_coords[0]
                    print(f"  Flipped sample coordinate: {sample_flipped}")
            
            # Write back to file
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            
            print(f"  ✓ Successfully flipped coordinates in {filepath}")
            return True
            
        # Handle FeatureCollection
        elif 'type' in data and data['type'] == 'FeatureCollection' and 'features' in data:
            modified = False
            for feature in data['features']:
                if 'geometry' in feature and 'coordinates' in feature['geometry']:
                    feature['geometry']['coordinates'] = flip_coordinates(feature['geometry']['coordinates'])
                    modified = True
            
            if modified:
                with open(filepath, 'w') as f:
                    json.dump(data, f, indent=2)
                print(f"  ✓ Successfully flipped coordinates in FeatureCollection {filepath}")
                return True
            else:
                print(f"  ⚠ No coordinates found in {filepath}")
                return False
        else:
            print(f"  ⚠ No geometry with coordinates found in {filepath}")
            return False
            
    except json.JSONDecodeError as e:
        print(f"  ✗ Error: Invalid JSON in {filepath}: {e}")
        return False
    except Exception as e:
        print(f"  ✗ Error processing {filepath}: {e}")
        return False


def main():
    if len(sys.argv) != 2:
        print("Usage: python flip_geojson_coords.py <file_or_directory>")
        sys.exit(1)
    
    target = sys.argv[1]
    target_path = Path(target)
    
    if not target_path.exists():
        print(f"Error: {target} does not exist")
        sys.exit(1)
    
    files_processed = 0
    files_modified = 0
    
    if target_path.is_file():
        # Process single file
        if target_path.suffix.lower() in ['.json', '.geojson']:
            if process_geojson_file(target_path):
                files_modified += 1
            files_processed += 1
        else:
            print(f"Warning: {target} doesn't appear to be a JSON/GeoJSON file")
    
    elif target_path.is_dir():
        # Process all JSON/GeoJSON files in directory
        for filepath in target_path.glob('*.json'):
            if process_geojson_file(filepath):
                files_modified += 1
            files_processed += 1
        
        for filepath in target_path.glob('*.geojson'):
            if process_geojson_file(filepath):
                files_modified += 1
            files_processed += 1
    
    print(f"\nSummary: Modified {files_modified} out of {files_processed} files")


if __name__ == "__main__":
    main()