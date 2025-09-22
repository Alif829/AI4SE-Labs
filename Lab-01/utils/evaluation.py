# utils/evaluation.py

import math
from typing import Dict, List
from tqdm import tqdm

def calculate_perplexity(model, df, max_samples=None):
    
    total_log_prob = 0
    total_tokens = 0
    
    samples = df.head(max_samples) if max_samples else df
    
    for idx, row in samples.iterrows():
        tokens = eval(row['code_tokens'])
        tokens = ['<START>'] * (model.n - 1) + tokens + ['<END>']
        
        for i in range(model.n - 1, len(tokens)):
            context = tuple(tokens[i - model.n + 1:i])
            next_token = tokens[i]
            
            prob = model.get_probability(context, next_token)
            if prob > 0:
                total_log_prob += math.log(prob)
            else:
                total_log_prob += math.log(1e-10)  # Small epsilon for zero probability
            
            total_tokens += 1
    
    avg_log_prob = total_log_prob / total_tokens
    perplexity = math.exp(-avg_log_prob)
    return perplexity

def evaluate_topk_accuracy(model, df, max_samples=None):
    
    top1_correct = 0
    top3_correct = 0
    top5_correct = 0
    total = 0
    
    samples = df.head(max_samples) if max_samples else df
    
    for idx, row in tqdm(samples.iterrows(), total=len(samples), desc="Evaluating"):
        tokens = eval(row['code_tokens'])
        tokens = ['<START>'] * (model.n - 1) + tokens + ['<END>']
        
        # Test predictions at each position
        for i in range(model.n - 1, min(len(tokens), 50)):  # Limit to first 50 tokens
            context = tokens[i - model.n + 1:i]
            actual_token = tokens[i]
            
            predictions = model.predict_next_tokens(context, top_k=5)
            
            if predictions:
                predicted_tokens = [p[0] for p in predictions]
                
                if len(predicted_tokens) > 0 and predicted_tokens[0] == actual_token:
                    top1_correct += 1
                if actual_token in predicted_tokens[:3]:
                    top3_correct += 1
                if actual_token in predicted_tokens[:5]:
                    top5_correct += 1
                
                total += 1
    
    return {
        'top1_accuracy': top1_correct / total if total > 0 else 0,
        'top3_accuracy': top3_correct / total if total > 0 else 0,
        'top5_accuracy': top5_correct / total if total > 0 else 0,
        'total_predictions': total
    }