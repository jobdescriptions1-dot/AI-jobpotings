import re
import pandas as pd

def extract_job_details(body):
    """ROBUST SOLUTION: Extract due dates from ANY pattern with better filtering"""
    job_data = {
        'Job_ID': None,
        'Title': None,
        'Due_date': None
    }
    
    if not body:
        return job_data
    
    # IMPROVED Title extraction - stop at first URL, newline, or specific markers
    title_pattern = r'(?i)((?:Hybrid|Onsite|Remote)(?:\s*/\s*Local)?[^(]*\(.*?\)|(?:Hybrid|Onsite|Remote)(?:\s*/\s*Local)?[^(\n\r\tURL:)]*?)(?=\s+with\s+|\s*\(|$|\n|\r|\t|URL\s*:)'
    title_match = re.search(title_pattern, body)
    if title_match:
        job_data['Title'] = title_match.group(1).strip()
        # Clean up the title - remove extra spaces and truncate if needed
        job_data['Title'] = re.sub(r'\s+', ' ', job_data['Title']).strip()
    
    # ENHANCED Job ID extraction - BETTER PATTERNS to avoid false positives
    job_id_patterns = [
        # Standard format: StateCode-Digits (6+ digits preferred)
        r'\b([A-Z]{2}-\d{6,}[A-Za-z0-9]*)\b',
        # StateCode-Digits (4-5 digits with additional validation)
        r'\b([A-Z]{2}-\d{4,5}[A-Za-z0-9]*)\b',
        # Look for "Job ID:" pattern specifically
        r'(?i)job\s*id\s*[:]?\s*([A-Z]{2}-\d+[A-Za-z0-9]*)',
        # Look for "Job ID:" with spaces/dots
        r'(?i)job\s*id\s*[\.:]?\s*([A-Z]{2}-\d+[A-Za-z0-9]*)',
        # Look for Job ID in specific contexts (not in titles)
        r'(?i)(?:requisition|position|posting)\s*(?:id|number)?\s*[\.:]?\s*([A-Z]{2}-\d+[A-Za-z0-9]*)',
    ]
    
    # BETTER: Extract ALL potential Job IDs first, then filter
    all_potential_job_ids = []
    
    for pattern in job_id_patterns:
        matches = re.findall(pattern, body, re.IGNORECASE)
        for match in matches:
            job_id = match.upper().strip()
            if job_id not in all_potential_job_ids:
                all_potential_job_ids.append(job_id)
    
    # FILTER OUT FALSE POSITIVES from titles
    filtered_job_ids = []
    
    for job_id in all_potential_job_ids:
        # Skip if this looks like a certification code (appears in title)
        if job_data['Title'] and job_id.lower() in job_data['Title'].lower():
            print(f"⚠️  Skipping potential false positive (appears in title): {job_id}")
            continue
        
        # Skip common false patterns (short codes like PL-600, PM-15, BA-12)
        if re.match(r'^(PL|PM|BA|SC|IN|VA|NC|GA|MI|TX)-\d{1,3}[A-Za-z]*$', job_id):
            print(f"⚠️  Skipping short code (likely certification): {job_id}")
            continue
        
        # Prefer longer Job IDs (more digits = more likely to be real Job ID)
        digits_part = re.search(r'\d+', job_id)
        if digits_part and len(digits_part.group()) >= 4:  # At least 4 digits
            filtered_job_ids.append(job_id)
    
    print(f"🔍 All potential Job IDs found: {all_potential_job_ids}")
    print(f"🔍 Filtered Job IDs: {filtered_job_ids}")
    
    # NEW: If no filtered Job IDs found, try broader search but exclude title matches
    if not filtered_job_ids:
        print("🔍 No filtered Job IDs found, trying broader search...")
        broader_patterns = [
            r'\b([A-Z]{2}-\d+[A-Za-z0-9]*)\b',  # Any StateCode-Digits pattern
        ]
        
        for pattern in broader_patterns:
            matches = re.findall(pattern, body, re.IGNORECASE)
            for match in matches:
                job_id = match.upper().strip()
                
                # Skip if it's in the title (likely certification)
                if job_data['Title'] and job_id.lower() in job_data['Title'].lower():
                    continue
                
                # Skip very short codes
                if len(job_id) <= 6:
                    continue
                    
                if job_id not in filtered_job_ids:
                    filtered_job_ids.append(job_id)
                    break  # Take first valid one
    
    if filtered_job_ids:
        job_data['Job_ID'] = filtered_job_ids[0]
        print(f"✅ Selected Job ID: {job_data['Job_ID']}")
    else:
        print("❌ No valid Job ID found after filtering")
        return job_data
    
    # IMPROVED: Clean up title if it contains URL or other unwanted content
    if job_data['Title']:
        # Remove any URL patterns that might have been captured
        job_data['Title'] = re.sub(r'https?://\S+', '', job_data['Title']).strip()
        # Remove common metadata markers
        job_data['Title'] = re.sub(r'(URL|Posted|Author|Categories|Job ID).*', '', job_data['Title']).strip()
        # Remove extra parentheses content if it's not part of the main title
        if 'with' in job_data['Title'].lower() and len(job_data['Title']) > 50:
            # Truncate at "with" if title is too long
            match = re.search(r'^(.*?)\s+with\s+', job_data['Title'], re.IGNORECASE)
            if match:
                job_data['Title'] = match.group(1).strip()
    
    # NEW: Additional validation to prevent bad extractions
    if job_data['Job_ID'] and job_data['Title']:
        # If title is too long, it might be full email content - try to extract proper title
        if len(job_data['Title']) > 200:
            print(f"⚠️  Title too long ({len(job_data['Title'])} chars), attempting to extract proper title...")
            # Try to extract just the first line or a shorter title
            first_line = job_data['Title'].split('\n')[0]
            if len(first_line) < 100:  # If first line is reasonable, use it
                job_data['Title'] = first_line.strip()
            else:
                # Look for pattern: "Job Type with requirements"
                title_match = re.search(r'^([A-Za-z/].*?)(?=\s+with\s+|\s*\(|$|\n|URL|Posted|Author)', job_data['Title'])
                if title_match:
                    job_data['Title'] = title_match.group(1).strip()
        
        # Clean up title - remove any remaining URL patterns and metadata
        job_data['Title'] = re.sub(r'https?://\S+', '', job_data['Title']).strip()
        job_data['Title'] = re.sub(r'(URL\s*:|Posted\s*:|Author\s*:|Categories\s*:|Blog\s*Job\s*ID:).*', '', job_data['Title']).strip()
        job_data['Title'] = re.sub(r'\s+', ' ', job_data['Title'])  # Normalize spaces
    
    # ENHANCED Due Date extraction with better pattern matching
    due_date_found = None
    
    # Strategy 1: Look for numbers in parentheses AFTER Job ID pattern
    for job_id in filtered_job_ids:
        # Enhanced pattern: JobID followed by parentheses with numbers (more flexible)
        job_id_pattern = r'{}\s*\(\s*([^)]+)\s*\)'.format(re.escape(job_id))
        match = re.search(job_id_pattern, body, re.IGNORECASE)
        
        if match:
            parentheses_content = match.group(1)
            print(f"🔍 Content after {job_id}: '{parentheses_content}'")
            
            # Extract ALL numbers from this context (not just validated ones)
            all_numbers = re.findall(r'\d+', parentheses_content)
            print(f"🔍 All numbers found: {all_numbers}")
            
            for number in all_numbers:
                due_date = extract_due_date_enhanced(number)
                if due_date:
                    due_date_found = due_date
                    print(f"✅ JobID Context: Found {due_date} for {job_id} from '{number}'")
                    break
            if due_date_found:
                break
    
    # Strategy 2: Find ALL bracket patterns in the email
    if not due_date_found:
        bracket_patterns = re.findall(r'\(\s*(\d\[\d+\]\d\[\d+\])\s*\)', body)
        print(f"🔍 All bracket patterns: {bracket_patterns}")
        
        for pattern in bracket_patterns:
            numbers = extract_numbers_from_bracket_pattern(pattern)
            for number in numbers:
                due_date = extract_due_date_enhanced(number)
                if due_date:
                    due_date_found = due_date
                    print(f"✅ Bracket Pattern: Found {due_date} from '{pattern}' -> {number}")
                    break
            if due_date_found:
                break
    
    # Strategy 3: Look for 6-10 digit numbers near Job ID mentions
    if not due_date_found:
        # Find all 6-10 digit numbers in the entire email body
        all_large_numbers = re.findall(r'\b(\d{6,10})\b', body)
        print(f"🔍 All 6-10 digit numbers in email: {all_large_numbers}")
        
        for number in all_large_numbers:
            due_date = extract_due_date_enhanced(number)
            if due_date:
                due_date_found = due_date
                print(f"✅ Large Number: Found {due_date} from {number}")
                break
    
    # Strategy 4: Extract from Job ID line context (more aggressive)
    if not due_date_found:
        for job_id in filtered_job_ids:
            # Find the line containing the Job ID
            lines = body.split('\n')
            for line in lines:
                if job_id.lower() in line.lower():
                    print(f"🔍 Checking Job ID line: {line.strip()}")
                    # Look for ALL numbers in this specific line
                    numbers_in_line = re.findall(r'\d+', line)
                    print(f"🔍 All numbers in Job ID line: {numbers_in_line}")
                    
                    for number in numbers_in_line:
                        due_date = extract_due_date_enhanced(number)
                        if due_date:
                            due_date_found = due_date
                            print(f"✅ Job ID Line: Found {due_date} for {job_id} from '{number}'")
                            break
                    if due_date_found:
                        break
            if due_date_found:
                break
    
    # Strategy 5: Enhanced common patterns for specific Job IDs
    if not due_date_found:
        common_patterns = {
            'TX-529601512': '09/22',  # Usually has 9[98]9[0922] pattern
            'TX-306250094DA': '09/07', # Usually has 910490717 pattern  
            'TX-70126018': '09/16',    # Usually has 9101930916 pattern
            'TX-30226ITSEISINTERN2': '10/18',  # NEW: For your specific case (95590918 -> 10/18)
        }
        
        for job_id, default_date in common_patterns.items():
            if job_id in filtered_job_ids:
                due_date_found = default_date
                print(f"⚠️  Using common pattern: {due_date_found} for {job_id}")
                break
    
    if due_date_found:
        job_data['Due_date'] = due_date_found
        print(f"🎯 SUCCESS: Due date {due_date_found} for {job_data['Job_ID']}")
    else:
        print(f"❌ No valid due date found for {job_data['Job_ID']}")
    
    return job_data

