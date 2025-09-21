import os
import re
from tree_sitter import Language, Parser
import config
from typing import List, Dict, Any

# --- Tree-sitter Setup ---
if not os.path.exists(config.JAVA_GRAMMAR_PATH):
    Language.build_library(config.JAVA_GRAMMAR_PATH, ['tree-sitter-java'])

JAVA_LANGUAGE = Language(config.JAVA_GRAMMAR_PATH, 'java')
parser = Parser()
parser.set_language(JAVA_LANGUAGE)

def extract_java_methods(source_code: str) -> List[Dict[str, Any]]:
    if not source_code:
        return []
    
    tree = parser.parse(bytes(source_code, "utf8"))
    query = JAVA_LANGUAGE.query("(method_declaration) @method")
    methods = []
    
    for capture in query.captures(tree.root_node):
        node = capture[0]
        method_details = {
            'source_code': node.text.decode('utf8'),
            'name': 'unknown',
            'signature': 'unknown',
            'start_line': node.start_point[0] + 1,
            'end_line': node.end_point[0] + 1,
            'doc_comment': ''
        }
        
        for child in node.children:
            if child.type == 'identifier':
                method_details['name'] = child.text.decode('utf8')
            if child.type == 'formal_parameters':
                method_details['signature'] = f"{method_details['name']}{child.text.decode('utf8')}"
        
        prev_sibling = node.prev_named_sibling
        if prev_sibling and 'comment' in prev_sibling.type:
            method_details['doc_comment'] = prev_sibling.text.decode('utf8').strip()
        
        methods.append(method_details)
    
    return methods

def get_ast_metrics(source_code: str) -> Dict[str, Any]:
    """Calculate AST-based metrics for the given source code."""
    tree = parser.parse(bytes(source_code, "utf8"))
    root_node = tree.root_node
    
    n_ast_nodes = 0
    ast_depth = 0
    identifiers = set()
    tokens = []
    
    # BFS traversal
    queue = [(root_node, 1)]
    while queue:
        node, depth = queue.pop(0)
        n_ast_nodes += 1
        ast_depth = max(ast_depth, depth)
        
        if node.type == 'identifier':
            identifiers.add(node.text.decode('utf8'))
        
        if not node.children:  # Leaf node
            tokens.append(node.text.decode('utf8'))
        else:
            for child in node.children:
                queue.append((child, depth + 1))
    
    return {
        "n_ast_nodes": n_ast_nodes,
        "ast_depth": ast_depth,
        "n_identifiers": len(identifiers),
        "vocab_size": len(set(tokens)),
        "code_tokens": tokens,
        "token_counts": len(tokens)
    }

def get_cyclomatic_complexity(source_code: str) -> int:
    
    if not source_code or not source_code.strip():
        return 0

    try:
        tree = parser.parse(bytes(source_code, "utf8"))
        root_node = tree.root_node

        # default complexity = 1
        complexity = 1

        # DFS traversal
        stack = [root_node]
        while stack:
            node = stack.pop()
            node_type = node.type

            # Branching
            if node_type == "if_statement":
                complexity += 1
            elif node_type in ("for_statement", "enhanced_for_statement", "while_statement", "do_statement"):
                complexity += 1
            elif node_type == "catch_clause":
                complexity += 1
            elif node_type == "switch_label":  # each case/default adds a branch
                complexity += 1
            elif node_type == "conditional_expression":  # ternary ?:
                complexity += 1
            elif node_type == "binary_expression":
                # Check if it's && or ||
                if len(node.children) >= 3:
                    op_node = node.children[1]
                    op_text = op_node.text.decode("utf8")
                    if op_text in ("&&", "||"):
                        complexity += 1

            for child in node.children:
                stack.append(child)

        return complexity

    except Exception as e:
        print(f"[WARN] Cyclomatic complexity calculation failed: {e}")
        return 0

def get_text_metrics(source_code: str) -> Dict[str, Any]:
    
    n_whitespaces = sum(1 for char in source_code if char.isspace())
    words = re.findall(r'\b\w+\b', source_code)
    n_words = len(words)
    
    # non-empty lines of code (NLOC)
    lines = source_code.split('\n')
    nloc = sum(1 for line in lines if line.strip())
    
    return {
        "n_whitespaces": n_whitespaces,
        "n_words": n_words,
        "nloc": nloc
    }

def get_all_metrics(source_code: str) -> Dict[str, Any]:
    
    ast_metrics = get_ast_metrics(source_code)
    text_metrics = get_text_metrics(source_code)
    cyclomatic_complexity = get_cyclomatic_complexity(source_code)
    
    return {
        "ast_metrics": ast_metrics,
        "text_metrics": text_metrics,
        "cyclomatic_complexity": cyclomatic_complexity
    }

# Backward compatibility functions
def get_metrics_for_mining(source_code: str) -> Dict[str, Any]:
    
    all_metrics = get_all_metrics(source_code)
    
    return {
        "ast_metrics": all_metrics["ast_metrics"],
        "cyclomatic_complexity": all_metrics["cyclomatic_complexity"],
        "n_whitespaces": all_metrics["text_metrics"]["n_whitespaces"],
        "n_words": all_metrics["text_metrics"]["n_words"],
        "nloc": all_metrics["text_metrics"]["nloc"],
        "token_counts": all_metrics["ast_metrics"]["token_counts"]
    }