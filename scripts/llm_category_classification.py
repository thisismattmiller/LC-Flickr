#!/usr/bin/env python3
from glob import escape
import json
import os
import sys
import time
from pathlib import Path
from datetime import datetime
from google import genai
from google.genai import types


def load_comments_data(filepath):
    """Load the simplified comments data."""
    print(f"Loading comments from {filepath}...")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"  Loaded {len(data)} categories")
    
    # Show summary
    total_comments = sum(len(cat['comments']) for cat in data)
    print(f"  Total comments: {total_comments:,}")
    
    return data


def classify_category(category_data, client, model="gemini-2.5-flash", max_comments=500):
    """Send comments to LLM for classification."""
    category_id = category_data['category']
    comments = category_data['comments'][:max_comments]  # Limit to max_comments
    
    # Prepare the prompt
    prompt = """Here is a sample of Flickr Comments on an historical photograph. I want you to return in a few words the type of comments they are, a classification of sorts, there are 38 groups in total, so the category should be specific to what the comments seem to all have in common the most. If there seems to be mutiple catagories that are very different go with the one that is more prevelant. Just return the calssfication, no other descriptior or reasoning text please. Here are the comments:

"""
    
    # Add each comment on a new line
    for comment in comments:
        # Clean comment text (remove excessive whitespace)
        cleaned_comment = ' '.join(comment.split())
        # escape any HTML code in the comment
        cleaned_comment = escape(cleaned_comment)
        # remove any < or > or & with the escaped versions:
        cleaned_comment = cleaned_comment.replace("<", "&lt;").replace(">", "&gt;").replace("&", "&amp;")

        if cleaned_comment:
            prompt += cleaned_comment + "\n"
    


    client = genai.Client(
        api_key=os.environ.get("GEMINI_API_KEY"),
    )
    print("SENDING")
    print(prompt)
    model = "gemini-2.5-flash"
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=prompt),
            ],
        ),
    ]
    generate_content_config = types.GenerateContentConfig(
        thinking_config = types.ThinkingConfig(
            thinking_budget=24576,
        ),
    )


    classification_results = ""

    for chunk in client.models.generate_content_stream(
        model=model,
        contents=contents,
        config=generate_content_config,
    ):

        print("Getting response...",flush=True)
        if chunk != None and chunk.text:
            classification_results += chunk.text


    # Extract the classification
    classification_results = classification_results.strip()

    # Clean up the classification (remove any extra text if present)
    # Take only the first line if multiple lines
    if '\n' in classification_results:
        classification_results = classification_results.split('\n')[0].strip()
    
    return classification_results










    # print("PROMPT:\n",prompt)
    # # Create the request
    # contents = [
    #     types.Content(
    #         role="user",
    #         parts=[
    #             types.Part.from_text(text=prompt),
    #         ],
    #     ),
    # ]
    
    # try:
    #     print("Sending request...")
    #     generate_content_config = types.GenerateContentConfig(
    #         temperature=1,
    #         response_mime_type="text/plain",
    #         thinking_config=types.ThinkingConfig(
    #             thinking_budget=-1,
    #         ),
    #     )
        
    #     classification = ""
    #     for chunk in client.models.generate_content_stream(
    #         model=model,
    #         contents=contents,
    #         config=generate_content_config,
    #     ):
    #         print("Getting response...",flush=True)
    #         if chunk != None and chunk.text:
    #             classification += chunk.text
        
        
    #     # Extract the classification
    #     classification = classification.strip()
        
    #     # Clean up the classification (remove any extra text if present)
    #     # Take only the first line if multiple lines
    #     if '\n' in classification:
    #         classification = classification.split('\n')[0].strip()
        
    #     return classification
        
    # except Exception as e:
    #     print(f"    Error classifying category {category_id}: {e}")
    #     return f"Error: {str(e)}"


def load_existing_results(output_file):
    """Load existing results if available."""
    if output_file.exists():
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                results = json.load(f)
            return results
        except Exception as e:
            print(f"Warning: Could not load existing results: {e}")
    return None


def save_results(results, output_file):
    """Save results to file."""
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)