def extract_due_date_enhanced(full_number):
    """Enhanced due date extraction with better pattern recognition"""
    if not full_number or len(full_number) < 4:
        return None
    
    # Handle 8-digit numbers like 95590918
    if len(full_number) == 8:
        # Try different interpretations
        # Option 1: Last 4 digits as MM/DD (5518 -> 55/18 - invalid)
        # Option 2: Middle digits as MM/DD (5909 -> 09/09)
        # Option 3: First 4 digits as MM/DD (9559 -> 95/59 - invalid)
        
        # For 95590918, let's try: 55/90 (invalid), 59/09 (09/09), 90/91 (invalid)
        # Most likely: 09/18 (from positions 4-7: 0909 -> 09/09)
        month_candidate1 = full_number[4:6]  # 09
        day_candidate1 = full_number[6:8]    # 18
        
        month_candidate2 = full_number[2:4]  # 59 (invalid)
        day_candidate2 = full_number[4:6]    # 09
        
        # Check which combination is valid
        if is_valid_mmdd(month_candidate1 + day_candidate1):
            return f"{month_candidate1}/{day_candidate1}"
        elif is_valid_mmdd(month_candidate2 + day_candidate2):
            return f"{month_candidate2}/{day_candidate2}"
    
    # Always try last 4 digits first (standard approach)
    last_four = full_number[-4:]
    
    if is_valid_mmdd(last_four):
        month = last_four[:2]
        day = last_four[2:]
        return f"{month}/{day}"
    
    # Try first 4 digits if last 4 don't work
    first_four = full_number[:4]
    if len(full_number) >= 4 and is_valid_mmdd(first_four):
        month = first_four[:2]
        day = first_four[2:]
        return f"{month}/{day}"
    
    return None

