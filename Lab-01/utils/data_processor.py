# utils/data_processor.py
import json

def get_qualified_name_from_path(path: str) -> str:
    """Heuristically derives a Java qualified name from a file path."""
    try:
        for src_root in ["src/main/java/", "src/java/", "src/"]:
            if src_root in path:
                start_index = path.find(src_root) + len(src_root)
                return path[start_index:].replace(".java", "").replace("/", ".")
        return path.replace(".java", "").replace("/", ".")
    except Exception:
        return ""


def format_record(commit, modification, method, metrics_data) -> dict:
    """Constructs the final JSON record for a single method."""
    repo_name = commit.project_name
    file_path = modification.new_path
    qualified_class_name = get_qualified_name_from_path(file_path)

    record = {
        "dataset_split": "train",
        "example_id": f"{repo_name}@{commit.hash[:7]}:{file_path}#{method.start_line}-{method.end_line}",
        "repo": {
            "name": repo_name,
            "url": f"https://github.com/{commit.repo_name}",
            "commit_sha": commit.hash,
            "license": commit.project_license,
        },
        "file": {"path": file_path, "language": "Java"},
        "method": {
            "name": method.name,
            "qualified_name": f"{qualified_class_name}#{method.name}",
            "start_line": method.start_line,
            "end_line": method.end_line,
            "signature": method.long_name,
            "original_code": method.source_code,
            "doc_comment": method.docstring.strip(),
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
    """Appends a JSON record to a .jsonl file."""
    with open(filepath, 'a') as f:
        f.write(json.dumps(record) + '\n')