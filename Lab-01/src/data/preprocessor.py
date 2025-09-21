# src/data/preprocessor.py
"""Main preprocessing pipeline"""

import pandas as pd
import numpy as np
from pathlib import Path
import pickle
import json
from sklearn.model_selection import train_test_split
from typing import Tuple, List, Dict
import sys
sys.path.append('..')

from src.data.tokenizer import JavaTokenizer
from src.data.corpus_builder import CorpusBuilder
from src.utils.config import Config

class DataPreprocessor:
    """Main data preprocessing pipeline"""
    
    def __init__(self, config_path: str = "configs/config.yaml"):
        self.config = Config(config_path)
        self.tokenizer = JavaTokenizer(self.config.get('tokenization'))
        self.corpus_builder = CorpusBuilder(self.tokenizer, self.config.get('model'))
        
    def load_data(self) -> pd.DataFrame:
        """Load the raw dataset"""
        data_path = self.config.get('data.raw_data_path')
        print(f"Loading data from {data_path}...")
        df = pd.read_csv(data_path)
        print(f"Loaded {len(df)} methods")
        return df
    
    def preprocess_sequences(self, df: pd.DataFrame) -> Tuple[List[List[str]], List[List[str]], List[List[str]]]:
        """Preprocess token sequences"""
        print("Preprocessing token sequences...")
        
        # Process training data
        train_df = df[df['dataset_split'] == 'train'].copy()
        test_df = df[df['dataset_split'] == 'test'].copy()
        
        # Split training data into train and validation
        train_ratio = self.config.get('data.train_ratio', 0.9)
        train_df, val_df = train_test_split(
            train_df, 
            train_size=train_ratio, 
            random_state=42,
            stratify=train_df['repo_name']
        )
        
        print(f"Split sizes - Train: {len(train_df)}, Val: {len(val_df)}, Test: {len(test_df)}")
        
        # Process sequences
        def process_dataframe(df):
            sequences = []
            min_len = self.config.get('data.min_sequence_length', 5)
            max_len = self.config.get('data.max_sequence_length', 512)
            
            for _, row in df.iterrows():
                # Clean and parse tokens
                tokens = self.tokenizer.clean_token_string(row['code_tokens'])
                
                # Skip if too short or too long
                if len(tokens) < min_len or len(tokens) > max_len:
                    continue
                
                # Process tokens (handle strings, numbers)
                tokens = self.tokenizer.process_tokens(tokens)
                
                # Add special tokens
                tokens = self.tokenizer.add_special_tokens(
                    tokens,
                    add_bos=self.config.get('tokenization.add_bos_token', True),
                    add_eos=self.config.get('tokenization.add_eos_token', True)
                )
                
                sequences.append(tokens)
            
            return sequences
        
        train_sequences = process_dataframe(train_df)
        val_sequences = process_dataframe(val_df)
        test_sequences = process_dataframe(test_df)
        
        print(f"Processed sequences - Train: {len(train_sequences)}, Val: {len(val_sequences)}, Test: {len(test_sequences)}")
        
        return train_sequences, val_sequences, test_sequences
    
    def build_and_save_corpus(self, train_sequences, val_sequences, test_sequences):
        """Build vocabulary and save processed corpus"""
        
        # Build vocabulary from training data only
        min_freq = self.config.get('model.min_token_frequency', 2)
        max_vocab = self.config.get('model.vocab_size_limit', 50000)
        
        self.corpus_builder.build_vocabulary(
            train_sequences,
            min_frequency=min_freq,
            max_vocab_size=max_vocab
        )
        
        # Compute statistics
        stats = self.corpus_builder.compute_statistics(train_sequences)
        
        # Convert to IDs
        train_ids = [self.corpus_builder.tokens_to_ids(seq) for seq in train_sequences]
        val_ids = [self.corpus_builder.tokens_to_ids(seq) for seq in val_sequences]
        test_ids = [self.corpus_builder.tokens_to_ids(seq) for seq in test_sequences]
        
        # Save everything
        output_dir = Path("data/processed")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save corpus
        with open(output_dir / "train_corpus.pkl", "wb") as f:
            pickle.dump({
                'sequences': train_sequences,
                'ids': train_ids
            }, f)
        
        with open(output_dir / "val_corpus.pkl", "wb") as f:
            pickle.dump({
                'sequences': val_sequences,
                'ids': val_ids
            }, f)
        
        with open(output_dir / "test_corpus.pkl", "wb") as f:
            pickle.dump({
                'sequences': test_sequences,
                'ids': test_ids
            }, f)
        
        # Save vocabulary
        with open(output_dir / "vocabulary.pkl", "wb") as f:
            pickle.dump(self.corpus_builder.vocabulary, f)
        
        # Save statistics
        stats_dir = Path("data/statistics")
        stats_dir.mkdir(parents=True, exist_ok=True)
        
        with open(stats_dir / "corpus_stats.json", "w") as f:
            # Convert non-serializable items
            stats['most_common_tokens'] = [[token, int(count)] for token, count in stats['most_common_tokens']]
            json.dump(stats, f, indent=2)
        
        print("\nCorpus Statistics:")
        print(f"  Total sequences: {stats['total_sequences']}")
        print(f"  Total tokens: {stats['total_tokens']}")
        print(f"  Vocabulary size: {stats['vocabulary_size']}")
        print(f"  Avg sequence length: {stats['avg_sequence_length']:.2f}")
        print(f"\nToken Type Distribution:")
        for token_type, percentage in stats['token_type_distribution'].items():
            print(f"  {token_type}: {percentage:.2f}%")
        print(f"\nMost common tokens:")
        for token, count in stats['most_common_tokens'][:10]:
            print(f"  '{token}': {count}")
        
        return stats
    
    def run(self):
        """Run the complete preprocessing pipeline"""
        print("Starting data preprocessing pipeline...")
        
        # Load data
        df = self.load_data()
        
        # Preprocess sequences
        train_seq, val_seq, test_seq = self.preprocess_sequences(df)
        
        # Build vocabulary and save
        stats = self.build_and_save_corpus(train_seq, val_seq, test_seq)
        
        print("\n✓ Data preprocessing complete!")
        print(f"  Processed data saved to: data/processed/")
        print(f"  Statistics saved to: data/statistics/corpus_stats.json")
        
        return stats