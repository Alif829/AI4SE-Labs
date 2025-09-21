# Java Method Mining Tool

A Python-based tool for mining and analyzing Java methods from popular GitHub repositories. This tool extracts method-level code along with comprehensive metrics and metadata, outputting structured datasets suitable for machine learning research, code analysis, and software engineering studies.

## Overview

The Java Code Mining Tool automatically:
- Discovers popular Java repositories on GitHub (># stars)
- Extracts individual Java methods from recent commits
- Calculates comprehensive code metrics using AST analysis
- Outputs structured data in JSONL format for easy processing
- Handles large-scale mining with configurable limits and chunking

## Features

### 🔍 **Repository Discovery**
- Searches GitHub for popular Java repositories
- Filters by star count, language, and recent activity
- Supports authenticated API access for higher rate limits

### 🏗️ **Robust Processing**
- Tree-sitter based AST parsing for accurate code analysis
- License detection and caching
- Error handling and progress tracking
- Configurable output chunking

### 📝 **Structured Output**
- JSONL format with rich metadata
- Repository information (name, URL, commit SHA, license)
- File context (path, language)
- Method details (name, signature, line numbers, documentation)
- Complete code metrics suite

## Installation

### Prerequisites
- Python 3.9+
- Git (for cloning repositories)
- GitHub personal access token

### Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Build Tree-sitter grammar:**
   ```bash
   # First, clone the Java grammar
   git clone https://github.com/tree-sitter/tree-sitter-java.git
   
   # Test the build
   python build_test.py
   ```

3. **Configure environment:**
   Create a `.env` file with your GitHub token:
   ```
   GITHUB_TOKEN=your_personal_access_token_here
   ```

## Configuration

Edit `config.py` to customize mining parameters:

```python
# Repository filtering
STARS_THRESHOLD          # Minimum stars required
SEARCH_QUERY_LANGUAGE  # Target language

# Time range (last 365 days by default)
TO_DATE = datetime.now()
SINCE_DATE = TO_DATE - timedelta(days=365)

# Mining limits
TOTAL_METHODS_TO_MINE = 1000000  # Total methods to extract
CHUNK_SIZE = 5000               # Methods per output file

# Paths
OUTPUT_DIR = "output"           # Output directory
JAVA_GRAMMAR_PATH = 'build/my-languages.so'  # Tree-sitter grammar
```

## Usage

### Mining
```bash
python mine.py
```

## Output Format

The tool generates JSONL files with the following structure:

```json
{
  "dataset_split": "train",
  "id": "repo-name@commit:path#start-end",
  "repo": {
    "name": "repository-name",
    "url": "https://github.com/owner/repo",
    "commit_sha": "full-commit-hash",
    "license": "license-key"
  },
  "file": {
    "path": "src/main/java/com/example/Class.java",
    "language": "Java"
  },
  "method": {
    "name": "methodName",
    "qualified_name": "com.example.Class#methodName",
    "start_line": 45,
    "end_line": 67,
    "signature": "methodName(String param)",
    "original_code": "public void methodName(String param) { ... }",
    "doc_comment": "/** Method documentation */"
  },
  "code_tokens": ["public", "void", "methodName", ...],
  "metrics": {
    "cyclomatic_complexity": 3,
    "n_ast_nodes": 156,
    "ast_depth": 8,
    "n_identifiers": 12,
    "vocab_size": 45,
    "n_whitespaces": 89,
    "n_words": 67,
    "nloc": 23,
    "token_counts": 234
  }
}
```


## Metrics Explained

| Metric | Description |
|--------|-------------|
| **cyclomatic_complexity** | Number of linearly independent paths through code (branches + 1) |
| **n_ast_nodes** | Total number of nodes in the Abstract Syntax Tree |
| **ast_depth** | Maximum depth of the AST (nesting level) |
| **n_identifiers** | Number of unique identifiers (variable/method names) |
| **vocab_size** | Number of unique tokens in the code |
| **n_whitespaces** | Count of whitespace characters |
| **n_words** | Number of words in the code |
| **nloc** | Non-empty Lines of Code |
| **token_counts** | Total number of code tokens |


### Key Dependencies

- **`pydriller`** - Git repository mining
- **`tree-sitter`** - AST parsing for Java
- **`PyGithub`** - GitHub API client
- **`python-dotenv`** - Environment variable management

## Troubleshooting

### Common Issues

1. **Tree-sitter build fails:**
   ```bash
   # Ensure tree-sitter-java is cloned in the project directory
   git clone https://github.com/tree-sitter/tree-sitter-java.git
   python build_test.py
   ```

2. **GitHub rate limit exceeded:**
   - Ensure your `GITHUB_TOKEN` is set in `.env`
   - Consider reducing `TOTAL_METHODS_TO_MINE` for testing

3. **Memory issues with large repositories:**
   - Adjust `CHUNK_SIZE` to smaller values
   - Monitor system resources during mining