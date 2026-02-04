import os
import re
from datetime import datetime

class RegexDataExtractor:
    def __init__(self):
        self.patterns = {
            'solicitation_number': [
                r'Solicitation Reference Number:\s*([A-Z0-9]+)',
                r'Response Number:\s*([A-Z0-9]+)',
                r'Solicitation Reference Number:\s*(\d+)',
                r'Reference Number:\s*([A-Z0-9]+)'
            ],
            'nte_rate': [
                r'NTE Rate:\$?([\d\.]+)',
                r'NTE Rate:\$([\d\.]+)',
                r'NTE Rate\s*\$([\d\.]+)',
                r'HHSC MAX NTE Rate:\s*\$?([\d\.]+)',
                r'MAX NTE Rate:\s*\$?([\d\.]+)',
            ],
            'response_deadline': [
                # ORIGINAL PATTERNS - They should work!
               r'response must be received by\s*(\d{1,2}/\d{1,2}/\d{4})',
               r'received by\s*(\d{1,2}/\d{1,2}/\d{4})',
               r'due by\s*(\d{1,2}/\d{1,2}/\d{4})',
    
               # NEW: Section VIII specific pattern (for your exact format)
               r'VIII\.\s*RESPONSE DEADLINE[\s\S]*?response must be received by[\s\S]*?(\d{1,2}/\d{1,2}/\d{4})',
               r'VIII\.\s*RESPONSE DEADLINE[\s\S]*?received by[\s\S]*?(\d{1,2}/\d{1,2}/\d{4})',
    
               # Fallback: Just look for any date in Section VIII
               r'VIII\.\s*RESPONSE DEADLINE[\s\S]*?(\d{1,2}/\d{1,2}/\d{4})',
            ],
            'work_location': [
                r'The primary work location.*?will be at\s*([^\n]+)',
                r'Work Location:\s*([^\n]+)',
                r'The primary work location will be\s*([^\n]+)',
            ],
            'work_arrangement': [
                r'Work Arrangement:\s*([^\n]+)',
                r'The working position is\s*([^\n]+)',
                r'working position\s*is\s*([^\n]+)',
                r'Position is\s*([^\n]+)',
            ],
            'start_date': [
                r'Services are expected to start\s*(\d{1,2}/\d{1,2}/\d{4})',
                r'Start Date:\s*(\d{1,2}/\d{1,2}/\d{4})',
            ],
            'end_date': [
                r'complete by\s*(\d{1,2}/\d{1,2}/\d{4})',
                r'End Date:\s*(\d{1,2}/\d{1,2}/\d{4})',
            ],
            'positions': [
                r'Vendor may submit no more than\s*(\d+)\s*candidate',
                r'may submit.*?(\d+)\s*candidate',
                r'requires the services of\s*(\d+)\s*([^,]+),',
            ],
            'skills_section': [
                r'II\.\s*CANDIDATE SKILLS AND QUALIFICATIONS(.*?)(?=III\.\s*TERMS OF SERVICE|IV\.\s*WORK HOURS AND LOCATION|$)',
                r'CANDIDATE SKILLS AND QUALIFICATIONS(.*?)(?=TERMS OF SERVICE|WORK HOURS AND LOCATION|$)',
                r'II\.\s*CANDIDATE SKILLS AND QUALIFICATIONS(.*?)(?=Minimum Requirements:)',
            ],
            'description_section': [
                r'I\.\s*DESCRIPTION OF SERVICES(.*?)(?=II\.\s*CANDIDATE SKILLS AND QUALIFICATIONS|CANDIDATE SKILLS AND QUALIFICATIONS|$)',
                r'DESCRIPTION OF SERVICES(.*?)(?=CANDIDATE SKILLS AND QUALIFICATIONS|$)',
                r'I\.\s*DESCRIPTION OF SERVICES(.*?)(?=Level Description|Job Description|Additional job details)',
            ],
            'department': [
                r'DEPARTMENT:\s*([^\n]+)',
                r'Texas Health and Human Services Commission',
                r'Texas Department of Family and Protective Services',
            ]
        }
        pass
    
    def extract_bill_rate_and_dates(self, file_content):
        """Enhanced extraction for bill rate and dates"""
        print("  🔍 Extracting bill_rate from document...")
        bill_rate = "000"
        
        all_nte_rates = []
        for pattern in self.patterns['nte_rate']:
            matches = re.findall(pattern, file_content, re.IGNORECASE)
            if matches:
                all_nte_rates.extend(matches)
                print(f"    ✅ Pattern found: {matches}")
        
        if all_nte_rates:
            try:
                bill_rates = [int(float(rate)) for rate in all_nte_rates]
                lowest_rate = min(bill_rates)
                bill_rate = str(lowest_rate)
                print(f"  ✅ Found {len(all_nte_rates)} NTE rates: {all_nte_rates}")
                print(f"  ✅ Using LOWEST BILL_RATE: {bill_rate}")
            except ValueError as e:
                print(f"  ❌ Error converting rates: {e}")
        else:
            print(f"  ⚠️ No NTE Rate found, using default: {bill_rate}")
        
        print("  🔍 Extracting due date from document...")
        date_mmdd = "0000"

        # SIMPLE AND DIRECT - No complex section extraction
        # Look for the exact text pattern
        date_match = re.search(r'response must be received by[^\d]*(\d{1,2})/(\d{1,2})/(\d{4})', file_content, re.IGNORECASE)

        if date_match:
            month = date_match.group(1).zfill(2)
            day = date_match.group(2).zfill(2)
            date_mmdd = month + day
            print(f"  ✅ Found date: {month}/{day}/2025")
            print(f"  ✅ Extracted MMDD: {date_mmdd}")
        else:
            print(f"  ⚠️ No due date found with simple pattern")
    
        if date_mmdd == "0000":
            print(f"  ⚠️ No due date found, using default: {date_mmdd}")
    
        return bill_rate, date_mmdd 
        pass
    
    def extract_core_data(self, raw_content, filename):
        """Extract only the essential data using regex from scraped content"""
        print(f"  🔍 Regex extracting core data from {filename}...")
        
        extracted = {}
        
        for field, patterns in self.patterns.items():
            if field in ['nte_rate', 'response_deadline']:
                continue
            
            for pattern in patterns:
                try:
                    if field in ['skills_section', 'description_section']:
                        match = re.search(pattern, raw_content, re.IGNORECASE | re.DOTALL)
                        if match:
                            content = match.group(1).strip()
                            # PRESERVE original line breaks - only clean up excessive spaces within lines
                            content = re.sub(r'[ \t]+', ' ', content)  # Clean up multiple spaces within lines
                            content = re.sub(r'\n[ \t]+\n', '\n\n', content)  # Clean up blank lines but keep paragraph breaks
                            extracted[field] = content
                            print(f"    ✅ Extracted {field}: {len(content)} chars")
                            break
                    else:
                        match = re.search(pattern, raw_content, re.IGNORECASE)
                        if match:
                            extracted[field] = match.group(1).strip()
                            print(f"    ✅ Extracted {field}: {match.group(1)}")
                            break
                except Exception as e:
                    continue
            else:
                extracted[field] = None
                print(f"    ❌ No match for {field}")
        
        # Extract bill rate and dates separately
        bill_rate, date_mmdd = self.extract_bill_rate_and_dates(raw_content)
        extracted['bill_rate'] = bill_rate
        extracted['response_deadline_mmdd'] = date_mmdd
    
        # ADD THIS: Extract the full date string
        extracted['due_date_full'] = self.extract_full_due_date(raw_content)
    
        return extracted
        pass
    
    def extract_full_due_date(self, file_content):
        """Extract the full due date string from document"""
        print("  🔍 Extracting full due date from document...")
        due_date_full = "Date not specified"
    
        for pattern in self.patterns['response_deadline']:
            date_match = re.search(pattern, file_content, re.IGNORECASE)
            if date_match:
                try:
                    due_date_full = date_match.group(1).strip()
                    print(f"  ✅ Extracted full due date: {due_date_full}")
                    break
                except Exception as e:
                    print(f"  ❌ Error extracting full date: {e}")
                    continue
    
        if due_date_full == "Date not specified":
            print(f"  ⚠️ No full due date found")
    
        return due_date_full
        pass
    
    def extract_clean_skills(self, raw_content):
        """Extract skills WITHOUT extra dashes - clean format"""
        skills = []
        
        # First try to extract the skills table section
        table_patterns = [
            r'Years\s*\|\s*Required/Preferred\s*\|\s*Experience(.*?)(?=III\.|IV\.|WORK HOURS|TERMS OF SERVICE|$)',
            r'Minimum Requirements:(.*?)(?=III\.|IV\.|WORK HOURS|TERMS OF SERVICE|$)',
        ]
        
        for table_pattern in table_patterns:
            table_match = re.search(table_pattern, raw_content, re.IGNORECASE | re.DOTALL)
            if table_match:
                table_content = table_match.group(1)
                print(f"    📊 Found skills table: {len(table_content)} chars")
                
                # Extract skills WITHOUT adding dashes
                skill_patterns = [
                    r'(\d+)\s*\|\s*(Required|Preferred)\s*\|\s*(.+?)(?=\n\d+\s*\||\n\n|\nIII\.|\nIV\.|$)',
                    r'(\d+)\s*(Required|Preferred)\s*(.+?)(?=\n\d+\s*|\n\n|\nIII\.|\nIV\.|$)',
                ]
                
                for skill_pattern in skill_patterns:
                    skill_rows = re.findall(skill_pattern, table_content, re.IGNORECASE | re.DOTALL)
                    if skill_rows:
                        for years, req_type, description in skill_rows:
                            # Clean up but DON'T add dashes
                            description = description.strip()
                            description = re.sub(r'\s+', ' ', description)
                            description = re.sub(r'^\|\s*', '', description)
                            
                            # NO DASH - clean format
                            skill_text = f"{years} Years {req_type} {description}"
                            skills.append(skill_text)
                            print(f"    ✅ Extracted CLEAN skill: {skill_text[:80]}...")
                        break
                
                if skills:
                    break
        
        return skills
        pass
    
    def extract_complete_description(self, raw_content):
        """Extract complete description with PROPER LINE BREAKS preserved - ONLY after periods"""
        description = ""
        
        for pattern in self.patterns['description_section']:
            match = re.search(pattern, raw_content, re.IGNORECASE | re.DOTALL)
            if match:
                description_content = match.group(1).strip()
                print(f"    📝 Found description section: {len(description_content)} chars")
                
                # PRESERVE ORIGINAL LINE BREAKS - don't compress into single line
                # Only clean up excessive spaces within lines, keep paragraph breaks
                description_content = re.sub(r'[ \t]+', ' ', description_content)  # Clean multiple spaces within lines
                description_content = re.sub(r'\n[ \t]+\n', '\n\n', description_content)  # Preserve paragraph breaks
                
                # Extract all parts of the description with proper formatting
                description_parts = []
                
                # Level Description - preserve line breaks
                level_match = re.search(r'Level Description(.*?)(?=Job Description|Additional job details|$)', description_content, re.IGNORECASE | re.DOTALL)
                if level_match:
                    level_desc = level_match.group(1).strip()
                    level_desc = re.sub(r'[ \t]+', ' ', level_desc)  # Clean spaces but keep line breaks
                    description_parts.append(f"LEVEL DESCRIPTION:\n{level_desc}")
                
                # Job Description - preserve line breaks
                job_match = re.search(r'Job Description(.*?)(?=Additional job details|$)', description_content, re.IGNORECASE | re.DOTALL)
                if job_match:
                    job_desc = job_match.group(1).strip()
                    job_desc = re.sub(r'[ \t]+', ' ', job_desc)  # Clean spaces but keep line breaks
                    description_parts.append(f"JOB DESCRIPTION:\n{job_desc}")
                
                # Additional details - preserve line breaks
                additional_match = re.search(r'Additional job details and special considerations(.*?)(?=$)', description_content, re.IGNORECASE | re.DOTALL)
                if additional_match:
                    additional_desc = additional_match.group(1).strip()
                    additional_desc = re.sub(r'[ \t]+', ' ', additional_desc)  # Clean spaces but keep line breaks
                    description_parts.append(f"ADDITIONAL DETAILS:\n{additional_desc}")
                
                # If no structured parts, use the whole content but preserve formatting
                if not description_parts:
                    # Remove the initial repetitive parts but keep line breaks
                    clean_content = re.sub(r'Texas Health and Human Services Commission\s+requires the services of\s+\d+\s+[^,]+,', '', description_content)
                    clean_content = re.sub(r'hereafter referred to as.*?All work products', 'All work products', clean_content, flags=re.DOTALL)
                    clean_content = clean_content.strip()
                    clean_content = re.sub(r'[ \t]+', ' ', clean_content)  # Clean spaces but keep line breaks
                    description_parts.append(clean_content)
                
                # Join with proper spacing between sections
                description = '\n\n'.join(description_parts)
                
                # FINAL CLEANUP: Add line breaks ONLY after periods (.)
                # This ensures sentences are properly separated
                description = re.sub(r'\.\s+', '.\n', description)  # Add line break after periods
                
                # Remove excessive blank lines but keep single blank lines between paragraphs
                description = re.sub(r'\n\s*\n\s*\n+', '\n\n', description)
                
                print(f"    ✅ Extracted complete description with period-based line breaks: {len(description)} chars")
                break
        
        return description
        pass
    
    def create_regex_extracted_content(self, extracted_data, filename):
        """Create COMPLETE file content with ONLY regex-extracted data"""

        # DEBUG: Print what's in extracted_data
        print(f"  🐛 DEBUG - extracted_data keys: {list(extracted_data.keys())}")
        print(f"  🐛 DEBUG - due_date_full: {extracted_data.get('due_date_full', 'NOT SET')}")
        print(f"  🐛 DEBUG - response_deadline_mmdd: {extracted_data.get('response_deadline_mmdd', 'NOT SET')}")
        
        content = []
        content.append("REGEX-EXTRACTED SOLICITATION DATA")
        content.append("=" * 60)
        content.append("")
        
        content.append("EXTRACTED DATA:")
        content.append("-" * 40)
        
        if extracted_data.get('solicitation_number'):
            content.append(f"Response Number: {extracted_data['solicitation_number']}")
        
        if extracted_data.get('department'):
            content.append(f"Department: {extracted_data['department']}")
        
        if extracted_data.get('bill_rate'):
            content.append(f"NTE Rate: ${extracted_data['bill_rate']}")
    
        # FIXED DATE HANDLING - Check what we actually have
        if extracted_data.get('due_date_full'):
            if extracted_data['due_date_full'] != "Date not specified":
                content.append(f"Response Deadline: {extracted_data['due_date_full']}")
                print(f"  📅 Added Response Deadline to file: {extracted_data['due_date_full']}")
            elif extracted_data.get('response_deadline_mmdd') and extracted_data['response_deadline_mmdd'] != "0000":
               mmdd = extracted_data['response_deadline_mmdd']
               # Convert MMDD to full date (assume current year)
               month = mmdd[:2]
               day = mmdd[2:]
               current_year = datetime.now().year
               content.append(f"Response Deadline: {month}/{day}/{current_year}")
               print(f"  📅 Added Response Deadline to file: {month}/{day}/{current_year}")
        elif extracted_data.get('response_deadline_mmdd') and extracted_data['response_deadline_mmdd'] != "0000":
            # Fallback if due_date_full doesn't exist
            mmdd = extracted_data['response_deadline_mmdd']
            month = mmdd[:2]
            day = mmdd[2:]
            current_year = datetime.now().year
            content.append(f"Response Deadline: {month}/{day}/{current_year}")
            print(f"  📅 Added Response Deadline (fallback): {month}/{day}/{current_year}")
        else:
            print(f"  ⚠️ No due date found to add to file")
        
        if extracted_data.get('start_date'):
            content.append(f"Start Date: {extracted_data['start_date']}")
        
        if extracted_data.get('end_date'):
            content.append(f"End Date: {extracted_data['end_date']}")
        
        if extracted_data.get('work_arrangement'):
            content.append(f"Work Arrangement: {extracted_data['work_arrangement']}")
        else:
            content.append("Work Arrangement: Not specified")
        
        location = extracted_data.get('work_location', 'Not specified')
        content.append(f"Location: {location}")
        
        content.append(f"Positions: {extracted_data.get('positions', 'Unknown')}")
        content.append("")
        
        # Use the CLEAN skills extraction (no dashes)
        skills_list = self.extract_clean_skills(extracted_data.get('raw_content', ''))
        if skills_list:
            content.append("SKILLS:")
            content.append("-" * 30)
            for skill in skills_list:
                content.append(f"    {skill}")
            content.append("")
        
        # Use the COMPLETE description extraction with period-based line breaks
        complete_description = self.extract_complete_description(extracted_data.get('raw_content', ''))
        if complete_description:
            content.append("DESCRIPTION:")
            content.append("-" * 30)
            if len(complete_description) > 2500:
                complete_description = complete_description[:2500] + "... [truncated]"
            # Add the description content AS-IS with preserved line breaks
            content.append(complete_description)
            content.append("")
        
        content.append("=" * 60)
        content.append("END EXTRACTED DATA")
        
        return '\n'.join(content)
        pass

