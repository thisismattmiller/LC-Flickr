#!/usr/bin/env python3
"""
Count comments per category from the classification and comments data.
"""

import json
from collections import defaultdict

# Custom category labels
categories = {
    0: "Historical Context and Identification with Links",
    1: "Aesthetic Praise and Admiration",
    2: "Biographical & Historical Wikimedia Contributions",
    3: "Factual Historical Annotation",
    4: "Historical Detail Identification and Contextualization",
    5: "Explore Congratulations",
    6: "See Also",
    7: "Historical Subject Identification and Details",
    8: "Location and Status Verification",
    9: "Aesthetic Feedback",
    10: "LC Staff Thanks for Metadata Improvement",
    11: "Non-English Compliments",
    12: "Flickr Group Invitations",
    13: "Crowdsourced Historical Data Refinement",
    14: "Historical Performing Artist Biographical Documentation",
    15: "Sourced Historical Details and Context",
    16: "Flickr Group Invitations",
    17: "Flickr Group Invitations",
    18: "Location Verification and Contemporary Comparison",
    19: "Cross-referencing and Linked Information",
    20: "External Content Feature Notification",
    21: "Observations on Period Appearance",
    22: "LC Staff Thanks for Contributions",
    23: "Wikidata Zone 💪",
    24: "Factual Correction and Archival Enhancement",
    25: "Historical Factual Identification and Context",
    26: "Historical Baseball Identification and Contextualization",
    27: "Flickr Group Invitations",
    28: "Factual contributions and corrections",
    29: "Factual Identification and Historical Context",
    30: "Group Invitations",
    31: "Identification and Biographical Information of Historical Figures",
    32: "Historical Photo Annotation",
    33: "Biographical and Genealogical Identification",
    34: "Flickr Group Invitations",
    35: "Praise",
    36: "Historical Annotation",
    37: "Compliments"
}

# Count comments per category
category_counts = defaultdict(int)

with open('data/comments_with_categories.jsonl', 'r') as f:
    for line in f:
        comment = json.loads(line)
        cat_id = comment['category']
        category_counts[cat_id] += 1

# Print results sorted by category ID
print(f"{'Category ID':<12} {'Count':<10} Category Label")
print("=" * 80)

for cat_id in sorted(category_counts.keys()):
    label = categories.get(cat_id, "Unknown")
    count = category_counts[cat_id]
    print(f"{cat_id:<12} {count:<10} {label}")

print("=" * 80)
print(f"{'Total:':<12} {sum(category_counts.values()):<10}")

# Generate HTML table
html_output = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Comment Categories Count</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
        }
        table {
            border-collapse: collapse;
            width: 100%;
            max-width: 1200px;
        }
        th, td {
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }
        th {
            background-color: #4CAF50;
            color: white;
        }
        tr:nth-child(even) {
            background-color: #f2f2f2;
        }
        tr:hover {
            background-color: #ddd;
        }
        .total-row {
            font-weight: bold;
            background-color: #e0e0e0 !important;
        }
        .count {
            text-align: right;
        }
        .cat-id {
            text-align: center;
        }
    </style>
</head>
<body>
    <h1>Comment Categories Count</h1>
    <table>
        <thead>
            <tr>
                <th class="cat-id">Category ID</th>
                <th class="count">Count</th>
                <th>Category Label</th>
            </tr>
        </thead>
        <tbody>
"""

for cat_id in sorted(category_counts.keys()):
    label = categories.get(cat_id, "Unknown")
    count = category_counts[cat_id]
    html_output += f"""            <tr>
                <td class="cat-id">{cat_id}</td>
                <td class="count">{count:,}</td>
                <td>{label}</td>
            </tr>
"""

html_output += f"""        </tbody>
        <tfoot>
            <tr class="total-row">
                <td class="cat-id">Total</td>
                <td class="count">{sum(category_counts.values()):,}</td>
                <td></td>
            </tr>
        </tfoot>
    </table>
</body>
</html>
"""

with open('category_counts.html', 'w') as f:
    f.write(html_output)

print("\nHTML table saved to category_counts.html")
