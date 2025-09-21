# scripts/prepare_data.py
"""Script to run data preprocessing"""

import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from src.data.preprocessor import DataPreprocessor

def main():
    """Run data preprocessing pipeline"""
    
    preprocessor = DataPreprocessor(config_path="configs/config.yaml")
    stats = preprocessor.run()
    
    print("\nPreprocessing completed successfully!")

if __name__ == "__main__":
    main()