def extract_data_with_regex():
    """STEP: Extract core data with regex and REPLACE file content"""
    print("\n" + "="*70)
    print("STEP: REGEX DATA EXTRACTION & REPLACEMENT")
    print("="*70)
    
    output_dir = "dir_portal_outputs"
    if not os.path.exists(output_dir):
        print("❌ No output directory found")
        return 0
    
    extractor = RegexDataExtractor()
    processed_count = 0
    
    for filename in os.listdir(output_dir):
        if filename.startswith("Solicitation_Response_Number_") and filename.endswith(".txt"):
            try:
                filepath = os.path.join(output_dir, filename)
                
                with open(filepath, 'r', encoding='utf-8') as f:
                    original_content = f.read()
                
                print(f"\n📄 Regex Processing: {filename}")
                print(f"   Original scraped content: {len(original_content)} chars")
                
                extracted_data = extractor.extract_core_data(original_content, filename)
                extracted_data['raw_content'] = original_content
                
                regex_content = extractor.create_regex_extracted_content(extracted_data, filename)
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(regex_content)
                
                processed_count += 1
                print(f"✅ REPLACED with regex content: {len(regex_content)} chars")
                print(f"   Content reduced by: {len(original_content) - len(regex_content)} chars")
                
            except Exception as e:
                print(f"❌ Error in regex extraction: {str(e)}")
                import traceback
                traceback.print_exc()
    
    print(f"\n🎉 REGEX EXTRACTION COMPLETED: {processed_count} files REPLACED")
    return processed_count
    pass