import os
import re
import time
import requests
from typing import Optional
from groq import Groq
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class PureLLMRequisitionProcessor:
    def __init__(self, api_key=None, model="llama-3.1-8b-instant"):
        self.api_key = api_key or os.getenv('GROQ_API_KEY')
        self.model = model
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"
        self.max_retries = 3
        self.retry_delay = 2

    def make_llm_call(self, prompt, system_message, max_tokens=2000, timeout=30):
        """Make LLM call"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": system_message
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.1,
            "max_tokens": max_tokens,
            "top_p": 0.9
        }
        
        for attempt in range(self.max_retries):
            try:
                print(f"  📡 LLM Call Attempt {attempt + 1}...")
                response = requests.post(self.base_url, headers=headers, json=payload, timeout=timeout)
                
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', 30))
                    print(f"  ⏳ Rate limited. Waiting {retry_after} seconds...")
                    time.sleep(retry_after)
                    continue
                    
                response.raise_for_status()
                result = response.json()
                
                if 'choices' in result and len(result['choices']) > 0:
                    print("  ✅ LLM call successful")
                    return result['choices'][0]['message']['content']
                else:
                    print("  ❌ No choices in response")
                    return None

            except requests.exceptions.Timeout:
                print(f"  ⏰ Timeout on attempt {attempt + 1}")
                if attempt < self.max_retries - 1:
                    time.sleep(10 * (attempt + 1))
                continue
                    
            except requests.exceptions.RequestException as e:
                print(f"  🔌 API connection error: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(5 * (attempt + 1))
                continue

        print("  ❌ All LLM attempts failed")               
        return None
    
    def get_deadline_date(self, clean_content):
        """
        Get the deadline date - with proper Virginia/NC logic
        """
        # First check if it's Virginia
        is_virginia = self.is_virginia_requisition(clean_content)
    
        if is_virginia:
            print("  🏛️  This is a Virginia requisition")
            # Virginia: Calculate 4 business days
            return self.calculate_4_business_days()
        else:
            print("  🌟 This is NOT Virginia (likely NC or other)")
            # Non-Virginia: Extract from "No New Submittals After:"
            return self.extract_date_mmd(clean_content)

    def is_virginia_requisition(self, clean_content):
        """Check if this is a Virginia requisition"""
        import re
    
        # Virginia indicators
        va_indicators = [
            r'VA-\d+',  # VA-12345 pattern
            r'Worksite Address:.*,\s*VA\s*\d',
            r'Location:.*,\s*VA\s*\d',
            r'Virginia',
        ]
    
        for pattern in va_indicators:
            if re.search(pattern, clean_content, re.IGNORECASE):
                return True
    
        return False

    def calculate_4_business_days(self):
        """Calculate 4 business days from today"""
        from datetime import datetime, timedelta
    
        today = datetime.now()
        business_days_added = 0
        current_date = today
    
        while business_days_added < 4:
            current_date += timedelta(days=1)
            # Check if it's a weekday (Monday=0, Sunday=6)
            if current_date.weekday() < 5:
               business_days_added += 1
    
        mmdd = current_date.strftime("%m%d")
        print(f"  📅 Calculated 4 business days: {mmdd}")
        return mmdd

    def extract_date_mmd(self, clean_content):
        """
        Manually extract and format date as MMDD from "No New Submittals After:" field
        Returns: MMDD string (e.g., "1215") or "0101" if not found
        """
        import re
        # FIRST: Check if the field exists at all
        if "No New Submittals After:" not in clean_content:
            print("  ⚠️  'No New Submittals After' NOT FOUND in text")
            return "0101"
    
        print("  ✅ 'No New Submittals After' IS PRESENT in text")
        # Try multiple patterns to match different date formats
        patterns = [
            # Pattern 1: MM/DD or MM-DD (NO YEAR) - THIS IS YOUR NC FORMAT!
            r'No New Submittals After:\s*(\d{1,2})[-/](\d{1,2})(?:\D|$)',
        
            # Pattern 2: MM/DD/YYYY or MM-DD-YYYY (with year)
            r'No New Submittals After:\s*(\d{1,2})[-/](\d{1,2})[-/](\d{4})',
        
            # Pattern 3: Just month and day separated by space
            r'No New Submittals After:\s*(\d{1,2})\s+(\d{1,2})',
        ]
        for pattern in patterns:
            date_match = re.search(pattern, clean_content)
            if date_match:
                month = date_match.group(1).zfill(2)  # Ensure 2 digits
                day = date_match.group(2).zfill(2)    # Ensure 2 digits
                mmdd = f"{month}{day}"
            
                if len(date_match.groups()) >= 3 and date_match.group(3):
                    print(f"  📅 Extracted date with year: {mmdd}")
                else:
                    print(f"  📅 Extracted date without year: {mmdd}")
            
                return mmdd
        # If we get here, we found the field but couldn't parse the date
        print("  ⚠️  'No New Submittals After' found but COULD NOT EXTRACT DATE")
        return "0101"  

    def format_extracted_data(self, clean_content, filename, title):
        """
        Format the extracted data into exact required format WITH TITLE IN CORRECT PLACE
        """
        from utils.vms_helpers import extract_bill_rates_from_all_sections
        
        # FIX: Call self.extract_date_mmd() not extract_deadline_date()
        date_mmd = self.get_deadline_date(clean_content)  # Use new logic
    
        bill_rates = extract_bill_rates_from_all_sections(clean_content)
    
        final_bill_rate = bill_rates.get('final_bill_rate', '00').split('.')[0]
        coded_id = f"9{final_bill_rate}9{date_mmd}"
    
        print(f"  💰 Using final bill rate: ${final_bill_rate}")
        print(f"  📅 Using date: {date_mmd}")
        print(f"  🆔 Job ID part will be: {coded_id}")
    
        prompt = f"""

