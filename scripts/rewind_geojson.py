#!/usr/bin/env python3.12
"""
Fix GeoJSON files using geojson-rewind to ensure correct winding order.
Overwrites the original file(s) with the corrected version.
"""

import sys
import os
import json
from pathlib import Path
from geojson_rewind import rewind


def process_geojson_file(filepath):
    """Process a single GeoJSON file and overwrite it with the rewound version."""
    try:
        with open(filepath, 'r') as f:
            content = f.read()
        
        rewound = rewind(content)
        
        with open(filepath, 'w') as f:
            f.write(rewound)
        
        print(f"✓ Fixed: {filepath}")
        return True
    except Exception as e:
        print(f"✗ Error processing {filepath}: {e}", file=sys.stderr)
        return False


def process_path(path):
    """Process a single file or all .geojson files in a directory."""
    path = Path(path)
    
    if not path.exists():
        print(f"Error: Path does not exist: {path}", file=sys.stderr)
        return False
    
    success_count = 0
    error_count = 0
    
    if path.is_file():
        if path.suffix.lower() in ['.geojson', '.json']:
            if process_geojson_file(path):
                success_count += 1
            else:
                error_count += 1
        else:
            print(f"Warning: {path} does not appear to be a GeoJSON file", file=sys.stderr)
            return False
    
    elif path.is_dir():
        geojson_files = list(path.glob('**/*.geojson')) + list(path.glob('**/*.json'))
        
        if not geojson_files:
            print(f"No .geojson or .json files found in {path}")
            return False
        
        print(f"Found {len(geojson_files)} GeoJSON file(s) in {path}")
        
        for filepath in geojson_files:
            if process_geojson_file(filepath):
                success_count += 1
            else:
                error_count += 1
    
    else:
        print(f"Error: {path} is neither a file nor a directory", file=sys.stderr)
        return False
    
    print(f"\nSummary: {success_count} file(s) fixed, {error_count} error(s)")
    return error_count == 0


def main():
    if len(sys.argv) != 2:
        print("Usage: python rewind_geojson.py <file.geojson | directory>")
        print("\nExamples:")
        print("  python rewind_geojson.py data.geojson")
        print("  python rewind_geojson.py /path/to/geojson/directory")
        sys.exit(1)
    
    target_path = sys.argv[1]
    success = process_path(target_path)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()