# src/data/corpus_builder.py
"""Build and manage corpus for N-gram model"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Set
from collections import Counter
import pickle
import json
from pathlib import Path
from tqdm import tqdm

class CorpusBuilder:
    """Build corpus from tokenized code data"""
    
    def __init__(self, tokenizer, config: Dict = None):
        self.tokenizer = tokenizer
        self.config = config or {}
        self.vocabulary = {}
        self.token_counts = Counter()
        self.vocab_size = 0
        
    def build_vocabulary(self, token_sequences: List[List[str]], 
                        min_frequency: int = 2,
                        max_vocab_size: int = 50000) -> Dict[str, int]:
        """Build vocabulary from token sequences"""
        print("Building vocabulary...")
        
        # Count all tokens
        for seq in tqdm(token_sequences, desc="Counting tokens"):
            self.token_counts.update(seq)
        
        # Always include special tokens
        special_tokens = [
            self.tokenizer.bos_token,
            self.tokenizer.eos_token,
            self.tokenizer.unk_token,
            self.tokenizer.pad_token,
            '<STRING>',
            '<NUM>'
        ]
        
        # Create vocabulary with most frequent tokens
        vocab = {token: idx for idx, token in enumerate(special_tokens)}
        
        # Add tokens by frequency
        for token, count in self.token_counts.most_common():
            if token not in vocab:
                if count >= min_frequency and len(vocab) < max_vocab_size:
                    vocab[token] = len(vocab)
        
        self.vocabulary = vocab
        self.vocab_size = len(vocab)
        
        print(f"Vocabulary size: {self.vocab_size}")
        print(f"Total unique tokens: {len(self.token_counts)}")
        print(f"Tokens filtered out: {len(self.token_counts) - self.vocab_size}")
        
        return vocab
    
    def tokens_to_ids(self, tokens: List[str]) -> List[int]:
        """Convert tokens to vocabulary IDs"""
        unk_id = self.vocabulary.get(self.tokenizer.unk_token, 0)
        return [self.vocabulary.get(token, unk_id) for token in tokens]
    
    def ids_to_tokens(self, ids: List[int]) -> List[str]:
        """Convert vocabulary IDs back to tokens"""
        id_to_token = {v: k for k, v in self.vocabulary.items()}
        return [id_to_token.get(id, self.tokenizer.unk_token) for id in ids]
    
    def compute_statistics(self, token_sequences: List[List[str]]) -> Dict:
        """Compute corpus statistics"""
        print("Computing corpus statistics...")
        
        lengths = [len(seq) for seq in token_sequences]
        
        # Token type distribution
        token_types = {
            'keywords': 0,
            'identifiers': 0,
            'operators': 0,
            'literals': 0,
            'special': 0
        }
        
        operators = {'+', '-', '*', '/', '%', '=', '==', '!=', '<', '>', '<=', '>=', 
                    '&&', '||', '!', '&', '|', '^', '~', '<<', '>>', '++', '--'}
        
        for token, count in self.token_counts.items():
            if token in self.tokenizer.java_keywords:
                token_types['keywords'] += count
            elif token in operators:
                token_types['operators'] += count
            elif token in ['<STRING>', '<NUM>', self.tokenizer.bos_token, 
                          self.tokenizer.eos_token, self.tokenizer.unk_token]:
                token_types['special'] += count
            elif token.startswith('"') or token.isdigit():
                token_types['literals'] += count
            else:
                token_types['identifiers'] += count
        
        total_tokens = sum(token_types.values())
        token_type_percentages = {k: (v/total_tokens)*100 for k, v in token_types.items()}
        
        stats = {
            'total_sequences': len(token_sequences),
            'total_tokens': sum(lengths),
            'unique_tokens': len(self.token_counts),
            'vocabulary_size': self.vocab_size,
            'avg_sequence_length': np.mean(lengths),
            'median_sequence_length': np.median(lengths),
            'min_sequence_length': min(lengths),
            'max_sequence_length': max(lengths),
            'std_sequence_length': np.std(lengths),
            'token_type_distribution': token_type_percentages,
            'most_common_tokens': self.token_counts.most_common(20)
        }
        
        return stats