CRITICAL: IGNORE ALL PREVIOUS DATA FROM OTHER REQUISITIONS. USE ONLY THE DATA PROVIDED BELOW.

IMPORTANT: DO NOT CONFUSE THIS WITH OTHER REQUISITIONS LIKE GA-788565. 
THIS IS A DIFFERENT REQUISITION WITH DIFFERENT DATA.

EXTRACTED JOB DATA:
{clean_content}

JOB TITLE TO USE: {title}

STRICTLY FOLLOW FORMAT THIS DATA EXACTLY AS SHOWN BELOW - NO ANALYSIS, NO EXPLANATIONS, NO ADDITIONAL TEXT:

Job ID: [State]-[RequisitionNumber] ({coded_id})

Location: [City, State (Work Location)]
Duration: [X Months]
Positions:[number_of_openings (max_submittals)]

skills:
[Skills as plain text list - NO TABLE FORMATTING]

Description:
[Combined description content without SHORT/COMPLETE headings]

CRITICAL INSTRUCTIONS - MUST FOLLOW EXACTLY:

1. OUTPUT ONLY THE FORMATTED RESULT - NO INTRODUCTORY TEXT, NO ANALYSIS, NO EXPLANATIONS
2. USE THIS EXACT TITLE: "{title}" - DO NOT MODIFY IT

3. JOB ID - CRITICAL: DO NOT USE GA-XXXXX, VA-XXXXX, NC-XXXXX OR ANY OTHER PREVIOUS JOB ID:
   - STATE: Find the "Worksite Address:" and extract the two-letter state abbreviation.
   - Extract the FULL requisition number (all digits) don't change 
   - FORMAT MUST BE EXACTLY: [State]-[Requisition Number] ({coded_id})
   - REMOVE DECIMAL POINTS AND ANY VALUES AFTER THEM 
   - EXAMPLE: "GA-788565 (98291216)"
   - DO NOT change the coded ID - use it exactly as provided: {coded_id}
   - EXAMPLES:
        - "85.50" → "85"
        - "137.00" → "137" 
        - "21.75" → "21"
        - "81.73" → "81"

4. LOCATION:
   - Find "Location:" field for city and state
   - Extract Work Location exactly 
   - Find the "Worksite Address:" field. Extract the city and state (2-letter code). Exclude the zip code.
   - Find the "Work Location:" field or similar in the descripthon section and extract the work location (e.g., "NCDHHS-NCFAST").
   - Format: "City, State (Work Location)" 

5. DURATION:
   - Find "Start Date:" and "End Date:" 
   - Calculate months between dates
   - Format: "X Months" (e.g., "12 Months")

6. POSITIONS:
   - Find "No. of Openings:" and also Max Submittals by Vendor and use that numbers
   - Format as "number_of_openings (Max Submittals by Vendor)" 

