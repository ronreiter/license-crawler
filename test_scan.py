#!/usr/bin/env python3
import json
import os
from pathlib import Path
import datetime
import tomli
from license_crawler import LicenseCrawler
import shutil

def test_python_dependencies():
    # Create a LicenseCrawler instance
    crawler = LicenseCrawler(output_dir="test_output")
    
    # Create test directories
    os.makedirs("test_repo", exist_ok=True)
    os.makedirs("poetry_test_repo", exist_ok=True)
    os.makedirs("test_output", exist_ok=True)
    
    # Copy the test files
    shutil.copy("test_pyproject.toml", "test_repo/pyproject.toml")
    shutil.copy("poetry_test_project.toml", "poetry_test_repo/pyproject.toml")
    
    # Test standard pyproject.toml
    print("\n=== Testing standard pyproject.toml ===")
    test_standard_pyproject(crawler)
    
    # Test Poetry pyproject.toml
    print("\n=== Testing Poetry pyproject.toml ===")
    test_poetry_pyproject(crawler)

def test_standard_pyproject(crawler):
    # Path to test repo
    test_repo_path = os.path.join(os.getcwd(), "test_repo")
    
    # Initialize dependencies list
    dependencies = []
    
    # Process pyproject.toml
    pyproject_path = Path(test_repo_path) / "pyproject.toml"
    last_modified = datetime.datetime.fromtimestamp(
        os.path.getmtime(pyproject_path)
    ).isoformat()
    
    with open(pyproject_path, 'rb') as f:
        data = tomli.load(f)
    
    # Get normal dependencies
    python_deps = {}
    if 'project' in data and 'dependencies' in data['project']:
        python_deps = data['project']['dependencies']
    
    # Process normal dependencies
    crawler.process_python_dependencies(python_deps, dependencies, pyproject_path, test_repo_path, last_modified, 'normal')
    
    # Get dev dependencies
    python_dev_deps = {}
    if 'project' in data and 'optional-dependencies' in data['project'] and 'dev' in data['project']['optional-dependencies']:
        python_dev_deps = data['project']['optional-dependencies']['dev']
    
    # Process dev dependencies
    crawler.process_python_dependencies(python_dev_deps, dependencies, pyproject_path, test_repo_path, last_modified, 'dev')
    
    # Write the result to a JSON file
    with open("test_output/standard_deps.json", 'w') as f:
        json.dump(dependencies, f, indent=2)
    
    print(f"Successfully extracted {len(dependencies)} dependencies from standard pyproject.toml")
    
    # Count and display normal vs dev dependencies
    normal_deps = [dep for dep in dependencies if dep.get('dependency_type') == 'normal']
    dev_deps = [dep for dep in dependencies if dep.get('dependency_type') == 'dev']
    
    print(f"Normal dependencies: {len(normal_deps)}")
    print(f"Dev dependencies: {len(dev_deps)}")

def test_poetry_pyproject(crawler):
    # Path to test repo
    poetry_repo_path = os.path.join(os.getcwd(), "poetry_test_repo")
    
    # Initialize dependencies list
    dependencies = []
    
    # Process pyproject.toml
    pyproject_path = Path(poetry_repo_path) / "pyproject.toml"
    last_modified = datetime.datetime.fromtimestamp(
        os.path.getmtime(pyproject_path)
    ).isoformat()
    
    with open(pyproject_path, 'rb') as f:
        data = tomli.load(f)
    
    # Get normal dependencies
    python_deps = {}
    if 'tool' in data and 'poetry' in data['tool'] and 'dependencies' in data['tool']['poetry']:
        python_deps = data['tool']['poetry']['dependencies']
    
    # Process normal dependencies
    crawler.process_python_dependencies(python_deps, dependencies, pyproject_path, poetry_repo_path, last_modified, 'normal')
    
    # Get dev dependencies
    python_dev_deps = {}
    if 'tool' in data and 'poetry' in data['tool'] and 'dev-dependencies' in data['tool']['poetry']:
        python_dev_deps = data['tool']['poetry']['dev-dependencies']
    # Handle newer Poetry group structure (Poetry 1.2.0+)
    elif 'tool' in data and 'poetry' in data['tool'] and 'group' in data['tool']['poetry'] and 'dev' in data['tool']['poetry']['group'] and 'dependencies' in data['tool']['poetry']['group']['dev']:
        python_dev_deps = data['tool']['poetry']['group']['dev']['dependencies']
    
    # Process dev dependencies
    crawler.process_python_dependencies(python_dev_deps, dependencies, pyproject_path, poetry_repo_path, last_modified, 'dev')
    
    # Write the result to a JSON file
    with open("test_output/poetry_deps.json", 'w') as f:
        json.dump(dependencies, f, indent=2)
    
    print(f"Successfully extracted {len(dependencies)} dependencies from Poetry pyproject.toml")
    
    # Count and display normal vs dev dependencies
    normal_deps = [dep for dep in dependencies if dep.get('dependency_type') == 'normal']
    dev_deps = [dep for dep in dependencies if dep.get('dependency_type') == 'dev']
    
    print(f"Normal dependencies: {len(normal_deps)}")
    print(f"Dev dependencies: {len(dev_deps)}")

if __name__ == "__main__":
    test_python_dependencies()