import re

def clean_text(text):
    """
    Cleans raw text extracted from documents.
    - Removes extra spaces
    - Removes repeated newlines
    - Strips leading/trailing whitespaces
    """
    if not text:
        return ""
        
    # Replace multiple spaces with a single space
    cleaned = re.sub(r'[ \t]+', ' ', text)
    
    # Replace multiple newlines with a single newline (or two if we want to preserve paragraph breaks, let's keep it to max 2)
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    
    # Remove basic page number artifacts (e.g., lines that just have a number or "Page X")
    cleaned = re.sub(r'^\s*Page\s+\d+\s*$', '', cleaned, flags=re.MULTILINE | re.IGNORECASE)
    cleaned = re.sub(r'^\s*\d+\s*$', '', cleaned, flags=re.MULTILINE)
    
    # Strip leading and trailing whitespace from the overall text
    cleaned = cleaned.strip()
    
    return cleaned