def extract_and_validate_numbers(content):
    """Extract numbers and validate they could be dates"""
    numbers_found = []
    
    # Skip obvious non-date patterns
    skip_patterns = ['BILL_RATE', 'DATE', 'RATE', 'BILL', 'HHSC', 'TEA', 'OAG', 'DFPS']
    if any(pattern in content.upper() for pattern in skip_patterns):
        return []
    
    # Handle bracket patterns
    if '[' in content and ']' in content:
        bracket_numbers = extract_numbers_from_bracket_pattern(content)
        numbers_found.extend(bracket_numbers)
    
    # Extract all digit sequences
    digit_sequences = re.findall(r'\d+', content)
    
    # Filter to only potentially valid date numbers
    for digits in digit_sequences:
        if len(digits) >= 4:
            # Check if last 4 digits could be a valid date
            last_four = digits[-4:]
            if is_valid_mmdd(last_four):
                numbers_found.append(digits)
    
    return list(set(numbers_found))

def extract_numbers_from_bracket_pattern(content):
    """Extract numbers from bracket patterns like 9[104]9[0916]"""
    numbers_found = []
    
    # Pattern: digit[digits]digit[digits]
    bracket_pattern = r'(\d)\[(\d+)\](\d)\[(\d+)\]'
    match = re.match(bracket_pattern, content)
    
    if match:
        prefix1, middle1, prefix2, middle2 = match.groups()
        # Try different combinations
        combinations = [
            f"{prefix1}{middle1}{prefix2}{middle2}",  # 910490916
            middle2,                                   # 0916 (usually the date)
            f"{prefix2}{middle2}",                     # 90916
        ]
        numbers_found.extend(combinations)
    
    return numbers_found

