# config.py
from datetime import datetime, timedelta

# --- GitHub Repository Search Settings ---
STARS_THRESHOLD = 4000
SEARCH_QUERY_LANGUAGE = "java"

# --- Mining Date Range ---
# Dynamic range for the last 2 years of commits.
TO_DATE = datetime.now()
SINCE_DATE = TO_DATE - timedelta(days=730)

# --- Mining Volume ---
TOTAL_METHODS_TO_MINE = 25000

# --- Output ---
# The directory where individual repository output files will be saved.
OUTPUT_DIR = "output"

# --- Environment ---
JAVA_GRAMMAR_PATH = 'build/my-languages.so'