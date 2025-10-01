#!/usr/bin/env python3

import json
import os
import re
import time
import requests
from collections import defaultdict

def extract_lat_lng_from_expanded_url(url):
    """Extract latitude and longitude from expanded Google Maps URL"""
    if not url:
        return None, None
    
    # Look for pattern like @39.909327,-74.1549075 in the URL
    at_pattern = r'@(-?\d+\.?\d*),(-?\d+\.?\d*)'
    matches = re.search(at_pattern, url)
    if matches:
        return float(matches.group(1)), float(matches.group(2))
    
    return None, None

def geocode_location(lat, lng, api_key):
    """
    Use Google Geocoding API to get location details from coordinates.
    Returns state (if US) or country name.
    """
    try:
        # Google Geocoding API endpoint
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {
            'latlng': f'{lat},{lng}',
            'key': api_key,
            'result_type': 'administrative_area_level_1|country'
        }
        
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            data = response.json()
            
            if data['status'] == 'OK' and data['results']:
                # Parse the results
                country = None
                state = None
                
                for result in data['results']:
                    for component in result.get('address_components', []):
                        types = component.get('types', [])
                        
                        # Check for country
                        if 'country' in types:
                            country = component.get('long_name')
                            country_code = component.get('short_name')
                        
                        # Check for state (administrative_area_level_1)
                        if 'administrative_area_level_1' in types:
                            state = component.get('long_name')
                            state_code = component.get('short_name')
                
                # Return appropriate location
                if country == 'United States' and state:
                    return {'type': 'US_STATE', 'state': state, 'country': 'USA'}
                elif country:
                    return {'type': 'INTERNATIONAL', 'country': country}
                else:
                    return {'type': 'UNKNOWN'}
            elif data.get('status') == 'REQUEST_DENIED':
                # Provide detailed error information for REQUEST_DENIED
                error_msg = data.get('error_message', 'No error message provided')
                print(f"\n  ❌ GEOCODING API REQUEST DENIED!")
                print(f"  Error message: {error_msg}")
                print(f"  Possible causes:")
                print(f"    1. API key is invalid or not activated")
                print(f"    2. Geocoding API is not enabled for this project")
                print(f"    3. API key restrictions don't allow this request")
                print(f"    4. Billing is not enabled on the Google Cloud project")
                print(f"\n  To fix:")
                print(f"    1. Check your API key at: https://console.cloud.google.com/apis/credentials")
                print(f"    2. Enable Geocoding API at: https://console.cloud.google.com/apis/library/geocoding-backend.googleapis.com")
                print(f"    3. Check billing at: https://console.cloud.google.com/billing")
                return {'type': 'ERROR', 'message': f'REQUEST_DENIED: {error_msg}'}
            else:
                status = data.get('status', 'UNKNOWN')
                error_msg = data.get('error_message', '')
                print(f"  Geocoding API returned status: {status}")
                if error_msg:
                    print(f"  Error message: {error_msg}")
                return {'type': 'ERROR', 'message': f'{status}: {error_msg}' if error_msg else status}
        else:
            print(f"  Geocoding API request failed with status code: {response.status_code}")
            print(f"  Response: {response.text[:500]}")  # Show first 500 chars of response
            return {'type': 'ERROR', 'message': f'HTTP {response.status_code}'}
    
    except Exception as e:
        print(f"  Error geocoding location: {e}")
        return {'type': 'ERROR', 'message': str(e)}