7. SKILLS:
   - Find the "SKILLS TABLE:" section and extract from there don't change anything like format and all 

8. DESCRIPTION:
   - COMBINE both "SHORT DESCRIPTION:" and "COMPLETE DESCRIPTION:" content
   - REMOVE the headers "SHORT DESCRIPTION:" and "COMPLETE DESCRIPTION:"
   - Keep all the actual description content
   - AFTER EACH PERIOD (.), START A NEW LINE FOR THE NEXT SENTENCE without line gap
   - REMOVE any analysis text like "Based on the provided job requisition..."
   UNIVERSAL DESCRIPTION SPACING:
   - IDENTIFY ALL section headers in the description using these rules:
     * Lines ending with ":" that are NOT continuations of sentences
     * Lines that are clearly section titles (standalone, not part of paragraphs)
     * Lines containing typical header words (Responsibilities, Qualifications, Requirements, Skills, Experience, Education, Duties, Overview,Preferred technical Skills etc.)
     * Lines that are formatted as headers (ALL CAPS, bold, underlined, or visually distinct)
     * FOR EACH SECTION HEADER: Insert exactly ONE blank line BEFORE the header
     * NO blank line AFTER the header - content should start immediately on the next line8iuuuuuuioop['
     ]
     * REMOVE ALL other blank lines from the entire description
     DESCRIPTION SPACING RULES:
     - IDENTIFY ALL section headers in the description (lines ending with ":" that are section titles)
     - FOR EACH SECTION HEADER: Insert exactly ONE blank line BEFORE the header
     - REMOVE the blank line immediately AFTER each header (content must start on the very next line with NO gap)
     - REMOVE ALL other blank lines from the entire description
     - PRESERVE all bullet points and original formatting
     - ENSURE: Header -> Immediate content (no blank line in between)

   HEADER DETECTION EXAMPLES:
   ✓ "RESPONSIBILITIES:" (header - add blank line before)
   ✓ "REQUIRED SKILLS:" (header - add blank line before)  
   ✓ "QUALIFICATIONS:" (header - add blank line before)
   ✓ "Work Environment: Professional office" (NOT a header - part of sentence)
   ✓ "Position: Compliance Officer" (NOT a header - part of sentence)
   - REMOVE ALL other blank lines from the entire description, except for the single blank lines inserted before headers as specified.
   - PRESERVE all original formatting, bullet points, and header names.
   - DO NOT add headers that aren't in the original text.
   

  FINAL RESULT MUST HAVE:
   - One blank line before each section header no blank line after header
   - AFTER EACH PERIOD (.), START A NEW LINE FOR THE NEXT SENTENCE without line gap
   - No other blank lines anywhere in the description
   - All original content preserved 
      CRITICAL: REMOVE ALL VENDOR, BILL, RATE, AND COST INFORMATION:
   - "Pay Rate: $XX.XX"
   - "Vendor Rate: $XX.XX"
   - "Maximum Vendor Submittal Rate is XX.XX/hr"
   - "Max Vendor Submittal Rate is XX.XX/hr"
   - "Maximum Vendor Submittal Rate is $XX.XX/hr"
   - "Max Vendor Submittal Rate is $XX.XX/hr"
   - "The max rate for this position is $XXX/hour
   - "Vendor Submittal Rate: $XX.XX"
   - "Bill Rate: $XX.XX"
   - "Hourly Rate: $XX.XX"
   - "Rate: $XX.XX"
   - "Cost: $XX.XX"
   - "Budget Rate: $XX.XX"
   - "is $XXX/hour"
   - "is $XXX/hr"
   - "Assignment Duration:"
   - "Work Environment:"
   - Any line containing "$" followed by numbers (e.g., "$76/hr", "$155.00/hour")
   - Any line containing "/hr" or "/hour" or "per hour"
   - Any line containing "rate" and numbers (e.g., "rate is 76/hr", "rate of $155")
   - Any line containing "submittal" and "rate" (e.g., "vendor submittal rate")
   
   SPECIFIC EXAMPLES TO REMOVE:
   - "System Analyst 3 Maximum Vendor Submittal Rate is 76/hr."
   - "Maximum Vendor Submittal Rate is $155.00/hour"
   - "Vendor Rate: $68.07/hour"
   - "Pay Rate: $85.50"
   - "Bill rate: $73.79"
   
   REMOVE THE ENTIRE LINE if it contains any of these patterns, even if it's part of a longer sentence.
