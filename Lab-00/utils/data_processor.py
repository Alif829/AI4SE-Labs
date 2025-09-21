import json
import os
from typing import Optional, Dict, Any
from github import Github, GithubException

class LicenseCache:
    """Cache for repository licenses to avoid redundant API calls."""
    def __init__(self):
        self._cache = {}
    
    def get(self, repo_key: str) -> Optional[str]:
        return self._cache.get(repo_key)
    
    def set(self, repo_key: str, license: Optional[str]):
        self._cache[repo_key] = license


license_cache = LicenseCache()

def get_repo_license(repo_url: str, github_token: Optional[str] = None) -> Optional[str]:
    
    try:
        parts = repo_url.replace('.git', '').rstrip('/').split('/')
        if len(parts) < 2:
            return None
        owner, repo_name = parts[-2], parts[-1]
        
        cache_key = f"{owner}/{repo_name}"
        cached_license = license_cache.get(cache_key)
        if cached_license is not None:
            return cached_license if cached_license != 'none' else None
        
        github_token = github_token or os.getenv("GITHUB_TOKEN")
        if not github_token:
            print(f"    [WARN] No GitHub token available for fetching license of {cache_key}")
            license_cache.set(cache_key, 'none')
            return None
        
        g = Github(github_token)
        repo = g.get_repo(cache_key)
        license_info = repo.get_license()
        
        if license_info and hasattr(license_info, 'license'):
            license_key = license_info.license.key
            license_cache.set(cache_key, license_key)
            print(f"    [INFO] Fetched license for {cache_key}: {license_key}")
            return license_key
        else:
            license_cache.set(cache_key, 'none')
            return None
            
    except GithubException as e:
        if e.status == 404:
            print(f"    [WARN] Repository not found or private: {repo_url}")
        elif e.status == 403:
            print(f"    [WARN] GitHub API rate limit exceeded when fetching license")
        else:
            print(f"    [WARN] GitHub API error when fetching license: {e}")
        license_cache.set(cache_key, 'none')
        return None
    except Exception as e:
        print(f"    [WARN] Unexpected error fetching license for {repo_url}: {e}")
        if 'cache_key' in locals():
            license_cache.set(cache_key, 'none')
        return None

def get_qualified_name_from_path(path: str) -> str:
    """Extract qualified class name from file path."""
    try:
        for src_root in ["src/main/java/", "src/java/", "src/"]:
            if src_root in path:
                start_index = path.find(src_root) + len(src_root)
                return path[start_index:].replace(".java", "").replace("/", ".")
        return path.replace(".java", "").replace("/", ".")
    except Exception:
        return ""

def format_record(commit, modification, method_data: Dict[str, Any], metrics_data: Dict[str, Any], 
                  repo_url: str,github_token: Optional[str] = None) -> Dict[str, Any]:
    
    repo_name = commit.project_name
    file_path = modification.new_path
    qualified_class_name = get_qualified_name_from_path(file_path)
    repo_license = get_repo_license(repo_url, github_token)
    
    if "text_metrics" in metrics_data:
        n_whitespaces = metrics_data["text_metrics"]["n_whitespaces"]
        n_words = metrics_data["text_metrics"]["n_words"]
        nloc = metrics_data["text_metrics"]["nloc"]
        token_counts = metrics_data["ast_metrics"]["token_counts"]
    else:
        n_whitespaces = metrics_data.get("n_whitespaces", 0)
        n_words = metrics_data.get("n_words", 0)
        nloc = metrics_data.get("nloc", 0)
        token_counts = metrics_data.get("token_counts", len(metrics_data["ast_metrics"]["code_tokens"]))
    
    record = {
        "dataset_split": "train",
        "id": f"{repo_name}@{commit.hash[:7]}:{file_path}#{method_data['start_line']}-{method_data['end_line']}",
        "repo": {
            "name": repo_name,
            "url": repo_url.replace('.git', ''),
            "commit_sha": commit.hash,
            "license": repo_license,
        },
        "file": {
            "path": file_path,
            "language": "Java"
        },
        "method": {
            "name": method_data['name'],
            "qualified_name": f"{qualified_class_name}#{method_data['name']}",
            "start_line": method_data['start_line'],
            "end_line": method_data['end_line'],
            "signature": method_data['signature'],
            "original_code": method_data['source_code'],
            "doc_comment": method_data['doc_comment'],
        },
        "code_tokens": metrics_data["ast_metrics"]["code_tokens"],
        "metrics": {
            "cyclomatic_complexity": metrics_data["cyclomatic_complexity"],
            "n_ast_nodes": metrics_data["ast_metrics"]["n_ast_nodes"],
            "ast_depth": metrics_data["ast_metrics"]["ast_depth"],
            "n_identifiers": metrics_data["ast_metrics"]["n_identifiers"],
            "vocab_size": metrics_data["ast_metrics"]["vocab_size"],
            "n_whitespaces": n_whitespaces,
            "n_words": n_words,
            "nloc": nloc,
            "token_counts": token_counts
        }
    }
    return record

def save_record_to_jsonl(record: Dict[str, Any], filepath: str):
    with open(filepath, 'a') as f:
        f.write(json.dumps(record) + '\n')

def clear_license_cache():
    global license_cache
    license_cache = LicenseCache()