def save_data(data, output_file):
    """Save data to JSON file"""
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def main():
    """Extract coordinates from expanded URLs and identify locations using Google Geocoding"""
    
    # Get API key from environment or prompt user
    api_key = os.environ.get('GOOGLE_MAPS_API_KEY')
    if not api_key:
        print("Google Maps API Key not found in environment variables.")
        print("Please enter your Google Maps API Key (or set GOOGLE_MAPS_API_KEY environment variable):")
        api_key = input().strip()
        if not api_key:
            print("API key is required for geocoding. Exiting.")
            return
    
    # Input and output files
    input_file = os.path.join('..', 'data', 'mapping_data.json')
    output_file = os.path.join('..', 'data', 'mapping_data_with_locations.json')
    
    # Load the JSON data
    print(f"Loading data from {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"Loaded {len(data)} records")
    
    # Quick scan to see how many need processing
    needs_processing = 0
    for record in data:
        if 'location_state' not in record and 'location_country' not in record:
            needs_processing += 1
    
    if needs_processing == 0:
        print(f"✅ All {len(data)} records have already been geocoded!")
        print("Nothing to process. Exiting.")
        return
    else:
        print(f"📍 {needs_processing} records need geocoding ({len(data) - needs_processing} already processed)")
        print(f"Starting geocoding process...\n")
    
    # Track locations
    us_states = defaultdict(list)
    countries = defaultdict(list)
    no_expanded_url = []
    no_coords_from_expanded = []
    geocoding_errors = []
    successful_geocoding = 0
    already_processed = 0
    
    # Process each record
    for idx, record in enumerate(data, 1):
        photo_id = record.get('photo_id', 'unknown')
        title = record.get('title', 'No title')[:50]
        
        # Check if already processed (for resumability) - skip silently
        if 'location_state' in record or 'location_country' in record:
            already_processed += 1
            
            # Add to summary for statistics (silently)
            if 'location_state' in record:
                location_info = {
                    'photo_id': photo_id,
                    'title': title,
                    'lat': record.get('latitude_from_expanded', record.get('latitude')),
                    'lng': record.get('longitude_from_expanded', record.get('longitude')),
                    'url': record.get('google_maps_url_expanded', record.get('google_maps_url'))
                }
                us_states[record['location_state']].append(location_info)
            elif 'location_country' in record:
                location_info = {
                    'photo_id': photo_id,
                    'title': title,
                    'lat': record.get('latitude_from_expanded', record.get('latitude')),
                    'lng': record.get('longitude_from_expanded', record.get('longitude')),
                    'url': record.get('google_maps_url_expanded', record.get('google_maps_url'))
                }
                countries[record['location_country']].append(location_info)
            continue
        
        # First try to use existing coordinates if available
        lat = record.get('latitude')
        lng = record.get('longitude')
        
        # If no existing coordinates, try to extract from expanded URL
        if lat is None or lng is None:
            expanded_url = record.get('google_maps_url_expanded')
            
            if expanded_url:
                lat, lng = extract_lat_lng_from_expanded_url(expanded_url)
                if lat is not None and lng is not None:
                    # Store where we got the coordinates from
                    record['latitude_from_expanded'] = lat
                    record['longitude_from_expanded'] = lng
            
            # If still no coordinates, can't process this record
            if lat is None or lng is None:
                no_coords_from_expanded.append({
                    'photo_id': photo_id,
                    'title': title,
                    'expanded_url': expanded_url if expanded_url else record.get('google_maps_url', '')
                })
                continue
        
        print(f"[{idx}/{len(data)}] Geocoding {photo_id}: {title}...")
        print(f"  Coordinates: {lat:.6f}, {lng:.6f}")
        
        # Geocode the location
        location_result = geocode_location(lat, lng, api_key)
        
        # Get the URL for the location info
        url = record.get('google_maps_url_expanded', record.get('google_maps_url', ''))
        
        location_info = {
            'photo_id': photo_id,
            'title': title,
            'lat': lat,
            'lng': lng,
            'url': url
        }
        
        if location_result['type'] == 'US_STATE':
            state = location_result['state']
            us_states[state].append(location_info)
            record['location_state'] = state
            record['location_country'] = 'USA'
            successful_geocoding += 1
            print(f"  ✅ Located in: {state}, USA")
        elif location_result['type'] == 'INTERNATIONAL':
            country = location_result['country']
            countries[country].append(location_info)
            record['location_country'] = country
            successful_geocoding += 1
            print(f"  ✅ Located in: {country}")
        elif location_result['type'] == 'ERROR':
            geocoding_errors.append({
                'photo_id': photo_id,
                'title': title,
                'error': location_result.get('message', 'Unknown error')
            })
            print(f"  ❌ Geocoding error: {location_result.get('message', 'Unknown')}")
        else:
            record['location_country'] = 'Unknown'
            print(f"  ⚠️  Location unknown")
        
        # Save after each geocoding to allow resuming
        save_data(data, output_file)
        
        # Rate limiting - wait 2 seconds between requests to be extra safe
        if idx < len(data):  # Don't wait after the last item
            print(f"  ⏳ Waiting 2 seconds before next request...")
            time.sleep(0.1)  # 2 seconds between requests
    
    # Final save
    save_data(data, output_file)
    
    # Print summary
    print("\n" + "=" * 80)
    print("📊 LOCATION EXTRACTION SUMMARY (Using Google Geocoding API)")
    print("=" * 80)
    
    print(f"\n✅ Successfully geocoded: {successful_geocoding} locations")
    print(f"♻️  Already processed (resumed): {already_processed} records")
    print(f"❌ No expanded URL: {len(no_expanded_url)} records")
    print(f"⚠️  No coordinates available: {len(no_coords_from_expanded)} records")
    print(f"❌ Geocoding errors: {len(geocoding_errors)} records")
    
    # Print US States summary
    if us_states:
        print("\n🇺🇸 US STATES:")
        print("-" * 40)
        total_us = sum(len(photos) for photos in us_states.values())
        print(f"Total US locations: {total_us}\n")
        
        for state in sorted(us_states.keys()):
            photos = us_states[state]
            print(f"{state}: {len(photos)} location(s)")
    
    # Print Countries summary
    if countries:
        print("\n🌍 OTHER COUNTRIES:")
        print("-" * 40)
        total_intl = sum(len(photos) for photos in countries.values())
        print(f"Total international locations: {total_intl}\n")
        
        for country in sorted(countries.keys()):
            photos = countries[country]
            print(f"{country}: {len(photos)} location(s)")
    
    # Create location summary file
    summary_file = os.path.join('..', 'data', 'location_summary.json')
    summary = {
        'total_records': len(data),
        'successful_geocoding': successful_geocoding,
        'already_processed': already_processed,
        'us_states': {state: len(photos) for state, photos in us_states.items()},
        'countries': {country: len(photos) for country, photos in countries.items()},
        'us_states_details': dict(us_states),
        'countries_details': dict(countries),
        'no_expanded_url_count': len(no_expanded_url),
        'no_coords_count': len(no_coords_from_expanded),
        'geocoding_errors_count': len(geocoding_errors),
        'geocoding_errors': geocoding_errors[:10]  # Save first 10 errors for debugging
    }
    
    print(f"\n💾 Saving location summary to {summary_file}...")
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    print("\n✨ Done! Check the following files:")
    print(f"  - {output_file} (full data with locations)")
    print(f"  - {summary_file} (location summary)")
    
    if geocoding_errors:
        print("\n⚠️ Note: Some geocoding errors occurred. Check the summary file for details.")

if __name__ == "__main__":
    main()