Output your response in exactly this format with no additional text:
Job ID: [value]

title: [value]

Location: [value]
Duration: [value]
Positions: [value]

skills:
 [value]

Description:
[value]

No line gaps between Location,Duration,Position 
"""

        system_message = """You are a strict data formatter. You output ONLY the formatted result in the exact structure requested.

RULES:
1. NEVER add introductory text, analysis, or explanations
2. NEVER modify the provided title - use it exactly as given
3. Extract data precisely from the provided content
4. For skills: keep all the actual skills
5. For description: Remove any vendor or bill rate text and keep the actual job description
6. Output must match the exact format and structure shown
7. AFTER EACH PERIOD (.), START THE NEXT SENTENCE ON A NEW LINE WITHOUT ADDING ANY BLANK LINES without line gap
  - REMOVE the blank line immediately AFTER each header (content must start on the very next line with NO gap)
  - REMOVE ALL other blank lines from the entire description
8. JOB ID FORMAT MUST BE EXACTLY: [State]-[RequisitionNumber] (9{final_bill_rate}9{date_mmd})  
9. CRITICAL: Remove ALL vendor, bill, rate, and cost information from description:
   - Any line containing "$" followed by numbers (e.g., "$76/hr", "$155.00/hour")
   - Any line containing "/hr" or "/hour" or "per hour"
   - Any line containing "rate" and numbers (e.g., "rate is 76/hr")
   - Any line containing "submittal" and "rate" (e.g., "vendor submittal rate")
   - "Maximum Vendor Submittal Rate is XX.XX/hr"
   - "Max Vendor Submittal Rate is XX.XX/hr"
   - "The max rate for this position is $XXX/hour
   - "Pay Rate: $XX.XX"
   - "Vendor Rate: $XX.XX"
   - "Bill Rate: $XX.XX"
   - "is $XXX/hour"
   - "is $XXX/hr"
   - "Assignment Duration:"
   - "Work Environment:"
   - If a sentence contains rate information, remove the ENTIRE sentence
10. skills extract same as how it extracted from the regrex function 
11. REMOVE ALL other blank lines from the entire description
"""

        result = self.make_llm_call(prompt, system_message, max_tokens=4000, timeout=60)
        
        # Post-process the result to remove any unwanted analysis text
        if result:
            # Remove any lines that contain analysis keywords
            lines = result.split('\n')
            cleaned_lines = []
            analysis_keywords = ['based on', 'analysis:', 'here is', 'following', 'provided', 'job requisition']
            
            for line in lines:
                line_lower = line.lower()
                # Skip lines that look like analysis
                if any(keyword in line_lower for keyword in analysis_keywords) and not line.strip().startswith(('Job ID:', 'title:', 'Location:', 'Duration:', 'Positions:', 'skills:', 'Description:', '•')):
                    continue
                cleaned_lines.append(line)
            
            result = '\n'.join(cleaned_lines)
            
            # Ensure the title is exactly what we provided
            if f"title: {title}" not in result:
                # Find where to insert the title (after Job ID line)
                lines = result.split('\n')
                new_lines = []
                title_inserted = False

                for i, line in enumerate(lines):
                    new_lines.append(line)
                    if line.startswith('Job ID:') and not title_inserted:
                        # Remove spaces within the Job ID
                        if ' ' in line:
                            # Remove spaces between numbers in Job ID but keep the main structure
                            line = line.replace(' (9 ', ' (9').replace(' 9', '9').replace(' )', ')')
                            new_lines[-1] = line  # Replace the last added line

                        # Insert title line after Job ID line (without "title:" label)
                        new_lines.append('')  # Empty line for spacing
                        new_lines.append(title)
                        title_inserted = True
            
                result = '\n'.join(new_lines)

            # Remove any "title:" labels that might be in the output   
            result = result.replace(f"title: {title}", title)
            result = re.sub(r'^title:\s*', '', result, flags=re.MULTILINE)

        return result      
                

    def process_extracted_data(self, file_content, filename, title):
        """Process extracted data with exact formatting"""
        try:
            print(f"  🤖 Formatting extracted data: {filename}")
            
            # Format the extracted data WITH the title included
            formatted_content = self.format_extracted_data(file_content, filename, title)
            
            if formatted_content:
                print("  ✅ Data formatting complete")
                return formatted_content
            else:
                print("  ❌ LLM formatting failed")
                return None
            
        except Exception as e:
            print(f"  ❌ Error processing data: {str(e)}")
            return None


class RequisitionTitleGenerator:
    def __init__(self):
        api_key = os.getenv('GROQ_API_KEY')
        self.client = Groq(api_key=api_key)
        self.model = "llama-3.1-8b-instant"

    def generate_title(self, requisition_content: str) -> Optional[str]:
        """Generate title - LLM finds skills from both sections naturally"""
        prompt = f"""ANALYZE THIS JOB REQUISITION AND GENERATE A TECHNICAL TITLE:

