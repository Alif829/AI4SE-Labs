# utils/data_processor.py
import json

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

def format_record(commit, modification, method_data: dict, metrics_data, repo_url: str) -> dict:
    """Format a method record for JSONL output."""
    repo_name = commit.project_name
    file_path = modification.new_path
    qualified_class_name = get_qualified_name_from_path(file_path)
    
    record = {
        "dataset_split": "train",
        "example_id": f"{repo_name}@{commit.hash[:7]}:{file_path}#{method_data['start_line']}-{method_data['end_line']}",
        "repo": {
            "name": repo_name,
            "url": repo_url.replace('.git', ''),
            "commit_sha": commit.hash,
            # Note: PyDriller doesn't provide license info at commit level
            # You may want to fetch this separately via GitHub API if needed
            "license": None,
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
        }
    }
    return record

def save_record_to_jsonl(record: dict, filepath: str):
    """Save a record to a JSONL file."""
    with open(filepath, 'a') as f:
        f.write(json.dumps(record) + '\n')