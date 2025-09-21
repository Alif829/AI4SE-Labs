import os
from dotenv import load_dotenv
from pydriller import Repository
import config
from utils.github_client import find_popular_java_repos
from utils.metrics_calculator import extract_java_methods, get_all_metrics
from utils.data_processor import format_record, save_record_to_jsonl, clear_license_cache

def main():
    """Main function to orchestrate the repository mining process."""
    load_dotenv()
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        print("GITHUB_TOKEN not found in .env file. Exiting.")
        return

    os.makedirs(config.OUTPUT_DIR, exist_ok=True)

    # Clear license cache at the start of a new mining session
    clear_license_cache()

    
    repo_urls = find_popular_java_repos(github_token)
    if not repo_urls:
        print("No repositories found to mine. Exiting.")
        return

    mined_methods_count = 0
    stop_mining = False

    print("\n Starting the mining process...")
    for repo_url in repo_urls:
        if stop_mining:
            break
        
        try:
            owner, repo_name = repo_url.split('/')[-2], repo_url.split('/')[-1].replace('.git', '')
            repo_output_dir = os.path.join(config.OUTPUT_DIR, f"{owner}--{repo_name}")
            os.makedirs(repo_output_dir, exist_ok=True)
            print(f"\nProcessing repository: {repo_url}")
            print(f"  Output directory: {repo_output_dir}/")
        except IndexError:
            print(f"\n[WARN] Could not parse owner/name from URL: {repo_url}. Skipping.")
            continue
        
        methods_in_repo_count = 0  # Initialize per-repo counter
        
        try:
            authenticated_url = repo_url.replace('https://', f'https://{github_token}@')
            repo_miner = Repository(
                authenticated_url,
                since=config.SINCE_DATE,
                to=config.TO_DATE,
                only_modifications_with_file_types=['.java']
            )
            
            for commit in repo_miner.traverse_commits():
                if stop_mining:
                    break
                
                for mod in commit.modified_files:
                    if not mod.source_code:
                        continue
                    
                    extracted_methods = extract_java_methods(mod.source_code)
                    
                    for method_data in extracted_methods:
                        if mined_methods_count >= config.TOTAL_METHODS_TO_MINE:
                            stop_mining = True
                            break
                        
                        try:
                            all_metrics = get_all_metrics(method_data['source_code'])
                            record = format_record(commit,mod,method_data,all_metrics,repo_url,github_token)
                            
                            mined_methods_count += 1
                            methods_in_repo_count += 1
                            
                            # Chunk number
                            chunk_number = (methods_in_repo_count - 1) // config.CHUNK_SIZE + 1
                            output_filepath = os.path.join(repo_output_dir, f"{repo_name}_{chunk_number}.jsonl")
                            save_record_to_jsonl(record, output_filepath)
                            
                            # Progress reporting
                            if mined_methods_count % 100 == 0:
                                print(f"  ... Mined {mined_methods_count}/{config.TOTAL_METHODS_TO_MINE} methods overall")
                            
                            if methods_in_repo_count % 50 == 0:
                                print(f"    [{repo_name}] Processed {methods_in_repo_count} methods from this repo")

                        except Exception as e:
                            print(f"    [WARN] Could not process method {method_data.get('name', 'unknown')} in commit {commit.hash[:7]}. Reason: {e}")
                            continue

        except Exception as e:
            print(f"[ERROR] Failed to process repository {repo_url}: {e}")
        
        # per-repository statistics
        if methods_in_repo_count > 0:
            print(f"  Completed {repo_name}: mined {methods_in_repo_count} methods")
            chunks_created = (methods_in_repo_count - 1) // config.CHUNK_SIZE + 1
            print(f"    Created {chunks_created} chunk file(s)")

    print(f"\nMining complete!")
    print(f"  Total methods mined: {mined_methods_count}")
    print(f"  Output directory: {config.OUTPUT_DIR}/")


if __name__ == "__main__":
    main()