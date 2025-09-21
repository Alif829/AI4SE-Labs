# utils/metrics_calculator.py
import os
import lizard
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
            'name': 'unknown', 'signature': 'unknown',
            'start_line': node.start_point[0] + 1, 'end_line': node.end_point[0] + 1,
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

def get_ast_metrics(source_code: str):
    tree = parser.parse(bytes(source_code, "utf8"))
    root_node = tree.root_node
    n_ast_nodes, ast_depth, identifiers, tokens = 0, 0, set(), []
    q = [(root_node, 1)]
    while len(q) > 0:
        node, depth = q.pop(0)
        n_ast_nodes += 1
        ast_depth = max(ast_depth, depth)
        if node.type == 'identifier':
            identifiers.add(node.text.decode('utf8'))
        if not node.children:
            tokens.append(node.text.decode('utf8'))
        else:
            for child in node.children:
                q.append((child, depth + 1))
    return {"n_ast_nodes": n_ast_nodes, "ast_depth": ast_depth, "n_identifiers": len(identifiers), "vocab_size": len(set(tokens)), "code_tokens": tokens}

def get_cyclomatic_complexity(source_code: str) -> int:
    try:
        analysis = lizard.analyze_source_code("method.java", source_code)
        return next(analysis.function_list).cyclomatic_complexity
    except (StopIteration, Exception):
        return 0