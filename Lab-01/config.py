# config.py
from datetime import datetime, timedelta

# --- GitHub Repository Search Settings ---
STARS_THRESHOLD = 1000
SEARCH_QUERY_LANGUAGE = "java"

# --- Mining Date Range ---
# Dynamic range for the last 2 years of commits.
TO_DATE = datetime.now()
SINCE_DATE = TO_DATE - timedelta(days=730)

# --- Mining Volume (for testing) ---
TOTAL_METHODS_TO_MINE = 1000
# --- Output ---
OUTPUT_DIR = "output"
CHUNK_SIZE = 100

# --- Environment ---
JAVA_GRAMMAR_PATH = 'build/my-languages.so'