def classify_all_categories(data, output_file, delay=1.0):
    """Classify all categories and save results incrementally."""
    
    # Check for API key
    if not os.environ.get("GEMINI_API_KEY"):
        print("Error: GEMINI_API_KEY environment variable not set")
        print("Please set it with: export GEMINI_API_KEY='your-api-key'")
        sys.exit(1)
    
    print("\nInitializing Gemini client...")
    client = genai.Client(
        api_key=os.environ.get("GEMINI_API_KEY"),
    )
    
    # Check for existing results to resume from
    results = load_existing_results(output_file)
    
    if results and 'classifications' in results:
        existing_count = len(results['classifications'])
        if existing_count > 0:
            print(f"Found existing results with {existing_count} classifications")
            response = input("Resume from existing progress? (y/n): ")
            if response.lower() != 'y':
                results = None
    
    # Initialize results if not resuming
    if not results:
        results = {
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'source_file': 'comments_by_category_simple.json',
                'model': 'gemini-2.5-flash',
                'total_categories': len(data),
                'max_comments_per_category': 1000,
                'last_updated': datetime.now().isoformat()
            },
            'classifications': {}
        }
        print(f"Starting fresh classification of {len(data)} categories...")
    else:
        # Update metadata for resumed run
        results['metadata']['last_updated'] = datetime.now().isoformat()
        print(f"Resuming classification...")
    
    print(f"Using {delay} second delay between API calls\n")
    
    # Track progress
    total_to_process = len(data)
    already_processed = set(results['classifications'].keys())
    processed_count = len(already_processed)
    
    for i, category_data in enumerate(data, 1):
        category_id = str(category_data['category'])
        
        # Check if already processed and has a valid classification
        if category_id in already_processed:
            existing_classification = results['classifications'][category_id].get('classification', '')
            if existing_classification and existing_classification.strip():
                print(f"[{i}/{total_to_process}] Category {category_id} already classified: '{existing_classification}'")
                continue
            else:
                print(f"[{i}/{total_to_process}] Category {category_id} has empty classification, retrying...")
        
        num_comments = len(category_data['comments'])
        
        print(f"[{i}/{total_to_process}] Classifying category {category_id} ({num_comments} comments)...", end=' ')
        
        try:
            # Get classification
            classification = classify_category(category_data, client)
            
            # Store result
            results['classifications'][category_id] = {
                'category_id': int(category_id),
                'classification': classification,
                'num_comments': num_comments,
                'sample_comments': category_data['comments'][:3],  # Store first 3 as samples
                'classified_at': datetime.now().isoformat()
            }
            
            print(f"→ '{classification}'")
            
            # Save after each successful classification
            results['metadata']['last_updated'] = datetime.now().isoformat()
            save_results(results, output_file)
            
            # Only increment processed_count if this was a new classification (not a retry)
            if category_id not in already_processed:
                processed_count += 1
            
        except Exception as e:
            print(f"→ Error: {e}")
            # Save even on error to preserve progress
            save_results(results, output_file)
        
        # Rate limiting delay (except for last item)
        if i < total_to_process:
            time.sleep(delay)
    
    print(f"\nClassification complete! Processed {processed_count} categories.")
    return results


def print_summary(results):
    """Print a summary of the classifications."""
    print("\n" + "="*60)
    print("CLASSIFICATION SUMMARY")
    print("="*60)
    
    classifications = results['classifications']
    
    # Get all unique classifications
    unique_classifications = {}
    for cat_id, data in classifications.items():
        classification = data['classification']
        if classification not in unique_classifications:
            unique_classifications[classification] = []
        unique_classifications[classification].append(int(cat_id))
    
    print(f"\n📊 Statistics:")
    print(f"  • Total categories classified: {len(classifications)}")
    print(f"  • Unique classifications: {len(unique_classifications)}")
    
    print(f"\n🏷️  Classifications by Category:")
    for cat_id in sorted(classifications.keys(), key=int):
        data = classifications[cat_id]
        print(f"  Category {int(cat_id):2d}: {data['classification']}")
    
    print(f"\n📑 Grouped by Classification:")
    for classification, category_ids in sorted(unique_classifications.items()):
        if len(category_ids) > 1:
            print(f"  '{classification}': Categories {sorted(category_ids)}")
        else:
            print(f"  '{classification}': Category {category_ids[0]}")
    
    # Check for errors
    error_count = sum(1 for data in classifications.values() if data['classification'].startswith('Error:'))
    if error_count > 0:
        print(f"\n⚠️  Warning: {error_count} categories had classification errors")


def main():
    # Set up paths
    script_dir = Path(__file__).parent
    data_dir = script_dir.parent / 'data'
    
    input_file = data_dir / 'comments_by_category_simple.json'
    output_file = data_dir / 'category_classifications.json'
    
    # Check if input file exists
    if not input_file.exists():
        print(f"Error: Input file not found: {input_file}")
        print("Please run sample_comments_by_category.py first.")
        sys.exit(1)
    
    # Parse command line arguments
    delay = 10.0  # Default delay between API calls
    if len(sys.argv) > 1:
        try:
            delay = float(sys.argv[1])
            print(f"📌 Using custom delay: {delay} seconds between API calls")
        except ValueError:
            print(f"Warning: Invalid delay '{sys.argv[1]}', using default: 1.0 seconds")
    
    # No need to check for existing file here - the classify_all_categories function handles it
    
    try:
        print("="*60)
        print("LLM CATEGORY CLASSIFICATION")
        print("="*60)
        
        # Load data
        data = load_comments_data(input_file)
        
        # Classify all categories
        results = classify_all_categories(data, output_file, delay=delay)
        
        # Print summary
        print_summary(results)
        
        print(f"\n✅ Classification complete!")
        print(f"   Results saved to: {output_file}")
        
        print(f"\n💡 Usage notes:")
        print(f"  • Classifications are stored in 'classifications' field")
        print(f"  • Each classification includes the category ID and comment count")
        print(f"  • Sample comments are included for reference")
        
        print(f"\n🔧 Adjust API rate limiting:")
        print(f"   python {Path(__file__).name} <delay_seconds>")
        print(f"   Example: python {Path(__file__).name} 2.0  # 2 second delay")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Classification interrupted by user")
        print("   Partial results may have been saved")
        sys.exit(1)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()