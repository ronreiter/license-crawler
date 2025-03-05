#!/usr/bin/env python3
import os
import json
import csv
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def json_to_csv(input_dir, output_file):
    """Convert JSON dependency files to a single CSV file."""
    print(f"Converting JSON files from {input_dir} to {output_file}")
    
    # Define CSV headers based on JSON fields
    headers = [
        'repo_name',
        'language',
        'package_name',
        'package_version',
        'package_with_version',
        'file_last_modified',
        'file_path',
        'org_name',
        'dependency_type'
    ]
    
    # Create the output directory if it doesn't exist
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Open the CSV file for writing
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()
        
        # Process all JSON files in the new directory structure (org/organization/repo.json)
        org_dir = Path(input_dir) / 'org'
        if org_dir.exists():
            for org_subdir in org_dir.iterdir():
                if not org_subdir.is_dir():
                    continue
                
                org_name = org_subdir.name
                
                # Process each JSON file in the organization directory
                for json_file in org_subdir.glob('*.json'):
                    try:
                        repo_name = json_file.stem
                        print(f"Processing {org_name}/{repo_name}...")
                        
                        with open(json_file, 'r', encoding='utf-8') as f:
                            dependencies = json.load(f)
                        
                        # Add each dependency to the CSV
                        for dep in dependencies:
                            row = dep.copy()
                            row['repo_name'] = repo_name
                            row['org_name'] = org_name
                            writer.writerow(row)
                            
                    except Exception as e:
                        print(f"Error processing {json_file}: {e}")
        
        # For backwards compatibility, also process root JSON files
        for json_file in Path(input_dir).glob('*.json'):
            try:
                repo_name = json_file.stem
                print(f"Processing root file {repo_name}...")
                
                with open(json_file, 'r', encoding='utf-8') as f:
                    dependencies = json.load(f)
                
                # Add each dependency to the CSV
                for dep in dependencies:
                    row = dep.copy()
                    row['repo_name'] = repo_name
                    row['org_name'] = ""  # No org for files in root
                    writer.writerow(row)
                    
            except Exception as e:
                print(f"Error processing {json_file}: {e}")
        
        # For backwards compatibility, also process repository subdirectories
        for repo_dir in Path(input_dir).iterdir():
            if not repo_dir.is_dir() or repo_dir.name == "org":
                continue
            
            repo_name = repo_dir.name
            
            # Process each JSON file in the repository directory
            for json_file in repo_dir.glob('*.json'):
                try:
                    print(f"Processing {repo_name}/{json_file.name}...")
                    
                    with open(json_file, 'r', encoding='utf-8') as f:
                        dependencies = json.load(f)
                    
                    # Add each dependency to the CSV
                    for dep in dependencies:
                        row = dep.copy()
                        row['repo_name'] = repo_name
                        row['org_name'] = ""  # No org for files in old structure
                        writer.writerow(row)
                        
                except Exception as e:
                    print(f"Error processing {json_file}: {e}")
    
    print(f"Conversion complete. CSV file saved to {output_file}")

def main():
    parser = argparse.ArgumentParser(description="Convert JSON dependency files to CSV")
    parser.add_argument("--input-dir", default="license_data", help="Directory containing JSON files")
    parser.add_argument("--output", default="dependencies.csv", help="Output CSV file path")
    
    args = parser.parse_args()
    json_to_csv(args.input_dir, args.output)

if __name__ == "__main__":
    main()