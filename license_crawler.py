#!/usr/bin/env python3
import os
import json
import datetime
import argparse
import subprocess
from pathlib import Path
import tempfile
import shutil
import tomli
import requests
from git import Repo
from dotenv import load_dotenv
import time
from concurrent.futures import ThreadPoolExecutor

# Load environment variables from .env file
load_dotenv()


class LicenseCrawler:
    def __init__(self, output_dir=None, org_name=None, user_name=None, fetch_licenses=True, max_workers=10):
        self.output_dir = output_dir or os.path.join(os.getcwd(), "license_data")
        self.org_name = org_name
        self.user_name = user_name
        self.fetch_licenses = fetch_licenses
        self.max_workers = max_workers
        
        # Create base output directory
        os.makedirs(self.output_dir, exist_ok=True)
        
        # If org_name is provided, create org subdirectory
        if self.org_name:
            self.output_dir = os.path.join(self.output_dir, f"org/{self.org_name}")
            os.makedirs(self.output_dir, exist_ok=True)
        # If user_name is provided, create user subdirectory
        elif self.user_name:
            self.output_dir = os.path.join(self.output_dir, f"user/{self.user_name}")
            os.makedirs(self.output_dir, exist_ok=True)
        
        # Cache for license information to avoid redundant API calls
        self.license_cache = {
            'python': {},
            'javascript': {}
        }
        
    def _fetch_licenses_batch(self, dependencies):
        """Fetch license information for multiple dependencies in parallel."""
        python_deps = []
        js_deps = []
        
        # Group dependencies by language
        for i, dep in enumerate(dependencies):
            # Skip if already has license information
            if 'license' in dep:
                continue
                
            if dep['language'] == 'python':
                python_deps.append((i, dep['package_name']))
            elif dep['language'] == 'javascript':
                js_deps.append((i, dep['package_name']))
        
        # Define worker functions
        def fetch_python_license(item):
            idx, pkg_name = item
            license_info = self.get_python_license(pkg_name)
            return (idx, license_info)
            
        def fetch_js_license(item):
            idx, pkg_name = item
            license_info = self.get_javascript_license(pkg_name)
            return (idx, license_info)
        
        # Process in parallel with rate limiting
        if python_deps or js_deps:
            print(f"Fetching license information for {len(python_deps)} Python and {len(js_deps)} JavaScript packages...")
            
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit Python license jobs
                python_futures = [executor.submit(fetch_python_license, item) for item in python_deps]
                
                # Submit JavaScript license jobs
                js_futures = [executor.submit(fetch_js_license, item) for item in js_deps]
                
                # Process Python results
                for future in python_futures:
                    try:
                        idx, license_info = future.result()
                        dependencies[idx]['license'] = license_info
                    except Exception as e:
                        print(f"Error fetching Python license: {e}")
                
                # Process JavaScript results
                for future in js_futures:
                    try:
                        idx, license_info = future.result()
                        dependencies[idx]['license'] = license_info
                    except Exception as e:
                        print(f"Error fetching JavaScript license: {e}")
            
            print("License fetching completed.")
    
    def get_python_license(self, package_name):
        """Fetch license information for a Python package from PyPI."""
        if package_name in self.license_cache['python']:
            return self.license_cache['python'][package_name]
        
        try:
            url = f"https://pypi.org/pypi/{package_name}/json"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                license_info = data.get('info', {}).get('license', 'Unknown')
                # Sometimes the license field is empty but classifiers contain license info
                if not license_info or license_info == 'UNKNOWN':
                    classifiers = data.get('info', {}).get('classifiers', [])
                    for classifier in classifiers:
                        if classifier.startswith('License ::'):
                            license_info = classifier.split(' :: ')[-1]
                            break
                
                self.license_cache['python'][package_name] = license_info
                return license_info
        except Exception as e:
            print(f"Error fetching license for Python package {package_name}: {e}")
        
        self.license_cache['python'][package_name] = 'Unknown'
        return 'Unknown'
    
    def get_javascript_license(self, package_name):
        """Fetch license information for a JavaScript package from npm registry."""
        if package_name in self.license_cache['javascript']:
            return self.license_cache['javascript'][package_name]
        
        try:
            url = f"https://registry.npmjs.org/{package_name}"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                license_info = data.get('license', 'Unknown')
                # Handle license object format
                if isinstance(license_info, dict):
                    license_info = license_info.get('type', 'Unknown')
                
                self.license_cache['javascript'][package_name] = license_info
                return license_info
        except Exception as e:
            print(f"Error fetching license for JavaScript package {package_name}: {e}")
        
        self.license_cache['javascript'][package_name] = 'Unknown'
        return 'Unknown'

    def process_python_dependencies(self, python_deps, dependencies, path, temp_dir, last_modified, dep_type):
        """Process Python dependencies and add them to the dependencies list."""
        if isinstance(python_deps, dict):
            for dep_name, dep_version in python_deps.items():
                if isinstance(dep_version, str):
                    dep_info = {
                        'language': 'python',
                        'package_name': dep_name,
                        'package_version': dep_version,
                        'package_with_version': f"{dep_name}=={dep_version}" if dep_version else dep_name,
                        'file_last_modified': last_modified,
                        'file_path': str(path.relative_to(temp_dir)),
                        'dependency_type': dep_type
                    }
                    
                    # Fetch license information if enabled
                    if self.fetch_licenses:
                        dep_info['license'] = self.get_python_license(dep_name)
                    
                    dependencies.append(dep_info)
        elif isinstance(python_deps, list):
            # Handle list-style dependencies
            for dep in python_deps:
                if isinstance(dep, str):
                    # Simple dependency string, e.g., "requests>=2.25.1"
                    parts = dep.split(">=")
                    if len(parts) > 1:
                        dep_name = parts[0].strip()
                        dep_version = ">=".join(parts[1:]).strip()
                    else:
                        parts = dep.split("==")
                        if len(parts) > 1:
                            dep_name = parts[0].strip()
                            dep_version = "==".join(parts[1:]).strip()
                        else:
                            parts = dep.split("~=")
                            if len(parts) > 1:
                                dep_name = parts[0].strip()
                                dep_version = "~=".join(parts[1:]).strip()
                            else:
                                dep_name = dep.strip()
                                dep_version = ""
                    
                    dep_info = {
                        'language': 'python',
                        'package_name': dep_name,
                        'package_version': dep_version,
                        'package_with_version': dep,
                        'file_last_modified': last_modified,
                        'file_path': str(path.relative_to(temp_dir)),
                        'dependency_type': dep_type
                    }
                    
                    # Fetch license information if enabled
                    if self.fetch_licenses:
                        dep_info['license'] = self.get_python_license(dep_name)
                    
                    dependencies.append(dep_info)
    
    def scan_repository(self, repo_url):
        """Scan a GitHub repository for dependency files."""
        repo_name = repo_url.split('/')[-1]
        if repo_url.endswith('.git'):
            repo_name = repo_name[:-4]
        
        print(f"Scanning repository: {repo_name}")
        
        # Get GitHub token from environment variable if available
        github_token = os.environ.get("GITHUB_TOKEN")
        
        # Create temporary directory for cloning
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                # Clone repository with auth if token is available
                if github_token and "github.com" in repo_url:
                    # Insert token into clone URL for auth
                    auth_url = repo_url.replace("https://", f"https://{github_token}@")
                    repo = Repo.clone_from(auth_url, temp_dir, depth=1)
                else:
                    repo = Repo.clone_from(repo_url, temp_dir, depth=1)
                
                # Find dependency files
                dependencies = []
                
                # Search for pyproject.toml
                pyproject_paths = list(Path(temp_dir).glob("**/pyproject.toml"))
                for path in pyproject_paths:
                    try:
                        last_modified = datetime.datetime.fromtimestamp(
                            os.path.getmtime(path)
                        ).isoformat()
                        
                        with open(path, 'rb') as f:
                            data = tomli.load(f)
                        
                        # Get normal dependencies
                        python_deps = {}
                        if 'project' in data and 'dependencies' in data['project']:
                            python_deps = data['project']['dependencies']
                        elif 'tool' in data and 'poetry' in data['tool'] and 'dependencies' in data['tool']['poetry']:
                            python_deps = data['tool']['poetry']['dependencies']
                        
                        # Process normal dependencies
                        self.process_python_dependencies(python_deps, dependencies, path, temp_dir, last_modified, 'normal')
                        
                        # Get dev dependencies
                        python_dev_deps = {}
                        if 'project' in data and 'optional-dependencies' in data['project'] and 'dev' in data['project']['optional-dependencies']:
                            python_dev_deps = data['project']['optional-dependencies']['dev']
                        elif 'tool' in data and 'poetry' in data['tool'] and 'dev-dependencies' in data['tool']['poetry']:
                            python_dev_deps = data['tool']['poetry']['dev-dependencies']
                        # Handle newer Poetry group structure (Poetry 1.2.0+)
                        elif 'tool' in data and 'poetry' in data['tool'] and 'group' in data['tool']['poetry'] and 'dev' in data['tool']['poetry']['group'] and 'dependencies' in data['tool']['poetry']['group']['dev']:
                            python_dev_deps = data['tool']['poetry']['group']['dev']['dependencies']
                        
                        # Process dev dependencies
                        self.process_python_dependencies(python_dev_deps, dependencies, path, temp_dir, last_modified, 'dev')
                    except Exception as e:
                        print(f"Error processing {path}: {e}")
                
                # Search for package.json
                package_json_paths = list(Path(temp_dir).glob("**/package.json"))
                for path in package_json_paths:
                    try:
                        last_modified = datetime.datetime.fromtimestamp(
                            os.path.getmtime(path)
                        ).isoformat()
                        
                        with open(path, 'r') as f:
                            data = json.load(f)
                        
                        # Process dependencies and devDependencies
                        for dep_type in ['dependencies', 'devDependencies']:
                            if dep_type in data:
                                for dep_name, dep_version in data[dep_type].items():
                                    dep_info = {
                                        'language': 'javascript',
                                        'package_name': dep_name,
                                        'package_version': dep_version,
                                        'package_with_version': f"{dep_name}@{dep_version}",
                                        'file_last_modified': last_modified,
                                        'file_path': str(path.relative_to(temp_dir)),
                                        'dependency_type': 'dev' if dep_type == 'devDependencies' else 'normal'
                                    }
                                    
                                    # Fetch license information if enabled
                                    if self.fetch_licenses:
                                        dep_info['license'] = self.get_javascript_license(dep_name)
                                    
                                    dependencies.append(dep_info)
                    except Exception as e:
                        print(f"Error processing {path}: {e}")
                
                # Fetch licenses in batch if enabled
                if self.fetch_licenses and dependencies:
                    self._fetch_licenses_batch(dependencies)
                
                # Save results
                if dependencies:
                    # Use a single directory structure, not one per repo
                    output_file = os.path.join(self.output_dir, f"{repo_name}.json")
                    with open(output_file, 'w') as f:
                        json.dump(dependencies, f, indent=2)
                    
                    print(f"Saved dependencies to {output_file}")
                    return True
                else:
                    print(f"No dependencies found for {repo_name}")
                    return False
                
            except Exception as e:
                print(f"Error scanning repository {repo_url}: {e}")
                return False
    
    def scan_github_user(self, username, max_repos=None):
        """Scan all repositories for a GitHub user."""
        api_url = f"https://api.github.com/users/{username}/repos"
        repos = []
        page = 1
        
        # Get GitHub token from environment variable if available
        github_token = os.environ.get("GITHUB_TOKEN")
        headers = {"Authorization": f"token {github_token}"} if github_token else {}
        
        if not github_token:
            print("Warning: No GITHUB_TOKEN environment variable found. API rate limits and visibility restrictions may apply.")
        
        while True:
            response = requests.get(f"{api_url}?page={page}&per_page=100", headers=headers)
            if response.status_code != 200:
                print(f"Error fetching repositories: {response.status_code}")
                if response.status_code == 403:
                    print("API rate limit may have been exceeded. Try setting a GITHUB_TOKEN environment variable.")
                break
            
            page_repos = response.json()
            if not page_repos:
                break
            
            repos.extend(page_repos)
            page += 1
            
            if max_repos and len(repos) >= max_repos:
                repos = repos[:max_repos]
                break
        
        print(f"Found {len(repos)} repositories for user {username}")
        
        for repo in repos:
            self.scan_repository(repo['clone_url'])
    
    def scan_github_org(self, org_name, max_repos=None):
        """Scan all repositories for a GitHub organization."""
        api_url = f"https://api.github.com/orgs/{org_name}/repos"
        repos = []
        page = 1
        
        # Get GitHub token from environment variable if available
        github_token = os.environ.get("GITHUB_TOKEN")
        headers = {"Authorization": f"token {github_token}"} if github_token else {}
        
        if not github_token:
            print("Warning: No GITHUB_TOKEN environment variable found. API rate limits and visibility restrictions may apply.")
        
        while True:
            response = requests.get(f"{api_url}?page={page}&per_page=100", headers=headers)
            if response.status_code != 200:
                print(f"Error fetching repositories: {response.status_code}")
                if response.status_code == 403:
                    print("API rate limit may have been exceeded. Try setting a GITHUB_TOKEN environment variable.")
                break
            
            page_repos = response.json()
            if not page_repos:
                break
            
            repos.extend(page_repos)
            page += 1
            
            if max_repos and len(repos) >= max_repos:
                repos = repos[:max_repos]
                break
        
        print(f"Found {len(repos)} repositories for organization {org_name}")
        
        for repo in repos:
            self.scan_repository(repo['clone_url'])


