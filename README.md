# License Crawler

A tool to scan GitHub repositories for dependency information in package.json and pyproject.toml files.

## Installation

You can install the tool directly from the source:

```bash
git clone https://github.com/yourusername/license-crawler.git
cd license-crawler
python license_crawler.py --install
```

Or install the dependencies manually with uv:

```bash
uv sync
```

### Environment Variables

The tool uses the following environment variables:

- `GITHUB_TOKEN`: GitHub personal access token for API authentication (required to avoid rate limits and to access private repositories)

You can create a `.env` file in the project root with the following content:

```
GITHUB_TOKEN=your_token_here
```

## Usage

### Scan a single repository

```bash
license-crawler repo https://github.com/username/repo
```

### Scan all repositories for a GitHub user

```bash
license-crawler user username
```

### Scan all repositories for a GitHub organization

```bash
license-crawler org organization-name
```

### Additional options

- `--output-dir PATH`: Specify custom output directory for JSON files
- `--max-repos N`: Limit the number of repositories to scan (for user and org commands)

## Output

For each scanned repository, the tool creates a JSON file in a repository-specific subdirectory within the output directory (default: `./license_data/{repo_name}/{repo_name}.json`).
Each file contains an array of dependency objects with the following information:

```json
[
  {
    "language": "python",
    "package_name": "requests",
    "package_version": "^2.28.1",
    "package_with_version": "requests==^2.28.1",
    "file_last_modified": "2023-05-01T12:34:56",
    "file_path": "pyproject.toml"
  },
  {
    "language": "javascript",
    "package_name": "react",
    "package_version": "18.2.0",
    "package_with_version": "react@18.2.0",
    "file_last_modified": "2023-05-01T12:34:56",
    "file_path": "package.json",
    "dependency_type": "normal"
  }
]
```

The `dependency_type` field shows whether the dependency is a normal dependency or a development dependency.

## Converting to CSV

You can convert the JSON output to a single CSV file using the included script:

```bash
python json_to_csv.py
```

This will process all JSON files in the license_data directory and its subdirectories, and create a consolidated CSV file.

### CSV Options

- `--input-dir PATH`: Specify custom input directory containing JSON files (default: `license_data`)
- `--output PATH`: Specify output CSV file path (default: `dependencies.csv`)

Example:
```bash
python json_to_csv.py --input-dir custom_data_dir --output dependencies/output.csv
```