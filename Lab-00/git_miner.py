#!/usr/bin/env python3
"""
git_miner.py

Snapshot miner for Java methods using:
 - GitHub search (language:Java stars:>X fork:false pushed:>DATE)
 - Clone HEAD (shallow)
 - Parse Java files with Tree-Sitter (java grammar)
 - Compute cyclomatic complexity with Lizard
 - Compute AST metrics (node counts, identifiers, depth, errors) with Tree-Sitter
 - Tokenize methods (subtokenize identifiers)
"""

import os
import sys
import json
import argparse
from dotenv import load_dotenv
import hashlib
import shutil
from pathlib import Path
from datetime import datetime, timedelta, timezone
from tqdm import tqdm
import logging
import ctypes

# external libs
from github import Github
from git import Repo
from tree_sitter import Language, Parser
import lizard
import importlib.metadata

# Load .env
load_dotenv()

# ---------- Config / Defaults ----------
DEFAULT_TREE_SITTER_LIB = "build/my-languages.so"
JAVA_LANG = "java"
DEFAULT_CLONE_DIR = "./repos_clone"
DEFAULT_OUT_DIR = "./methods_out"
DEFAULT_TARGET_METHODS = 25000
DEFAULT_STARS = 4000
DEFAULT_PUSHED_DAYS = 30
DEFAULT_CHUNK_SIZE = 5000
DEFAULT_MAX_REPOS = 500
MIN_TOKENS = 3
MAX_TOKENS = 2000

# ---------- Logging ----------
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
)
logger = logging.getLogger("miner")

# ---------- Utilities ----------
def sha1_hex(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()

def subtokenize_identifier(ident: str):
    """
    Splits identifiers by camelCase, snake_case, and digits.
    """
    import re
    parts = re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?![a-z])|\d+", ident)
    return [p.lower() for p in parts] if parts else [ident.lower()]

def node_text(node, source_bytes):
    return source_bytes[node.start_byte: node.end_byte].decode('utf8', errors='replace')

# ---------- Tree-sitter helpers ----------
def load_tree_sitter(lib_path: str):
    if not os.path.exists(lib_path):
        raise FileNotFoundError(f"Tree-sitter lib not found at {lib_path}. Build it first.")
    # Try preferred API: Language(lib_path, language_name)
    try:
        JAVA = Language(lib_path, JAVA_LANG)
        parser = Parser()
        try:
            parser.set_language(JAVA)
        except Exception:
            parser.language = JAVA
        return parser
    except Exception:
        logger.debug("Language(lib_path, name) failed, trying ctypes symbol fallback")

    # Fallback using ctypes: call exported language symbol to obtain a pointer
    try:
        cdll = ctypes.CDLL(lib_path)
    except Exception as e:
        raise RuntimeError(f"Failed to load shared library {lib_path}: {e}")

    symbol_candidates = [f"tree_sitter_{JAVA_LANG}", f"{JAVA_LANG}", f"tree_sitter_{JAVA_LANG}_language"]
    ptr = None
    for sym in symbol_candidates:
        try:
            func = getattr(cdll, sym)
            func.restype = ctypes.c_void_p
            ptr = func()
            logger.debug("Found symbol %s -> ptr %s", sym, ptr)
            break
        except Exception:
            continue

    if not ptr:
        raise RuntimeError(f"Could not find language symbol in {lib_path}; looked for {symbol_candidates}")

    try:
        JAVA = Language(int(ptr))
    except Exception as e:
        raise RuntimeError(f"Failed to construct Language from pointer: {e}")

    parser = Parser()
    try:
        parser.set_language(JAVA)
    except Exception:
        parser.language = JAVA
    return parser

def compute_ast_metrics(node, source_bytes):
    """Traverse subtree and compute: node_count, identifier_count, max_depth, error_nodes_text_list."""
    total_nodes = 0
    id_count = 0
    max_depth = 0
    error_nodes = []
    stack = [(node, 0)]
    while stack:
        nd, depth = stack.pop()
        total_nodes += 1
        ntype = nd.type or ""
        if ntype in ("identifier", "type_identifier"):
            id_count += 1
        if "error" in ntype.lower() or ntype == "ERROR":
            try:
                error_nodes.append(node_text(nd, source_bytes))
            except Exception:
                error_nodes.append("<unreadable-error-node>")
        if depth > max_depth:
            max_depth = depth
        for c in nd.children:
            stack.append((c, depth + 1))
    return {
        "ast_node_count": total_nodes,
        "identifier_count": id_count,
        "ast_max_depth": max_depth,
        "ast_error_count": len(error_nodes),
        "ast_error_nodes": error_nodes,
    }

