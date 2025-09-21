# mine.py
import os
from dotenv import load_dotenv
from pydriller import Repository
import config
from utils.github_client import find_popular_java_repos
from utils.metrics_calculator import get_ast_metrics, get_cyclomatic_complexity
from utils.data_processor import format_record, save_record_to_jsonl

def main():
    """Main function to orchestrate the repository mining process."""
    load_dotenv()
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        print("❌ GITHUB_TOKEN not found in .env file. Exiting.")
        return

    # Create the output directory if it doesn't exist
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)

    repo_urls = find_popular_java_repos(github_token)
    if not repo_urls:
        print("No repositories found to mine. Exiting.")
        return

    mined_methods_count = 0
    stop_mining = False

    print("\n🚀 Starting the mining process...")
    for repo_url in repo_urls:
        if stop_mining:
            break
        
        # Generate a unique filename for this repository's output
        try:
            owner = repo_url.split('/')[-2]
            repo_name = repo_url.split('/')[-1].replace('.git', '')
            output_filepath = os.path.join(config.OUTPUT_DIR, f"{owner}--{repo_name}.jsonl")
            print(f"\nProcessing repository: {repo_url}  ->  saving to {output_filepath}")
        except IndexError:
            print(f"\n[WARN] Could not parse owner/name from URL: {repo_url}. Skipping.")
            continue
        
        try:
            authenticated_url = repo_url.replace('https://', f'https://{github_token}@')
            repo_miner = Repository(
                authenticated_url,
                since=config.SINCE_DATE,
                to=config.TO_DATE,
                only_modifications_with_file_types=['.java']
            )
            
            for commit in repo_miner.traverse_commits():
                try:
                    if stop_mining:
                        break
                    
                    for mod in commit.modified_files:
                        if not mod.new_path or not mod.new_path.endswith(".java"):
                            continue
                        
                        for method in mod.changed_methods:
                            if not method.source_code:
                                continue

                            if mined_methods_count >= config.TOTAL_METHODS_TO_MINE:
                                stop_mining = True
                                break
                            
                            ast_metrics = get_ast_metrics(method.source_code)
                            cc = get_cyclomatic_complexity(method.source_code)
                            
                            metrics_data = {"ast_metrics": ast_metrics, "cyclomatic_complexity": cc}
                            record = format_record(commit, mod, method, metrics_data)
                            # Use the new dynamic filepath for saving
                            save_record_to_jsonl(record, output_filepath)
                            
                            mined_methods_count += 1
                            if mined_methods_count % 100 == 0:
                                print(f"  ... Mined {mined_methods_count}/{config.TOTAL_METHODS_TO_MINE} methods")

                except Exception as e:
                    print(f"    [WARN] Skipping problematic commit {commit.hash}: {e}")
                    continue

        except Exception as e:
            print(f"[ERROR] Failed to process repository {repo_url}: {e}")

    print(f"\n✅ Mining complete. Total methods mined: {mined_methods_count}.")
    print(f"Dataset saved to the '{config.OUTPUT_DIR}' directory.")


if __name__ == "__main__":
    main()