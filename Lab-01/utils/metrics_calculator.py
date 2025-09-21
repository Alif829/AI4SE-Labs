# utils/metrics_calculator.py
import os
import lizard
from tree_sitter import Language, Parser
import config

# --- Tree-sitter Setup ---
# Build the grammar library if it doesn't exist.
if not os.path.exists(config.JAVA_GRAMMAR_PATH):
    Language.build_library(
        config.JAVA_GRAMMAR_PATH,
        ['tree-sitter-java']
    )
JAVA_LANGUAGE = Language(config.JAVA_GRAMMAR_PATH, 'java')
parser = Parser()
parser.set_language(JAVA_LANGUAGE)


def get_ast_metrics(source_code: str):
    """Parses source code using Tree-sitter and computes AST-related metrics."""
    tree = parser.parse(bytes(source_code, "utf8"))
    root_node = tree.root_node
    
    n_ast_nodes, ast_depth = 0, 0
    identifiers, tokens = set(), []
    
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
                
    return {
        "n_ast_nodes": n_ast_nodes,
        "ast_depth": ast_depth,
        "n_identifiers": len(identifiers),
        "vocab_size": len(set(tokens)),
        "code_tokens": tokens,
    }


def get_cyclomatic_complexity(source_code: str) -> int:
    """Calculates cyclomatic complexity using the lizard library."""
    try:
        analysis = lizard.analyze_source_code("method.java", source_code)
        return next(analysis.function_list).cyclomatic_complexity
    except (StopIteration, Exception):
        return 0