DECISION_TYPES = {
    "if_statement", "for_statement", "while_statement", "do_statement",
    "switch_statement", "synchronized_statement", "catch_clause", "conditional_expression"
}

def cc_from_ast(node, source_bytes):
    """Compute cyclomatic complexity using AST."""
    decision_count = 0
    stack = [node]
    while stack:
        nd = stack.pop()
        if nd.type in DECISION_TYPES:
            decision_count += 1
        stack.extend(nd.children)
    code_fragment = source_bytes[node.start_byte: node.end_byte].decode('utf8', errors='replace')
    logical_ops = code_fragment.count("&&") + code_fragment.count("||")
    cc = 1 + decision_count + logical_ops
    return int(cc)

def tokenize_method_with_tree_sitter(node, source_bytes):
    """
    Tokenizes a method AST node using Tree-Sitter only.
    - Identifiers are subtokenized
    - Literals normalized (__NUM__, __STR__)
    - Operators and keywords included
    """
    tokens = []

    def visit(n):
        ntype = n.type
        text = node_text(n, source_bytes)
        if ntype in ("identifier", "type_identifier"):
            tokens.extend(subtokenize_identifier(text))
        elif ntype in ("integer_literal", "decimal_integer_literal", "floating_point_literal"):
            tokens.append("__NUM__")
        elif ntype in ("string_literal", "character_literal"):
            tokens.append("__STR__")
        elif ntype in ("true", "false", "null"):
            tokens.append(text.lower())
        elif n.children:
            for c in n.children:
                visit(c)
        else:
            tokens.append(text)

    visit(node)
    return tokens

# ---------- Lizard helpers ----------
def analyze_file_with_lizard(filename, source_code):
    try:
        res = lizard.analyze_file.analyze_source_code(filename, source_code)
        return res
    except Exception as e:
        logger.warning("Lizard failed on %s: %s", filename, e)
        return None

# ---------- GitHub discovery ----------
def discover_repos(github_token, stars_cutoff, pushed_since_days, max_repos):
    gh = Github(github_token, per_page=100)
    cutoff_date = (datetime.now(timezone.utc) - timedelta(days=pushed_since_days)).date().isoformat()
    query = f"language:Java stars:>{stars_cutoff} fork:false pushed:>{cutoff_date}"
    logger.info("GitHub query: %s", query)
    results = gh.search_repositories(query=query, sort="stars")
    repos = []
    for i, repo in enumerate(results):
        repos.append(repo)
        if len(repos) >= max_repos:
            break
    logger.info("Discovered %d repos (capped at %d)", len(repos), max_repos)
    return repos

def clone_repo_shallow(clone_url, dest_dir, depth=1):
    if os.path.exists(dest_dir):
        shutil.rmtree(dest_dir)
    Repo.clone_from(clone_url, dest_dir, depth=depth)
    return dest_dir

