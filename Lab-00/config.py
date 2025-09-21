from datetime import datetime, timedelta

STARS_THRESHOLD = 5000
SEARCH_QUERY_LANGUAGE = "java"
TO_DATE = datetime.now()
SINCE_DATE = TO_DATE - timedelta(days=365)


TOTAL_METHODS_TO_MINE =500000


OUTPUT_DIR = "output"
CHUNK_SIZE = 5000


JAVA_GRAMMAR_PATH = 'build/my-languages.so'