def install_app():
    """Install the script as a command-line application."""
    script_path = os.path.abspath(__file__)
    
    # Create setup.py
    setup_path = os.path.join(os.path.dirname(script_path), 'setup.py')
    with open(setup_path, 'w') as f:
        f.write("""
from setuptools import setup

setup(
    name="license-crawler",
    version="0.1",
    py_modules=["license_crawler"],
    install_requires=[
        "gitpython",
        "requests",
        "tomli",
        "python-dotenv",
    ],
    entry_points={
        'console_scripts': [
            'license-crawler=license_crawler:main',
        ],
    },
)
""")
    
    # Install the package
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-e", os.path.dirname(script_path)])
    print("Successfully installed license-crawler as a command-line application")


def check_github_token():
    """Check if GITHUB_TOKEN is set, and prompt the user if not."""
    if not os.environ.get("GITHUB_TOKEN"):
        print("\033[33mWarning: GITHUB_TOKEN environment variable is not set.\033[0m")
        print("Without a token, you may experience API rate limits and restricted visibility to repositories.")
        print("Visit this URL to create a token with the required permissions:")
        print("\033[36mhttps://github.com/settings/tokens/new?scopes=repo&description=License+Crawler+Access\033[0m")
        print("\nAfter creating your token, set it using:")
        print("  export GITHUB_TOKEN=your_token_here")
        print("Or add it to your ~/.bashrc or ~/.zshrc file for persistence.")
        print("\nDo you want to continue without a token? (y/n): ", end="")
        
        response = input().lower().strip()
        if response != 'y' and response != 'yes':
            print("Exiting. Please set the GITHUB_TOKEN environment variable and try again.")
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Scan GitHub repositories for dependencies")
    parser.add_argument("--install", action="store_true", help="Install as a command-line application")
    parser.add_argument("--output-dir", help="Output directory for JSON files")
    parser.add_argument("--skip-token-check", action="store_true", help="Skip the GitHub token check")
    parser.add_argument("--skip-licenses", action="store_true", help="Skip fetching license information")
    parser.add_argument("--max-workers", type=int, default=10, help="Maximum number of concurrent workers for license fetching")
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Repository command
    repo_parser = subparsers.add_parser("repo", help="Scan a single repository")
    repo_parser.add_argument("url", help="GitHub repository URL")
    
    # User command
    user_parser = subparsers.add_parser("user", help="Scan all repositories for a GitHub user")
    user_parser.add_argument("username", help="GitHub username")
    user_parser.add_argument("--max-repos", type=int, help="Maximum number of repositories to scan")
    
    # Organization command
    org_parser = subparsers.add_parser("org", help="Scan all repositories for a GitHub organization")
    org_parser.add_argument("org_name", help="GitHub organization name")
    org_parser.add_argument("--max-repos", type=int, help="Maximum number of repositories to scan")
    
    args = parser.parse_args()
    
    if args.install:
        install_app()
        return
    
    # Check for GitHub token if not explicitly skipped
    if not args.skip_token_check and args.command in ["user", "org"]:
        check_github_token()
    
    # Determine whether to fetch licenses
    fetch_licenses = not args.skip_licenses
    
    if args.command == "repo":
        crawler = LicenseCrawler(output_dir=args.output_dir, fetch_licenses=fetch_licenses, max_workers=args.max_workers)
        crawler.scan_repository(args.url)
    elif args.command == "user":
        crawler = LicenseCrawler(output_dir=args.output_dir, user_name=args.username, 
                               fetch_licenses=fetch_licenses, max_workers=args.max_workers)
        crawler.scan_github_user(args.username, max_repos=args.max_repos)
    elif args.command == "org":
        crawler = LicenseCrawler(output_dir=args.output_dir, org_name=args.org_name, 
                               fetch_licenses=fetch_licenses, max_workers=args.max_workers)
        crawler.scan_github_org(args.org_name, max_repos=args.max_repos)
    else:
        parser.print_help()


if __name__ == "__main__":
    import sys
    main()