# ---------- Main processing ----------
def process_repository(parser, gh_repo, dest_dir, out_buf, seen_hashes, cfg):
    repo_meta = {
        "full_name": gh_repo.full_name,
        "html_url": gh_repo.html_url,
        "stargazers_count": gh_repo.stargazers_count,
        "forks_count": gh_repo.forks_count,
        "size_kb": gh_repo.size,
        "license": gh_repo.license.spdx_id if gh_repo.license else None,
        "created_at": gh_repo.created_at.isoformat() if gh_repo.created_at else None,
        "pushed_at": gh_repo.pushed_at.isoformat() if gh_repo.pushed_at else None,
    }
    # contributor & commit info
    try:
        repo_meta["repo_contributor_count"] = gh_repo.get_contributors().totalCount
    except Exception:
        repo_meta["repo_contributor_count"] = None
    try:
        since_dt = datetime.now(timezone.utc) - timedelta(days=cfg['pushed_days'])
        repo_meta["repo_commit_freq_30d"] = gh_repo.get_commits(since=since_dt).totalCount
    except Exception:
        repo_meta["repo_commit_freq_30d"] = None

    try:
        repo_git = Repo(dest_dir)
        head_sha = repo_git.head.commit.hexsha
    except Exception:
        head_sha = None

    java_files = list(Path(dest_dir).rglob("*.java"))
    for java_file in java_files:
        try:
            src_text = java_file.read_text(encoding='utf8', errors='replace')
        except Exception:
            logger.warning("Failed to read %s", java_file)
            continue

        lizard_info = analyze_file_with_lizard(str(java_file), src_text)
        lizard_map = {}
        if lizard_info:
            for f in lizard_info.function_list:
                lizard_map.setdefault(f.start_line, []).append(f)

        source_bytes = bytes(src_text, 'utf8')
        try:
            tree = parser.parse(source_bytes)
        except Exception as e:
            logger.warning("Tree-sitter failed to parse %s: %s", java_file, e)
            continue
        root = tree.root_node

        stack = [root]
        while stack:
            node = stack.pop()
            if node.type in ("method_declaration", "constructor_declaration"):
                try:
                    tokens = tokenize_method_with_tree_sitter(node, source_bytes)
                except Exception:
                    continue  # skip if tokenization fails

                token_count = len(tokens)
                if token_count < cfg['min_tokens'] or token_count > cfg['max_tokens']:
                    continue

                ast_metrics = compute_ast_metrics(node, source_bytes)

                # Cyclomatic complexity
                start_line = node.start_point[0] + 1
                cc = None
                if start_line in lizard_map:
                    candidate = lizard_map[start_line][0]
                    cc = getattr(candidate, "cyclomatic_complexity", None)
                if cc is None:
                    try:
                        cc = cc_from_ast(node, source_bytes)
                    except Exception:
                        cc = 1

                # normalized source using Tree-Sitter
                norm_src = ""
                for n in node.children:
                    ttype = n.type
                    ttext = node_text(n, source_bytes)
                    if ttype in ("integer_literal", "decimal_integer_literal", "floating_point_literal"):
                        norm_src += "__NUM__"
                    elif ttype in ("string_literal", "character_literal"):
                        norm_src += "__STR__"
                    else:
                        norm_src += ttext

                # deduplication hash
                dup_hash = sha1_hex(repo_meta["full_name"] + ":" + str(java_file.relative_to(dest_dir)) + ":" + str(start_line) + ":" + norm_src)
                if dup_hash in seen_hashes:
                    continue
                seen_hashes.add(dup_hash)

                # method name
                mname = node.child_by_field_name("name")
                mname_str = node_text(mname, source_bytes) if mname else None
                signature = None  # not extracted here

                # dataset split
                repo_hash_int = int(sha1_hex(repo_meta["full_name"])[:8], 16)
                mod = repo_hash_int % 10
                split = "val" if mod == 8 else "test" if mod == 9 else "train"

                whitespace_count = sum(1 for ch in node_text(node, source_bytes) if ch.isspace())
                vocab_size = len(set(tokens))

                record = {
                    "id": dup_hash,
                    "repo_full_name": repo_meta["full_name"],
                    "repo_url": repo_meta["html_url"],
                    "repo_head_sha": head_sha,
                    "repo_stars": repo_meta["stargazers_count"],
                    "repo_forks": repo_meta["forks_count"],
                    "repo_license": repo_meta["license"],
                    "repo_size_kb": repo_meta["size_kb"],
                    "repo_created_at": repo_meta["created_at"],
                    "repo_pushed_at": repo_meta["pushed_at"],
                    "repo_contributor_count": repo_meta.get("repo_contributor_count"),
                    "repo_commit_freq_30d": repo_meta.get("repo_commit_freq_30d"),
                    "file_path": str(java_file.relative_to(dest_dir)),
                    "file_blob_sha": None,
                    "method_name": mname_str,
                    "signature": signature,
                    "start_line": start_line,
                    "end_line": node.end_point[0] + 1,
                    "nloc": node.end_point[0] - node.start_point[0] + 1,
                    "method_source_normalized": norm_src,
                    "original_code": node_text(node, source_bytes),
                    "code_tokens": tokens,
                    "token_count": token_count,
                    "vocab_size": vocab_size,
                    "cyclomatic_complexity": cc,
                    "ast_node_count": ast_metrics["ast_node_count"],
                    "n_identifiers": ast_metrics["identifier_count"],
                    "ast_max_depth": ast_metrics["ast_max_depth"],
                    "ast_error_count": ast_metrics["ast_error_count"],
                    "ast_error_nodes": ast_metrics["ast_error_nodes"],
                    "n_whitespaces": whitespace_count,
                    "is_generated": ("@Generated" in node_text(node, source_bytes) or "generated by" in node_text(node, source_bytes).lower()),
                    "is_test": ("test" in str(java_file).lower()),
                    "dataset_split": split,
                    "provenance": {
                        "extraction_time": datetime.now(timezone.utc).isoformat(),
                        "tree_sitter_lib": cfg['tree_sitter_lib'],
                        "lizard_version": (getattr(lizard, '__version__', None) or importlib.metadata.version('lizard'))
                    },
                    "commit_hash": head_sha
                }

                out_buf(record)

            stack.extend(reversed(node.children))

