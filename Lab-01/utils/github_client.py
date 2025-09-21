# utils/github_client.py
from github import Github, RateLimitExceededException
import time
import config

def find_popular_java_repos(github_token: str):
    """
    Uses the GitHub API to find popular Java repositories created within a date range.
    """
    g = Github(github_token)
    
    # Construct a query to find popular, non-forked Java repos pushed to within the date range
    query = (
        f"language:{config.SEARCH_QUERY_LANGUAGE} "
        f"stars:>{config.STARS_THRESHOLD} "
        f"fork:false "
        f"pushed:{config.SINCE_DATE.strftime('%Y-%m-%d')}..{config.TO_DATE.strftime('%Y-%m-%d')}"
    )
    
    print(f"🔍 Searching GitHub with query: \"{query}\"")
    
    try:
        repos = g.search_repositories(query=query, sort='stars', order='desc')
        repo_urls = [repo.clone_url for repo in repos]
        print(f"✅ Found {len(repo_urls)} repositories matching the criteria.")
        return repo_urls
    except RateLimitExceededException:
        print("❌ GitHub API rate limit exceeded. Please wait and try again, or use a different token.")
        return []
    except Exception as e:
        print(f"❌ An error occurred while searching for repositories: {e}")
        return []