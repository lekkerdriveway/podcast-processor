import re

def test_formatter():
    # Sample episode names with different formats
    test_cases = [
        "Episode 23 - E T & Imaginary Friends and Empathy",
        "Ep. 5 - Building Blocks",
        "Episode 101: The Final Chapter",
        "Regular Title Without Episode",
        "Episode 7 - Home Alone & Understanding Time Out"
    ]
    
    for name in test_cases:
        # Simulate episode number extraction (assuming we already have it)
        match = re.search(r'(?:episode|ep)\.?\s*#?(\d+)', name, re.IGNORECASE)
        num = match.group(1) if match else "0"
        padded_num = num.zfill(3)
        
        print(f"Original: {name}")
        
        # Clean the title by removing Episode X prefix
        cleaned_name = re.sub(r'^(?:Episode|Ep\.?)\s+\d+\s*[-:]\s*', '', name, flags=re.IGNORECASE)
        print(f"Cleaned:  {cleaned_name}")
        
        # Create output key
        safe_name = cleaned_name.replace(':', ' -')
        safe_name = re.sub(r'[^\w\s&-]', '_', safe_name)
        safe_name = re.sub(r'[\s_]+', ' ', safe_name)
        safe_name = safe_name.strip()
        
        output_key = f"summaries/{padded_num} - {safe_name}.md"
        print(f"Output:   {output_key}")
        print("-" * 50)

if __name__ == "__main__":
    test_formatter()