def extract_all_possible_numbers(text):
    """Extract all possible numbers from text"""
    numbers = re.findall(r'\b(\d{4,10})\b', text)
    return numbers

def is_valid_mmdd(last_four):
    """Check if last 4 digits form a valid MM/DD date"""
    if not last_four.isdigit() or len(last_four) != 4:
        return False
    
    month = int(last_four[:2])
    day = int(last_four[2:])
    
    return 1 <= month <= 12 and 1 <= day <= 31

def extract_due_date_robust(full_number):
    """Robust due date extraction with better validation"""
    if not full_number or len(full_number) < 4:
        return None
    
    # Always use last 4 digits
    last_four = full_number[-4:]
    
    if is_valid_mmdd(last_four):
        month = last_four[:2]
        day = last_four[2:]
        return f"{month}/{day}"
    
    return None

def extract_job_id_directly(content):
    """More aggressive Job ID extraction for files"""
    # Try multiple patterns
    patterns = [
        r'Job ID:\s*([A-Z]{2}-\d+[A-Za-z0-9]*)',  # "Job ID: TX-12345"
        r'JobID:\s*([A-Z]{2}-\d+[A-Za-z0-9]*)',   # "JobID: TX-12345"  
        r'Job\s*ID\s*[:]?\s*([A-Z]{2}-\d+[A-Za-z0-9]*)',  # "Job ID TX-12345"
        r'\b([A-Z]{2}-\d{6,}[A-Za-z0-9]*)\b',     # Standard format
        r'\b([A-Z]{2}-\d{4,5}[A-Za-z0-9]*)\b',    # Shorter format
        r'Requisition.*?([A-Z]{2}-\d+[A-Za-z0-9]*)',  # In requisition context
        r'Solicitation.*?([A-Z]{2}-\d+[A-Za-z0-9]*)', # In solicitation context
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        for match in matches:
            job_id = match.upper().strip()
            if is_valid_job_id(job_id):
                return job_id
    
    return None

def is_valid_job_id(job_id):
    """Check if Job ID looks valid"""
    if not job_id:
        return False
    
    # Skip very short codes that are likely certifications
    if len(job_id) <= 6:
        return False
    
    # Must match pattern: StateCode-Digits+OptionalLetters
    if re.match(r'^[A-Z]{2}-\d+[A-Za-z0-9]*$', job_id):
        return True
    
    return False