REQUISITION CONTENT:
{requisition_content}

CRITICAL INSTRUCTIONS - MUST FOLLOW EXACTLY:

        1. FORMAT: [Work Arrangement]/Local [Job Title] (Experience+ Certifications) with [Technical Skills] experience

        2. WORK ARRANGEMENT: Find the "Work Arrangement:" field in the content and use that exact value

        3. JOB TITLE: Extract clean technical title only (remove anything after "/")
           - CREATE job title by analyzing the technical skills from BOTH the Skills Table AND Description sections.
           - Analyze what the person will actually DO based on the skills mentioned
           - Create an appropriate technical job title

        4. CERTIFICATIONS (IN PARENTHESES ONLY):
           - ONLY include actual certification names
           - NEVER include experience descriptions, skills, or qualifications
           - Example certifications: Salesforce Technical Architect, AWS Certified, PMP, CISSP
           - If no certifications found, use: (Experience+)

        5. TECHNICAL SKILLS (AFTER "with" ONLY):
           - EXTRACT ONLY TECHNICAL/TECHNOLOGY SKILLS
           - ABSOLUTELY NO SOFT SKILLS: NO "critical thinking", "teamwork", "communication", "problem-solving", "organizational skills"
           - ONLY: programming languages, frameworks, tools, platforms, systems, protocols, ServiceNow, Genetec, SQL Server, MS Excel, .NET, AWS, Azure
           - Examples: Java, Python, SQL, AWS, Azure, Docker, Kubernetes, React, .NET, HL7, Windows Server,SSRS/SSAS/SSIS
           - EXTRACT ONLY programming languages, tools, platforms, systems from Skills Table
           - ABSOLUTELY NO SOFT SKILLS, NO DESCRIPTIONS, NO REQUIREMENTS
           - REMOVE phrases like: "experience in", "knowledge of", "ability to", "understanding of"
           - REMOVE job descriptions like: "IT experience in distributed environment", "application development", "security measures"
           - Include relevant technical skills ONLY
           - FORMAT: Comma-separated technical skills only

        6. EXPERIENCE YEARS:
           - If title contains "Lead", "Senior", "Manager", "Architect", or "Project Manager": (15+)
           - Otherwise: (12+)

        7. OUTPUT MUST BE EXACT FORMAT: [Work Arrangement]/Local [Job Title] (Experience+ Certifications) with [Technical Skills] experience

        SKILLS (Go after "with"):
        - Abilities, technologies, or knowledge areas
        - Examples: Python, Java, JavaScript, React, Node.js, Angular, SQL, NoSQL, Docker, Kubernetes, AWS, Azure, GCP, Splunk, CrowdStrike, Nessus, Tableau, Power BI, machine learning, data analysis, network security, vulnerability management, restorations, dentures, extractions, patient care, dental procedures, financial analysis, risk assessment, project management, agile methodology, EagleSoft Electronic Oral Health Record, Salesforce, ServiceNow, Epic Systems, SAP, Oracle,SSRS/SSAS/SSIS,
        
        EXAMPLES OF CORRECT FORMAT:
        
        Example 1 : (Security Analyst):
        Hybrid/Local Security Analyst(12+ CISSP/CISM/Security+) with Splunk, CrowdStrike Falcon, Nessus, Tenable.sc, NIST, FISMA, vulnerability management, risk assessment experience
        
        Example 2 : (Dentist):
        Onsite/Local Dentist(12+ DDS/DMD Degree/FL Dental License/DEA/CPR) with restorations, dentures, extractions, EagleSoft Electronic Oral Health Record, patient care, dental procedures experience
        
        Example 3 : (Software Developer):
        Remote/Local Senior Full Stack Developer(15+ AWS/Azure) with Java, JavaScript, React, Node.js, Angular, SQL, NoSQL, microservices, CI/CD, Agile methodology experience
        
        Example 4 : (Salesforce Developer):
        Onsite/Local Salesforce Solutions Developer(12+ Salesforce Admin I and II/Salesforce Platform Developer I and II and/or Platform App Builder/Salesforce ServiceCloud Consultant/Copado I and II/CRT) with GITHUB, Copado, Jira, Shield, Lightning (LWC), Salesforce Flows, Salesforce Platform Community, Service Cloud, Gov Cloud, Ownbackup, Microsoft Office Suite (MS Word, EXCEL, PowerPoint, Visio), Agile methodology, Scrum, Kanban experience
        

        BAD EXAMPLES TO AVOID:
        - ❌ (12+ Hands-on experience with mobile device deployment) → REMOVE "Hands-on experience"
        - ❌ with critical thinking, teamwork, communication skills → REMOVE SOFT SKILLS
        - ❌ (Familiarity with Mobile Device Management) → NOT A CERTIFICATION

        GOOD EXAMPLES:
        - ✅ Onsite/Local Rhapsody Developer (12+) with Rhapsody Integration Engine, HL7/FHIR, .NET/C#, SQL, IIS, Windows Server, PowerShell, Oracle PL/SQL, NBS/NEDSS experience
        - ✅ Remote/Local Mobile Device Management Specialist (12+ Apple Certified Support Professional) with iOS, MDM platforms, mobile device deployment, IT security practices experience
        - ✅Remote/Local SQL Server DBA (Azure certification must) with HA/Clustering/DR, Hyper-V/VMware, T-SQL, PowerShell, Windows/Active Directory/CNO, SSRS, SSIS, SSAS, Redgate/SolarWinds/Sentry, DNS experience
        EXAMPLES OF CORRECT OUTPUT:
        - Remote/Local Service Support Analyst (12+) with ServiceNow, Genetec, SQL Server experience
        - Onsite/Local .NET Developer (12+) with .NET, SQL Server, REST APIs experience
        - Hybrid/Local Cloud Engineer (15+) with AWS, Azure, Terraform experience


        NOW GENERATE THE TITLE FOLLOWING THESE STRICT RULES:"""

        try:
            response = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "system", 
                        "content": """STRICT RULES: 
                        1. OUTPUT EXACT FORMAT: [Work Arrangement]/Local [Job Title] (Experience+ Certifications) with [Technical Skills] experience
                        2. CREATE NEW JOB TITLE by analyzing skills from both Skills Table AND Description
                        4. FIND Work Arrangement from the content
                        5. CERTIFICATIONS: Only include if explicitly mentioned, otherwise use (12+) or (15+)
                        6. AFTER "with": ONLY technical skills from analysis
                        7. NO SOFT SKILLS EVER
                        8. OUTPUT ONLY THE FINAL TITLE - NO ANALYSIS, NO EXPLANATION, NO REASONING"""
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                model=self.model,
                temperature=0.1,
                max_tokens=150
            )
            
            title = response.choices[0].message.content.strip()
            
            # STRICT CLEANING - Remove ANY analysis text
            lines = title.split('\n')
            final_title = None
            
            # Look for the line that matches our exact title format
            for line in lines:
                line = line.strip()
                # Check if this line matches our title format pattern
                if (('/Local ' in line or '/Local' in line) and 
                    ('(12+)' in line or '(15+)' in line) and 
                    'with' in line and 
                    'experience' in line):
                    final_title = line
                    break
            
            # If no exact format found, look for any line that starts with work arrangement
            if not final_title:
                work_arrangements = ['Onsite/', 'Remote/', 'Hybrid/']
                for line in lines:
                    line = line.strip()
                    if any(line.startswith(arrangement) for arrangement in work_arrangements):
                        final_title = line
                        break
            
            # If still no title found, use the first line and clean it aggressively
            if not final_title:
                first_line = lines[0].strip()
                # Remove any markdown formatting, asterisks, etc.
                first_line = re.sub(r'\*\*|\*|\[|\]|\(|\)|\#', '', first_line)
                # Remove common analysis phrases
                analysis_phrases = [
                    'Based on the provided job requisition',
                    'here is the analysis',
                    'Work Arrangement:',
                    'Job Title:',
                    'Explanation:',
                    'Final Output:',
                    'Technical Skills:',
                    'Certifications:'
                ]
                for phrase in analysis_phrases:
                    first_line = first_line.replace(phrase, '').strip()
                final_title = first_line
            
            # Final cleanup
            if final_title:
                final_title = self.clean_generated_title(final_title)
                print(f"  🎯 Generated Title: {final_title}")
                return final_title
            else:
                print("  ❌ Title generation failed")
                return None
                
        except Exception as e:
            print(f"Generation error: {e}")
            return None

    def generate_title_from_extracted_data(self, extracted_content: str) -> Optional[str]:
        """Generate title from extracted data - wrapper around generate_title"""
        return self.generate_title(extracted_content)

    def clean_generated_title(self, title: str) -> str:
        """Clean up the generated title to enforce rules"""
        # Remove any markdown formatting
        title = re.sub(r'\*\*|\*|__|_|\[|\]|#', '', title)
        
        # Remove common analysis phrases
        analysis_phrases = [
            'Based on the provided job requisition',
            'here is the analysis',
            'Work Arrangement:',
            'Job Title:',
            'Explanation:',
            'Final Output:',
            'Technical Skills:',
            'Certifications:',
            'has the analysis',
            'the analysis is',
            'following title:',
            'generated title:',
            'title is:'
        ]
        
        for phrase in analysis_phrases:
            title = title.replace(phrase, '').strip()
        
        # Remove anything in parentheses that's not certifications or experience
        if '(' in title and ')' in title:
            # Keep only (12+), (15+), or actual certifications
            paren_content = title.split('(')[1].split(')')[0]
            certification_indicators = ['certified', 'certification', 'license', 'credential', 'pmp', 'cissp', 'aws', 'azure', 'salesforce']
            if not any(indicator in paren_content.lower() for indicator in certification_indicators) and not any(exp in paren_content for exp in ['12+', '15+']):
                title = title.replace(f"({paren_content})", "").strip()
        
        # Clean the job title - remove anything after "/" in the job title part
        if "Local " in title:
            # Split the title into work arrangement and the rest
            parts = title.split("Local ", 1)
            if len(parts) == 2:
                work_arrangement = parts[0]  # "Onsite/" or "Remote/" etc.
                rest_of_title = parts[1]     # "Automated SW Tester/Analyst (12+) with..."
                
                # Clean the job title (part before parentheses)
                if '(' in rest_of_title:
                    job_title_part = rest_of_title.split('(', 1)[0].strip()
                    remaining_part = rest_of_title.split('(', 1)[1]
                    
                    # Remove anything after "/" in the job title
                    if '/' in job_title_part:
                        job_title_part = job_title_part.split('/')[0].strip()
                    
                    # Reconstruct the title
                    title = f"{work_arrangement}Local {job_title_part} ({remaining_part}"
        
        # Remove soft skills that might have slipped through
        soft_skills = [
            "critical thinking", "teamwork", "communication", "problem-solving",
            "organizational skills", "collaboration", "customer service",
            "attention to detail", "analytical skills", "time management",
            "interpersonal skills", "leadership", "mentoring", "training",
            "documentation", "presentation skills", "written communication",
            "verbal communication", "multitasking", "adaptability", "creativity",
            "strategic thinking", "decision making", "conflict resolution",
            "negotiation", "mentoring", "coaching", "facilitation"
        ]
        
        for skill in soft_skills:
            title = title.replace(f", {skill}", "").replace(f"{skill}, ", "")
        
        # Ensure certifications are only included if actually mentioned
        # If parentheses contain non-certification content, replace with just experience
        if '(' in title and ')' in title:
            paren_content = title.split('(')[1].split(')')[0]
            # Check if this looks like actual certifications or just experience
            certification_indicators = ['certified', 'certification', 'license', 'credential', 'pmp', 'cissp', 'aws', 'azure', 'salesforce']
            has_real_certifications = any(indicator in paren_content.lower() for indicator in certification_indicators)
            
            if not has_real_certifications and 'experience' in paren_content.lower():
                # Replace with just experience years
                if any(word in title.lower() for word in ['lead', 'senior', 'manager', 'architect', 'project manager']):
                    title = title.replace(f"({paren_content})", "(15+)")
                else:
                    title = title.replace(f"({paren_content})", "(12+)")
        
        # Ensure proper spacing
        title = re.sub(r'\s+', ' ', title)
        
        return title.strip()