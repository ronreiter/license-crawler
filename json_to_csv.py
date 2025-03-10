#!/usr/bin/env python3
import os
import json
import csv
import argparse
import re
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def standardize_license(license_text):
    """Standardize license text by converting full license texts to standard formats."""
    if not license_text or license_text == "Unknown":
        return license_text
    
    # Standardize Apache licenses
    if any(re.search(pattern, license_text, re.IGNORECASE) for pattern in [
        r'apache.+2\.0',
        r'apache.+software.+license',
        r'apache.+license',
        r'^apache 2$',
        r'^apache 2\.0$',
        r'^apache$',
        r'^Apache Software License$',
        r'^Apache-2\.0$'
    ]) or license_text.startswith("                                   Version 2.0"):
        return "Apache 2.0 License"
    
    # Standardize MIT licenses
    if any(re.search(pattern, license_text, re.IGNORECASE) for pattern in [
        r'^mit$',
        r'^MIT License$',
        r'^MIT$'
    ]):
        return "MIT License"
    
    # Standardize BSD licenses
    if any(re.search(pattern, license_text, re.IGNORECASE) for pattern in [
        r'bsd.+license',
        r'^bsd$',
        r'^BSD License$',
        r'^BSD-2-Clause',
        r'^BSD-3-Clause',
        r'LICENSE\.BSD3'
    ]):
        return "BSD License"
    
    # Return original if no standardization was applied
    return license_text

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
        'dependency_type',
        'license'  # Add license field
    ]
    
    # Create the output directory if it doesn't exist
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Open the CSV file for writing
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers, extrasaction='ignore')
        writer.writeheader()
        
        input_path = Path(input_dir)
        
        # Check if the input directory is an organization directory (contains JSON files directly)
        if list(input_path.glob('*.json')):
            # This is an organization directory with JSON files directly inside
            org_name = input_path.name
            for json_file in input_path.glob('*.json'):
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
                        # Standardize license if present
                        if 'license' in row:
                            row['license'] = standardize_license(row['license'])
                        writer.writerow(row)
                        
                except Exception as e:
                    print(f"Error processing {json_file}: {e}")
        else:
            # Process all JSON files in the new directory structure (org/organization/repo.json)
            org_dir = input_path / 'org'
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
                                # Standardize license if present
                                if 'license' in row:
                                    row['license'] = standardize_license(row['license'])
                                writer.writerow(row)
                                
                        except Exception as e:
                            print(f"Error processing {json_file}: {e}")
            
            # Process user directory structure (user/username/repo.json)
            user_dir = input_path / 'user'
            if user_dir.exists():
                for user_subdir in user_dir.iterdir():
                    if not user_subdir.is_dir():
                        continue
                    
                    user_name = user_subdir.name
                    
                    # Process each JSON file in the user directory
                    for json_file in user_subdir.glob('*.json'):
                        try:
                            repo_name = json_file.stem
                            print(f"Processing user/{user_name}/{repo_name}...")
                            
                            with open(json_file, 'r', encoding='utf-8') as f:
                                dependencies = json.load(f)
                            
                            # Add each dependency to the CSV
                            for dep in dependencies:
                                row = dep.copy()
                                row['repo_name'] = repo_name
                                row['org_name'] = f"user/{user_name}"  # Store user info in org_name field
                                # Standardize license if present
                                if 'license' in row:
                                    row['license'] = standardize_license(row['license'])
                                writer.writerow(row)
                                
                        except Exception as e:
                            print(f"Error processing {json_file}: {e}")
            
            # For backwards compatibility, also process root JSON files
            for json_file in input_path.glob('*.json'):
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
                        # Standardize license if present
                        if 'license' in row:
                            row['license'] = standardize_license(row['license'])
                        writer.writerow(row)
                        
                except Exception as e:
                    print(f"Error processing {json_file}: {e}")
            
            # For backwards compatibility, also process repository subdirectories
            for repo_dir in input_path.iterdir():
                if not repo_dir.is_dir() or repo_dir.name in ["org", "user"]:
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
                            # Standardize license if present
                            if 'license' in row:
                                row['license'] = standardize_license(row['license'])
                            writer.writerow(row)
                            
                    except Exception as e:
                        print(f"Error processing {json_file}: {e}")
    
    print(f"Conversion complete. CSV file saved to {output_file}")

def main():
    parser = argparse.ArgumentParser(description="Convert JSON dependency files to CSV")
    parser.add_argument("--input-dir", default="license_data", help="Directory containing JSON files")
    parser.add_argument("--output", default="dependencies.csv", help="Output CSV file path")
    parser.add_argument("--org", help="Organization name to process (e.g., 'sentraio')")
    
    args = parser.parse_args()
    
    # If an organization is specified, create an organization-specific output file
    if args.org:
        # Check if the org directory exists
        org_path = Path(args.input_dir) / 'org' / args.org
        if not org_path.exists() or not org_path.is_dir():
            print(f"Error: Organization directory '{args.org}' not found")
            return
            
        # Create organization-specific output filename
        output_file = f"dependencies_{args.org}.csv"
        print(f"Processing files for organization: {args.org}")
        json_to_csv(str(org_path), output_file)
    else:
        # Process all files as before
        json_to_csv(args.input_dir, args.output)

if __name__ == "__main__":
    main()