# ---------- Orchestration ----------
def run(args):
    if not args.github_token:
        logger.error("GITHUB_TOKEN required.")
        sys.exit(1)

    parser = load_tree_sitter(args.tree_sitter_lib)
    repos = discover_repos(args.github_token, args.stars, args.pushed_days, args.max_repos)
    if args.test:
        repos = repos[: min(len(repos), max(3, args.test_sample_repos))]

    os.makedirs(args.clone_dir, exist_ok=True)
    os.makedirs(args.out_dir, exist_ok=True)

    methods_collected = 0
    chunk_index = 1
    current_chunk = []
    seen_hashes = set()
    cfg = {
        "min_tokens": args.min_tokens,
        "max_tokens": args.max_tokens,
        "pushed_days": args.pushed_days,
        "tree_sitter_lib": args.tree_sitter_lib
    }

    def flush_chunk():
        nonlocal chunk_index, current_chunk
        if not current_chunk:
            return
        out_path = Path(args.out_dir) / f"methods_chunk_{chunk_index}.ndjson"
        logger.info("Writing chunk %d (%d records) to %s", chunk_index, len(current_chunk), out_path)
        with open(out_path, "w", encoding="utf8") as f:
            for item in current_chunk:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        chunk_index += 1
        current_chunk = []

    def append_record(rec):
        nonlocal methods_collected, current_chunk
        current_chunk.append(rec)
        methods_collected += 1
        if len(current_chunk) >= args.chunk_size:
            flush_chunk()

    for gh_repo in repos:
        if methods_collected >= args.target_methods:
            break
        repo_name = gh_repo.full_name.replace("/", "_")
        dest = Path(args.clone_dir) / repo_name
        logger.info("Cloning %s ...", gh_repo.full_name)
        try:
            clone_repo_shallow(gh_repo.clone_url, str(dest), depth=1)
        except Exception as e:
            logger.warning("Clone failed for %s: %s", gh_repo.full_name, e)
            continue
        try:
            process_repository(parser, gh_repo, str(dest), append_record, seen_hashes, cfg)
        except Exception as e:
            logger.exception("Processing failed for %s: %s", gh_repo.full_name, e)
        if args.cleanup:
            shutil.rmtree(dest, ignore_errors=True)
        logger.info("Collected %d methods so far", methods_collected)

    flush_chunk()
    logger.info("DONE. Total methods collected: %d", methods_collected)

# ---------- CLI ----------
def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--env_file", default=None)
    p.add_argument("--github_token", default=os.environ.get("GITHUB_TOKEN"))
    p.add_argument("--tree_sitter_lib", default=DEFAULT_TREE_SITTER_LIB)
    p.add_argument("--clone_dir", default=DEFAULT_CLONE_DIR)
    p.add_argument("--out_dir", default=DEFAULT_OUT_DIR)
    p.add_argument("--target_methods", type=int, default=DEFAULT_TARGET_METHODS)
    p.add_argument("--stars", type=int, default=DEFAULT_STARS)
    p.add_argument("--pushed_days", type=int, default=DEFAULT_PUSHED_DAYS)
    p.add_argument("--chunk_size", type=int, default=DEFAULT_CHUNK_SIZE)
    p.add_argument("--max_repos", type=int, default=DEFAULT_MAX_REPOS)
    p.add_argument("--min_tokens", type=int, default=MIN_TOKENS)
    p.add_argument("--max_tokens", type=int, default=MAX_TOKENS)
    p.add_argument("--cleanup", action="store_true")
    p.add_argument("--test", action="store_true")
    p.add_argument("--test_sample_repos", type=int, default=5)
    return p.parse_args()

if __name__ == "__main__":
    quick_p = argparse.ArgumentParser(add_help=False)
    quick_p.add_argument("--env_file", default=None)
    quick_args, _ = quick_p.parse_known_args()
    if quick_args.env_file:
        load_dotenv(quick_args.env_file)
    args = parse_args()
    if args.env_file:
        load_dotenv(args.env_file, override=True)
    run(args)
