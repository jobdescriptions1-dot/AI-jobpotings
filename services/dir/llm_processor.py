import os
import re
import time
import datetime
import requests
from typing import Optional
from groq import Groq
# from groq import GroqClient, AsyncGroqClient
from dotenv import load_dotenv


load_dotenv()

class PureLLMRequisitionProcessor:
    def __init__(self, api_key, model):
        self.api_key = api_key
        self.model = model
        self.client = Groq(api_key=api_key)
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"
        self.max_retries = 3
        self.retry_delay = 2
        pass
    
    def make_llm_call(self, prompt, system_message, max_tokens=4000, timeout=45):
        """Make a pure LLM call with better error handling"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
           
        if len(prompt) > 28000:
            prompt = prompt[:28000] + "... [content truncated]"
        
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": system_message[:1000]
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.1,
            "max_tokens": min(max_tokens, 6000),
            "top_p": 0.9
        }
        
        for attempt in range(self.max_retries):
            try:
                response = requests.post(self.base_url, headers=headers, json=payload, timeout=timeout)
                
                if response.status_code == 413:
                    print("Request too large, reducing content...")
                    return None
                if response.status_code == 429:
                    print("Rate limited, waiting...")
                    time.sleep(10)
                    continue
                    
                response.raise_for_status()
                result = response.json()
                
                if 'choices' in result and len(result['choices']) > 0:
                    return result['choices'][0]['message']['content']
                    
            except requests.exceptions.RequestException as e:
                print(f"API error on attempt {attempt + 1}: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                else:
                    return None
            
        return None
        pass
    
    def extract_data_from_regex_content(self, regex_content, filename):
        """Extract data from regex-extracted content instead of raw scraped content"""
        print("  🔍 Using regex-extracted data for LLM processing...")
        
        # Extract requisition number from filename
        requisition_number = "unknown"
        try:
            clean_name = filename.replace(".txt", "")
            prefixes_to_remove = [
                "Solicitation_Reference_Number_",
                "SolicitationReferenceNumber_", 
                "solicitation_reference_number_",
                "Reference_Number_",
                "Response_Number_",
                "Solicitation_",
                "Response_"
            ]
            
            temp_number = clean_name
            for prefix in prefixes_to_remove:
                if prefix in temp_number:
                   temp_number = temp_number.replace(prefix, "")
            
            requisition_number = temp_number
            print(f"  ✅ Final extracted number: {requisition_number}")
                
        except Exception as e:
            print(f"  ❌ Error extracting from filename: {e}")
            requisition_number = "unknown"

        # Extract data from regex content
        bill_rate = "000"
        date_mmdd = "0000"
        due_date_full = "Date not specified"
        location = "Not specified"
        duration = "Unknown"
        positions = "Unknown"
        skills_section = ""
        description_section = ""
        work_arrangement = "Not specified"

        # Extract bill rate from regex content
        bill_rate_match = re.search(r'NTE Rate:\s*\$\s*(\d+)', regex_content)
        if bill_rate_match:
            bill_rate = bill_rate_match.group(1)
            print(f"  ✅ Extracted bill rate: {bill_rate}")

        # Extract date from regex-extracted content
        print("  🔍 Extracting due date from regex content...")

        # Method 1: Look for "Response Deadline:" line
        if "Response Deadline:" in regex_content:
           lines = regex_content.split('\n')
           for line in lines:
               if line.startswith('Response Deadline:'):
                    date_part = line.replace('Response Deadline:', '').strip()
                    print(f"  ✅ Found Response Deadline line: {date_part}")
            
                    # Extract date from the line
                    date_match = re.search(r'(\d{1,2})/(\d{1,2})/(\d{4})', date_part)
                    if date_match:
                        month = date_match.group(1).zfill(2)
                        day = date_match.group(2).zfill(2)
                        year = date_match.group(3)
                
                        date_mmdd = month + day
                        due_date_full = f"{month}/{day}/{year}"
                        print(f"  ✅ Extracted date: {due_date_full}, MMDD: {date_mmdd}")
                        break
                    else:
                        print(f"  ❌ Could not parse date from: {date_part}")
                        date_mmdd = "0000"
                        due_date_full = "Date not specified"
                        break
        else:
            print(f"  ❌ No Response Deadline line found")
            date_mmdd = "0000"
            due_date_full = "Date not specified"

        # Extract location from regex content
        location_match = re.search(r'Location:\s*([^\n]+)', regex_content)
        if location_match:
            location = location_match.group(1)
            print(f"  ✅ Extracted location: {location}")

        # Extract work arrangement from regex content
        work_arrangement_match = re.search(r'Work Arrangement:\s*([^\n]+)', regex_content)
        if work_arrangement_match:
            work_arrangement = work_arrangement_match.group(1)
            print(f"  ✅ Extracted work arrangement: {work_arrangement}")

        # Extract positions from regex content
        positions_match = re.search(r'Positions:\s*(\d+)', regex_content)
        if positions_match:
            positions = positions_match.group(1)
            print(f"  ✅ Extracted positions: {positions}")

        # Extract duration from regex content (calculate from dates)
        start_date_match = re.search(r'Start Date:\s*(\d{1,2}/\d{1,2}/\d{4})', regex_content)
        end_date_match = re.search(r'End Date:\s*(\d{1,2}/\d{1,2}/\d{4})', regex_content)
        
        if start_date_match and end_date_match:
            start_date = datetime.datetime.strptime(start_date_match.group(1), '%m/%d/%Y')
            end_date = datetime.datetime.strptime(end_date_match.group(1), '%m/%d/%Y')
            months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
            duration = f"{months} months"
            print(f"  ✅ Calculated duration: {duration}")

        # Extract skills section - REMOVE SEPARATOR LINES
        skills_start = regex_content.find("SKILLS:")
        description_start = regex_content.find("DESCRIPTION:")

        if skills_start != -1 and description_start != -1:
            skills_section = regex_content[skills_start:description_start].strip()
            print(f"  ✅ Extracted skills section: {len(skills_section)} chars")  
            # Remove separator lines (like "------------------------------")
            # Split into lines and filter out separator lines
            skills_lines = skills_section.split('\n')
            cleaned_skills_lines = []
            for line in skills_lines:
                # Skip lines that are just hyphens/dashes (separator lines)
                line_stripped = line.strip()
                if line_stripped and not re.match(r'^[-=]+$', line_stripped):
                   cleaned_skills_lines.append(line)
        
            skills_section = '\n'.join(cleaned_skills_lines)
            print(f"  ✅ Cleaned skills section (removed separators): {len(skills_section)} chars")

        # Extract description section - REMOVE SEPARATOR LINES
        if description_start != -1:
           description_section = regex_content[description_start:].strip()
           # Find the end of description (before "END EXTRACTED DATA")
           end_marker = description_section.find("END EXTRACTED DATA")
           if end_marker != -1:
              description_section = description_section[:end_marker].strip()
           print(f"  ✅ Extracted description section: {len(description_section)} chars")
        
           # Remove separator lines (like "------------------------------")
           # Split into lines and filter out separator lines
           desc_lines = description_section.split('\n')
           cleaned_desc_lines = []
           for line in desc_lines:
               # Skip lines that are just hyphens/dashes (separator lines)
               line_stripped = line.strip()
               if line_stripped and not re.match(r'^[-=]+$', line_stripped):
                  cleaned_desc_lines.append(line)
        
           description_section = '\n'.join(cleaned_desc_lines)
           print(f"  ✅ Cleaned description section (removed separators): {len(description_section)} chars")

        return {
            'requisition_number': requisition_number,
            'bill_rate': bill_rate,
            'date_mmdd': date_mmdd,
            'due_date_full': due_date_full,
            'location': location,
            'duration': duration,
            'positions': positions,
            'skills_section': skills_section,
            'description_section': description_section,
            'work_arrangement': work_arrangement
        }
        pass
    
    def extract_all_data_pure_llm(self, regex_content, filename):
        """Use pure LLM to extract data from REGEX-EXTRACTED content"""
        
        # First extract all data from regex content
        extracted_data = self.extract_data_from_regex_content(regex_content, filename)
        
        requisition_number = extracted_data['requisition_number']
        bill_rate = extracted_data['bill_rate']
        date_mmdd = extracted_data['date_mmdd']
        location = extracted_data['location']
        duration = extracted_data['duration']
        positions = extracted_data['positions']
        skills_section = extracted_data['skills_section']
        description_section = extracted_data['description_section']
        work_arrangement = extracted_data['work_arrangement']

        print(f"  📋 Using pre-extracted data:")
        print(f"    - Requisition: {requisition_number}")
        print(f"    - Bill Rate: {bill_rate}")
        print(f"    - Date: {date_mmdd}")
        print(f"    - Location: {location}")
        print(f"    - Duration: {duration}")
        print(f"    - Positions: {positions}")
        print(f"    - Skills: {len(skills_section)} chars")
        print(f"    - Description: {len(description_section)} chars")
        print(f"    - Work Arrangement: {work_arrangement}")

        system_message = """You are an expert document analyst specialized in Texas government solicitations. 
        Format the output exactly as specified without any additional commentary or explanations.
        Use the provided pre-extracted data to create the final formatted output.

        CRITICAL OUTPUT FORMATTING RULES:
        - For Job ID: Format MUST be exactly: TX-{requisition_number} (9{bill_rate}9{date_mmdd})
        - Return output in exactly the specified format with no additional text"""

        prompt = f"""
        Please format the following pre-extracted solicitation data into the required output format:

    PRE-EXTRACTED DATA:
    - Response Number: {requisition_number}
    - NTE Rate: ${bill_rate}
    - Response Deadline: {date_mmdd}
    - Location: {location}
    - Duration: {duration}
    - Positions: {positions}
    - Work Arrangement: {work_arrangement}

    SKILLS SECTION:
    {skills_section}

    DESCRIPTION SECTION:
    {description_section}

    OUTPUT FORMAT - RETURN EXACTLY IN THIS FORMAT WITH NO ADDITIONAL TEXT:

    Job ID: TX-{requisition_number} (9{bill_rate}9{date_mmdd})
    Location: {location}
       - Format as: "City, State (Department Abbreviation)"
       - Take department abbreviation from the full name and convert it into short form by taking each word first letter
       - Example: "Lamar Boulevard, TX (OCCC)"
       - For this location if they mention WFH then go for Austin don't use WFH
    Duration: {duration}
    Positions: {positions}

    {skills_section}

    {description_section}

    IMPORTANT: 
    - Use the EXACT data provided above
    - Do NOT modify the Job ID format
    - Do NOT add any additional text or explanations
    - Keep the skills and description exactly as provided
    - Output must match the exact format above
    UNIVERSAL DESCRIPTION SPACING RULES:
     - Exclude the first paragraph about general requirements
     - IDENTIFY ALL section headers in the description using these rules:
       * Lines ending with ":" that are NOT continuations of sentences
       * Lines that are clearly section titles (standalone, not part of paragraphs)
       * Lines containing typical header words (Responsibilities, Qualifications, Requirements, Skills, Experience, Education, Duties, Overview,ADDITIONAL DETAILS etc.)
       * Lines that are formatted as headers (ALL CAPS, bold, underlined, or visually distinct)
       * FOR EACH SECTION HEADER: Insert exactly ONE blank line BEFORE the header
       * NO blank line AFTER the header - content should start immediately on the next line
       * REMOVE ALL other blank lines from the entire description
       * AFTER EACH PERIOD (.), START THE NEXT SENTENCE ON A NEW LINE WITHOUT ADDING ANY BLANK LINES

     HEADER DETECTION EXAMPLES:
     ✓ "RESPONSIBILITIES:" (header - add blank line before)
     ✓ "REQUIRED SKILLS:" (header - add blank line before)  
     ✓ "QUALIFICATIONS:" (header - add blank line before)
     ✓ "Work Environment: Professional office" (NOT a header - part of sentence)
     ✓ "Position: Compliance Officer" (NOT a header - part of sentence)

     FINAL RESULT MUST HAVE:
     - One blank line before each section
    """
        print(f"  📋 Sending {len(prompt)} chars to LLM for formatting...")

        result = self.make_llm_call(prompt, system_message, max_tokens=4000, timeout=60)

        return result if result else "LLM extraction failed"
        pass

class RequisitionTitleGenerator:
    def __init__(self, api_key, model):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"
        self.max_retries = 3
        self.retry_delay = 2
        pass
    
    def make_llm_call(self, prompt, system_message, max_tokens=4000, timeout=45):
        """Make a pure LLM call with better error handling"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": system_message[:1000]
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.1,
            "max_tokens": min(max_tokens, 6000),
            "top_p": 0.9
        }
        
        for attempt in range(self.max_retries):
            try:
                response = requests.post(self.base_url, headers=headers, json=payload, timeout=timeout)
                
                if response.status_code == 413:
                    print("Request too large, reducing content...")
                    return None
                if response.status_code == 429:
                    print("Rate limited, waiting...")
                    time.sleep(10)
                    continue
                    
                response.raise_for_status()
                result = response.json()
                
                if 'choices' in result and len(result['choices']) > 0:
                    return result['choices'][0]['message']['content']
                    
            except requests.exceptions.RequestException as e:
                print(f"API error on attempt {attempt + 1}: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                else:
                    return None
            
        return None
        pass
    
    def generate_title_from_regex_content(self, regex_content):
        """Generate title using data from regex-extracted content"""
        print("  🔍 Generating title from regex-extracted data...")

        # Extract work arrangement from regex content
        work_arrangement = "Onsite"  # default
        work_arrangement_match = re.search(r'Work Arrangement:\s*([^\n]+)', regex_content)
        if work_arrangement_match:
            work_arrangement_text = work_arrangement_match.group(1)
            if "Hybrid" in work_arrangement_text:
                work_arrangement = "Hybrid"
            elif "Remote" in work_arrangement_text or "Telework" in work_arrangement_text:
                work_arrangement = "Remote"
            elif "Onsite" in work_arrangement_text or "On Site" in work_arrangement_text:
                work_arrangement = "Onsite"
        
        print(f"  ✅ Extracted work arrangement: {work_arrangement}")

        # Extract skills from regex content
        skills_section = ""
        skills_start = regex_content.find("SKILLS:")
        description_start = regex_content.find("DESCRIPTION:")
        
        if skills_start != -1 and description_start != -1:
            skills_section = regex_content[skills_start:description_start].strip()
            print(f"  ✅ Extracted skills for title: {len(skills_section)} chars")

        system_message = """STRICT RULES: 
You are an expert job title classifier. Analyze the skills section and generate the most appropriate job title based ONLY on the technical skills found.
1. OUTPUT EXACT FORMAT: [Work Arrangement]/Local [Job Title] (Experience+ Certifications) with [Technical Skills] experience
2. ALWAYS INCLUDE "Local" after the work arrangement - FORMAT IS: [Work Arrangement]/Local [Job Title]
3. PARENTHESES: ONLY certifications, NO experience descriptions.If no certifications, use (Experience+)
4. AFTER "with": ONLY technical skills, NO soft skills
5. REMOVE any introductory text like "Based on the provided document" or "Here's the generated title:"
6. VIOLATING THESE RULES IS NOT ACCEPTABLE
7. REMOVE any "(Experience+)" or similar text from title 
8. Don't add certification word after the certification name only just give certifications name  e.g : BluePrism Certification -> BluePrism """

        prompt = f"""ANALYZE THIS SKILLS SECTION AND GENERATE A TECHNICAL TITLE FOLLOWING STRICT FORMAT RULES:

WORK ARRANGEMENT: {work_arrangement}

SKILLS SECTION:
{skills_section}

CRITICAL INSTRUCTIONS - MUST FOLLOW EXACTLY:

1. WORK ARRANGEMENT: Use the provided work arrangement: {work_arrangement}
   - **ALWAYS FORMAT AS: [Work Arrangement]/Local**

2. FORMAT: [Work Arrangement]/Local [Job Title] (Experience+ Certifications) with [Technical Skills] experience

3. JOB TITLE: BASED ON SKILLS ANALYSIS - Generate job title by analyzing ALL technical skills from the skills section:
- Look at ALL technical skills and qualifications
- Identify the primary role pattern (Data, Cloud, Business Analysis, Development, etc.)
- Generate job title that matches the skills pattern  

4. CERTIFICATIONS (IN PARENTHESES ONLY):
   - ONLY include actual certification names from the skills section
   - NEVER include experience descriptions, skills, or qualifications
   - If no certifications found, use: (Experience+)

5. TECHNICAL SKILLS (AFTER "with" ONLY):
   - EXTRACT ONLY TECHNICAL/TECHNOLOGY SKILLS from the skills section
   - ABSOLUTELY NO SOFT SKILLS like communication, teamwork, leadership, etc.
   - ONLY: programming languages, frameworks, tools, platforms, systems, databases

6. EXPERIENCE YEARS:
   - If title contains "Lead", "Senior", "Manager", "Architect", or "Project Manager": (15+)
   - Otherwise: (12+)
   - REMOVE any "(Experience+)" or similar text from title

7. OUTPUT MUST BE EXACT FORMAT: [Work Arrangement]/Local [Job Title] (Experience+ Certifications) with [Technical Skills] experience

NOW GENERATE THE TITLE FOLLOWING THESE STRICT RULES:"""

        result = self.make_llm_call(prompt, system_message, max_tokens=500, timeout=45)
        
        if result:
            title = result.strip()
            
            # Remove any introductory text
            unwanted_prefixes = [
                "Here is the generated technical title:",
                "Based on the provided document,",
                "Based on the analysis:",
                "The title is:",
                "Generated title:",
                "Here is the title:",
                "Based on the document,",
                "Here's the generated title:",
                "Title:"
            ]
            for prefix in unwanted_prefixes:
                if title.startswith(prefix):
                    title = title[len(prefix):].strip()

            print(f"  🎯 Skills-based Title: {title}")
            return title
        
        print("  ❌ Failed to generate title from skills")    
        return "Title generation failed"
        pass

def add_title_to_formatted_content(formatted_content, title):
    """Add the generated title to the formatted content below Job ID with proper spacing"""
    if not title or not formatted_content:
        return formatted_content
    
    # Clean the title - remove any remaining introductory text
    title = title.strip()
    if title.startswith(":"):
        title = title[1:].strip()
    
    # Split the formatted content into lines
    lines = formatted_content.split('\n')
    new_content = []
    job_id_found = False
    
    for line in lines:
        new_content.append(line)
        # Look for the Job ID line and insert title immediately after it
        if line.startswith('Job ID:') and not job_id_found:
            new_content.append('')  # Empty line after Job ID
            new_content.append(title)  # Add the title
            new_content.append('')  # Empty line after title
            job_id_found = True
    
    return '\n'.join(new_content)
    pass

def process_files_with_llm():
    """Process all files in dir_portal_outputs folder with LLM using REGEX-EXTRACTED data"""
    print("\n=== Starting LLM Processing with Regex-Extracted Data ===")
    
    # Load environment variables from .env file
    load_dotenv()
    
    # Get API key from environment variable
    groq_api_key = os.getenv('GROQ_API_KEY')
    
    if not groq_api_key:
        print("❌ GROQ_API_KEY not found in environment variables")
        return
    
    processor = PureLLMRequisitionProcessor(
        api_key=groq_api_key,
        model="llama-3.1-8b-instant"
    )
    
    title_generator = RequisitionTitleGenerator(
        api_key=groq_api_key,
        model="llama-3.1-8b-instant"
    )
    
    # Get all solicitation files (these should now contain REGEX-EXTRACTED data)
    solicitation_files = []
    output_dir = "dir_portal_outputs"
    if os.path.exists(output_dir):
        for file_name in os.listdir(output_dir):
            if file_name.startswith('Solicitation_Response_Number_') and file_name.endswith('.txt'):
                solicitation_files.append(os.path.join(output_dir, file_name))
    
    if not solicitation_files:
        print("No solicitation files found for LLM processing")
        return
    
    # Sort files to process smaller ones first (better success rate)
    solicitation_files.sort(key=lambda x: os.path.getsize(x))
    
    results = {}
    successful_files = 0
    failed_files = 0
    
    for file_path in solicitation_files:
        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        print(f"Processing {file_name} with LLM (using regex data)...")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                regex_content = f.read()  # This now contains REGEX-EXTRACTED data
            
            # STEP 1: Generate title FIRST using regex data
            print("  Step 1: Generating title from regex data...")
            title = title_generator.generate_title_from_regex_content(regex_content)
            print(f"  📝 Generated Title: {title}")

            if not title or "failed" in title.lower():
                print(f"  ❌ Title generation failed for {file_name}")
                failed_files += 1
                continue

            # Increased delay between title and content processing
            print("  ⏳ Waiting 8 seconds before content formatting...")
            time.sleep(30)
            
            # STEP 2: Format content SECOND (using the regex-extracted content)
            print("  Step 2: Formatting content from regex data...")
            formatted_content = processor.extract_all_data_pure_llm(regex_content, file_name)
            
            if formatted_content and "failed" not in formatted_content.lower() and title and "failed" not in title.lower():
                
                # STEP 3: Add generated title to formatted content
                print("  Step 3: Adding title to formatted content...")
                final_content = add_title_to_formatted_content(formatted_content, title)
                results[file_path] = final_content
                print(f"✅ Success: {file_name}")
                successful_files += 1
            else:
                # DON'T save failed processing
                print(f"❌ Failed: {file_name}")
                if "failed" in formatted_content.lower():
                    print(f"  ❌ Formatting failed")
                if "failed" in title.lower():
                    print(f"  ❌ Title generation failed")
                failed_files += 1
                # Skip this file - don't add to results
                continue
            
        except Exception as e:
            print(f"Error processing {file_name}: {str(e)}")
            failed_files += 1
            # Skip this file on error
            continue
        
        # Increased delay to avoid rate limiting - progressive waiting
        if successful_files % 2 == 0:  # Every 2 successful files, wait longer
            wait_time = 45
        else:
            wait_time = 35
            
        print(f"  ⏳ Waiting {wait_time} seconds before next request...")
        time.sleep(wait_time)
    
    # Only replace files that were successfully processed
    replaced_files = []
    for file_path, final_content in results.items():
        try:
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(final_content)
            replaced_files.append(file_path)
            print(f"✅ Saved enhanced content: {os.path.basename(file_path)}")
        except Exception as e:
            print(f"Error writing to {file_path}: {str(e)}")
            failed_files += 1
    
    print(f"🎉 LLM processing completed.")
    print(f"   ✅ Successfully processed: {successful_files} files")
    print(f"   ❌ Failed: {failed_files} files")
    print(f"   📁 Total enhanced: {len(replaced_files)} files")

    # If many failures due to rate limiting, suggest solution
    if failed_files > successful_files and failed_files > 2:
        print(f"\n⚠️  High failure rate detected - likely due to rate limiting.")
        print(f"   Consider:")
        print(f"   1. Using a different API key")
        print(f"   2. Increasing delays between requests")
        print(f"   3. Processing fewer files at once")
    pass