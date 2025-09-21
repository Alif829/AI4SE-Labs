import os
from tree_sitter import Language

print("--- Attempting to build tree-sitter grammar ---")
print(f"Current working directory: {os.getcwd()}")
print("Looking for 'tree-sitter-java' folder here...")

try:
    Language.build_library(
        'build/my-languages.so',
        ['tree-sitter-java']
    )
    print("\n SUCCESS: Grammar built successfully!")
    print("A 'build' folder should now exist.")

except Exception as e:
    print("\n FAILED: An error occurred during the build.")
    print("--- THE ERROR MESSAGE IS: ---")
    print(e)
    print("------------------------------------")