def classify_task(text: str) -> str:
    """Simple keyword-based task classification"""
    text_lower = text.lower()
    
    if any(word in text_lower for word in ["grammar", "fix", "correct", "typo"]):
        return "grammar"
    elif any(word in text_lower for word in ["email", "draft", "write to"]):
        return "email"
    elif "?" in text or any(word in text_lower for word in ["search", "find", "what", "how"]):
        return "search"
    else:
        return "grammar"  # default fallback
    
#ts is a placeholder lol, i need a gate network to classify the task