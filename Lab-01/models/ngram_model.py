import numpy as np
from collections import defaultdict
from typing import Dict, List, Tuple
import math

class NGramModel:
    
    def __init__(self, n: int = 3, smoothing: str = 'laplace', k: float = 1.0):
        
        self.n = n
        self.smoothing = smoothing
        self.k = k
        self.ngram_counts = defaultdict(lambda: defaultdict(int))
        self.context_counts = defaultdict(int)
        self.vocabulary = set()
        
    def train(self, df):
       
        print(f"Training {self.n}-gram model...")
        
        for idx, row in df.iterrows():
            # Parse tokens
            tokens = eval(row['code_tokens'])
            
            # special tokens
            tokens = ['<START>'] * (self.n - 1) + tokens + ['<END>']
            self.vocabulary.update(tokens)
            
            # Extract n-grams
            for i in range(len(tokens) - self.n + 1):
                context = tuple(tokens[i:i + self.n - 1])
                next_token = tokens[i + self.n - 1]
                
                self.ngram_counts[context][next_token] += 1
                self.context_counts[context] += 1
        
        self.vocab_size = len(self.vocabulary)
        print(f"Training complete. Vocabulary size: {self.vocab_size}")
    
    def get_probability(self, context: Tuple, token: str) -> float:
        """probability with laplace and add-k smoothing."""
        count = self.ngram_counts[context].get(token, 0)
        context_total = self.context_counts[context]
        
        if self.smoothing == 'none':
            return count / context_total if context_total > 0 else 0.0
        elif self.smoothing == 'laplace':
            return (count + 1) / (context_total + self.vocab_size)
        elif self.smoothing == 'add-k':
            return (count + self.k) / (context_total + self.k * self.vocab_size)
    
    def predict_next_tokens(self, context: List[str], top_k: int = 5) -> List[Tuple[str, float]]:
        """top-k predictions for next token."""
        # Preparing the context here
        if len(context) < self.n - 1:
            context = ['<START>'] * (self.n - 1 - len(context)) + context
        else:
            context = context[-(self.n - 1):]
        
        context_tuple = tuple(context)
        
        # predictions
        predictions = []
        if context_tuple in self.ngram_counts:
            for token in self.ngram_counts[context_tuple]:
                prob = self.get_probability(context_tuple, token)
                predictions.append((token, prob))
        
        # Sort and return top-k tokens
        predictions.sort(key=lambda x: x[1], reverse=True)
        return predictions[:top_k]
    
    def sample_completion(self, context: List[str], max_length: int = 20) -> Tuple[List[str], List]:
        """Generates a completion from context."""
        generated = []
        current_context = context.copy()
        all_predictions = []

        for _ in range(max_length):
            # a simple backoff strategy
            temp_context_for_prediction = current_context.copy()
            predictions = []
            while len(temp_context_for_prediction) > 0:
                predictions = self.predict_next_tokens(temp_context_for_prediction, top_k=5)
                if predictions:
                    break  # Found predictions, so exiting the while loop
                temp_context_for_prediction = temp_context_for_prediction[1:]

            if not predictions:
                # Even with backoff, no predictions could be made
                break

            all_predictions.append(predictions)

            # Sample based on probabilities
            tokens = [p[0] for p in predictions]
            probs = [p[1] for p in predictions]

            # Normalized probabilities
            total = sum(probs)
            if total > 0:
                probs = [p/total for p in probs]
                chosen = np.random.choice(tokens, p=probs)
            else:
                break

            if chosen == '<END>' or chosen in ['}', ';']:
                if chosen != '<END>':
                    generated.append(chosen)
                break

            generated.append(chosen)
            current_context = current_context + [chosen]
            if len(current_context) > self.n -1:
                current_context = current_context[-(self.n-1):]

        return generated, all_predictions