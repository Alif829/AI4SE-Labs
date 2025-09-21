# src/data/tokenizer.py
"""Tokenizer for Java code with special token handling"""

import re
from typing import List, Dict, Set
import json

class JavaTokenizer:
    """Tokenizer specifically designed for Java code"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.bos_token = self.config.get('bos_token', '<BOS>')
        self.eos_token = self.config.get('eos_token', '<EOS>')
        self.unk_token = self.config.get('unk_token', '<UNK>')
        self.pad_token = self.config.get('pad_token', '<PAD>')
        
        # Special tokens for abstraction
        self.string_token = '<STRING>'
        self.number_token = '<NUM>'
        
        self.preserve_strings = self.config.get('preserve_strings', False)
        self.preserve_numbers = self.config.get('preserve_numbers', False)
        
        # Java keywords for better tokenization
        self.java_keywords = {
            'public', 'private', 'protected', 'static', 'final', 'void',
            'class', 'interface', 'extends', 'implements', 'new', 'return',
            'if', 'else', 'for', 'while', 'do', 'switch', 'case', 'default',
            'break', 'continue', 'try', 'catch', 'finally', 'throw', 'throws',
            'int', 'long', 'double', 'float', 'boolean', 'char', 'String'
        }
    
    def clean_token_string(self, token_str: str) -> List[str]:
        """Clean and parse token string from dataset"""
        # Remove brackets and quotes, split by comma
        if isinstance(token_str, str):
            # Handle string representation of list
            token_str = token_str.strip('[]')
            # Split by comma and clean each token
            tokens = []
            for token in token_str.split(','):
                token = token.strip().strip('"\'')
                if token:
                    tokens.append(token)
            return tokens
        elif isinstance(token_str, list):
            return token_str
        else:
            return []
    
    def process_tokens(self, tokens: List[str]) -> List[str]:
        """Process tokens with special token handling"""
        processed = []
        
        for token in tokens:
            # Skip empty tokens
            if not token:
                continue
            
            # Handle string literals
            if not self.preserve_strings and (token.startswith('"') or token.startswith("'")):
                processed.append(self.string_token)
            # Handle numbers
            elif not self.preserve_numbers and token.replace('.', '').replace('-', '').isdigit():
                processed.append(self.number_token)
            # Keep everything else
            else:
                processed.append(token)
        
        return processed
    
    def add_special_tokens(self, tokens: List[str], add_bos: bool = True, add_eos: bool = True) -> List[str]:
        """Add BOS and EOS tokens"""
        result = tokens.copy()
        if add_bos:
            result = [self.bos_token] + result
        if add_eos:
            result = result + [self.eos_token]
        return result