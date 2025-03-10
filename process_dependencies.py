import csv

frontend_repos = ['sentra-app', 'sentra-app-gateway', 'sentra-auth']

with open('dependencies_sentraio.csv', 'r') as infile, open('dependencies_sentraio_processed.csv', 'w', newline='') as outfile:
    reader = csv.DictReader(infile)
    
    # Keep only the three specified columns
    fieldnames = ['package_name', 'license', 'dependency_type_final']
    
    writer = csv.DictWriter(outfile, fieldnames=fieldnames)
    writer.writeheader()
    
    for row in reader:
        # Set dependency_type_final based on rules
        if row['dependency_type'] == 'dev':
            row['dependency_type_final'] = 'dev'
        elif row['repo_name'] in frontend_repos:
            row['dependency_type_final'] = 'frontend'
        else:
            row['dependency_type_final'] = 'backend'
        
        # Create a new row with only the required columns
        filtered_row = {
            'package_name': row['package_name'],
            'license': row['license'],
            'dependency_type_final': row['dependency_type_final']
        }
        
        writer.writerow(filtered_row)

print("Processing complete. Output saved to dependencies_sentraio_processed.csv")