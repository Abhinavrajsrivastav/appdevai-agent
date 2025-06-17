import asyncio
import logging
import re
from typing import Dict, Any, List, Optional
import json
import datetime
import uuid
import os
import sqlite3
import random

# Import for web automation
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

# Import utilities
from utils import extract_text_from_pdf
from config import GEMINI_API_KEY

# Configure logging
logger = logging.getLogger(__name__)

# Initialize database
DB_PATH = os.path.join(os.path.dirname(__file__), "applications.db")

def init_db():
    """Initialize the database schema if it doesn't exist"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create applications table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_title TEXT NOT NULL,
        company TEXT NOT NULL,
        job_url TEXT NOT NULL,
        application_date TEXT NOT NULL,
        status TEXT NOT NULL,
        resume_data TEXT,
        application_data TEXT,
        UNIQUE(job_url)
    )
    ''')
    
    conn.commit()
    conn.close()
    logger.info("Application database initialized")

# Initialize database on module import
init_db()

class ResumeParser:
    """Extract structured data from resume text"""
    
    def parse_resume(self, resume_text: str) -> Dict[str, Any]:
        """Parse resume text into structured data"""
        result = {
            "full_name": "",
            "first_name": "",
            "last_name": "",
            "email": "",
            "phone": "",
            "location": "",
            "education": [],
            "experience": [],
            "skills": []
        }
        
        # Extract basic contact information
        result.update(self._extract_contact_info(resume_text))
        
        # Extract education
        result["education"] = self._extract_education(resume_text)
        
        # Extract work experience
        result["experience"] = self._extract_experience(resume_text)
        
        # Extract skills
        result["skills"] = self._extract_skills(resume_text)
        
        return result
    
    def _extract_contact_info(self, text: str) -> Dict[str, str]:
        """Extract contact information from resume text"""
        info = {}
        
        # Extract email
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
        if email_match:
            info["email"] = email_match.group(0)
        
        # Extract phone number (various formats)
        phone_match = re.search(r'(\+\d{1,2}\s?)?(\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4})', text)
        if phone_match:
            info["phone"] = phone_match.group(0)
        
        # Extract name (usually at the beginning of the resume)
        # Simplified approach: assume the first line contains the name
        lines = text.strip().split('\n')
        if lines:
            potential_name = lines[0].strip()
            # Check if it looks like a name (no special characters, not too long)
            if len(potential_name) < 50 and re.match(r'^[A-Za-z\s\.-]+$', potential_name):
                info["full_name"] = potential_name
                
                # Split into first and last name
                name_parts = potential_name.split()
                if len(name_parts) >= 2:
                    info["first_name"] = name_parts[0]
                    info["last_name"] = name_parts[-1]
                elif len(name_parts) == 1:
                    info["first_name"] = name_parts[0]
        
        # Extract location/address (look for common location patterns)
        address_pattern = r'\b[A-Z][a-z]+,\s*[A-Z]{2}\s*\d{5}\b'  # City, State ZIP
        address_match = re.search(address_pattern, text)
        if address_match:
            info["location"] = address_match.group(0)
        else:
            # Try another pattern: just city and state
            city_state_pattern = r'\b[A-Z][a-z]+,\s*[A-Z]{2}\b'
            city_state_match = re.search(city_state_pattern, text)
            if city_state_match:
                info["location"] = city_state_match.group(0)
        
        return info
    
    def _extract_education(self, text: str) -> List[Dict[str, str]]:
        """Extract education information from resume"""
        education = []
        
        # Find education section
        education_section = self._extract_section(text, ["education", "academic background", "academic history"])
        if not education_section:
            return education
        
        # Extract degree patterns
        degree_patterns = [
            r'(Bachelor|Master|PhD|Doctorate|Associate|B\.S\.|M\.S\.|B\.A\.|M\.A\.|B\.Tech|M\.Tech|M\.B\.A\.)',
            r'(High School Diploma)'
        ]
        
        for pattern in degree_patterns:
            for match in re.finditer(pattern, education_section, re.IGNORECASE):
                degree = match.group(0)
                
                # Get surrounding text (100 characters before and after)
                start_idx = max(0, match.start() - 100)
                end_idx = min(len(education_section), match.end() + 100)
                context = education_section[start_idx:end_idx]
                
                # Try to extract institution
                institution_pattern = r'(University|College|Institute|School) of ([A-Za-z\s&]+)'
                institution_match = re.search(institution_pattern, context, re.IGNORECASE)
                institution = ""
                if institution_match:
                    institution = institution_match.group(0)
                
                # Try to extract dates
                date_pattern = r'(19|20)\d{2}\s*(-|to|–|—)\s*(19|20)\d{2}|((19|20)\d{2})\s*(-|to|–|—)\s*(Present|Current)'
                date_match = re.search(date_pattern, context, re.IGNORECASE)
                date_range = date_match.group(0) if date_match else ""
                
                education.append({
                    "degree": degree,
                    "institution": institution,
                    "date_range": date_range,
                    "context": context
                })
        
        return education
    
    def _extract_experience(self, text: str) -> List[Dict[str, str]]:
        """Extract work experience information from resume"""
        experience = []
        
        # Find experience section
        experience_section = self._extract_section(text, ["experience", "work history", "employment", "professional experience"])
        if not experience_section:
            return experience
        
        # Look for company and title patterns
        # This is a simplified approach - real-world resumes vary greatly
        
        # Pattern: Job Title at Company Name (Date - Date)
        job_pattern = r'([A-Za-z\s]+) at ([A-Za-z\s&]+) \((\d{4}.*?)\)'
        for match in re.finditer(job_pattern, experience_section):
            title = match.group(1).strip()
            company = match.group(2).strip()
            date_range = match.group(3).strip()
            
            # Get surrounding text for description
            start_idx = max(0, match.start() - 50)
            end_idx = min(len(experience_section), match.end() + 200)
            description = experience_section[start_idx:end_idx]
            
            experience.append({
                "title": title,
                "company": company,
                "date_range": date_range,
                "description": description
            })
        
        # If no matches found, try alternative pattern
        if not experience:
            # Look for lines that might contain job titles and companies
            lines = experience_section.split('\n')
            for i, line in enumerate(lines):
                # Look for patterns like "Job Title - Company"
                job_company_pattern = r'([A-Za-z\s]+) - ([A-Za-z\s&]+)'
                match = re.search(job_company_pattern, line)
                if match:
                    title = match.group(1).strip()
                    company = match.group(2).strip()
                    
                    # Look for dates in the same line or next line
                    date_pattern = r'(19|20)\d{2}\s*(-|to|–|—)\s*(19|20)\d{2}|((19|20)\d{2})\s*(-|to|–|—)\s*(Present|Current)'
                    date_match = None
                    if i < len(lines) - 1:
                        date_match = re.search(date_pattern, lines[i] + " " + lines[i+1], re.IGNORECASE)
                    else:
                        date_match = re.search(date_pattern, line, re.IGNORECASE)
                    
                    date_range = date_match.group(0) if date_match else ""
                    
                    # Get description from following lines
                    description = "\n".join(lines[i:min(i+5, len(lines))])
                    
                    experience.append({
                        "title": title,
                        "company": company,
                        "date_range": date_range,
                        "description": description
                    })
        
        return experience
    
    def _extract_skills(self, text: str) -> List[str]:
        """Extract skills from resume text"""
        skills = []
        
        # Find skills section
        skills_section = self._extract_section(text, ["skills", "technical skills", "core competencies", "proficiencies"])
        
        if skills_section:
            # Common technical skills to look for
            skill_patterns = [
                r'python', r'java', r'javascript', r'typescript', r'html', r'css', r'sql', r'react', r'angular', r'vue', 
                r'node\.js', r'django', r'flask', r'spring', r'aws', r'azure', r'gcp', r'docker', r'kubernetes',
                r'machine learning', r'artificial intelligence', r'data science', r'data analysis',
                r'product management', r'scrum', r'agile', r'waterfall', r'jira', r'confluence',
                r'photoshop', r'illustrator', r'indesign', r'figma', r'sketch', r'xd'
            ]
            
            for pattern in skill_patterns:
                if re.search(pattern, skills_section.lower()):
                    skills.append(pattern.replace('\\', ''))
            
            # Also extract skills formatted as lists
            list_items = re.findall(r'[•·-]\s*([^•·-\n]+)', skills_section)
            for item in list_items:
                if len(item.strip()) > 0 and len(item.strip()) < 50:  # Reasonable length for a skill
                    skills.append(item.strip())
        else:
            # If no skills section found, try to extract skills from the whole resume
            common_skills = [
                "Python", "Java", "JavaScript", "HTML", "CSS", "SQL", "React", "Angular", "Node.js", 
                "C++", "C#", "Ruby", "Swift", "Kotlin", "PHP", "Go", "Rust", "Scala",
                "AWS", "Azure", "GCP", "Docker", "Kubernetes", "Git", "CI/CD", "Jenkins", "TeamCity",
                "Agile", "Scrum", "Kanban", "JIRA", "Confluence", "Trello", "MS Office", "Excel"
            ]
            
            for skill in common_skills:
                if re.search(r'\b' + re.escape(skill) + r'\b', text, re.IGNORECASE):
                    skills.append(skill)
        
        return list(set(skills))  # Remove duplicates
    
    def _extract_section(self, text: str, section_names: List[str]) -> str:
        """Extract a section from the resume based on section names"""
        # Convert text to lowercase for case-insensitive matching
        text_lower = text.lower()
        
        # Find the start of the section
        section_start = -1
        section_name_found = ""
        for name in section_names:
            # Look for section header pattern (uppercase, followed by colon or newline)
            pattern = f"(^|\n)\\s*{name}[:\\s]*(\n|$)"
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                section_start = match.end()
                section_name_found = name
                break
        
        if section_start == -1:
            return ""
        
        # Find the start of the next section
        next_section_pattern = r'(^|\n)\s*[A-Z][A-Z\s]+[A-Z][:\s]*(\n|$)'
        next_section_match = re.search(next_section_pattern, text[section_start:], re.MULTILINE)
        
        if next_section_match:
            section_end = section_start + next_section_match.start()
        else:
            section_end = len(text)
        
        return text[section_start:section_end].strip()

class JobApplicationAutomator:
    """Automate job applications using web browser automation"""
    
    def __init__(self):
        self.driver = None
        self.wait = None
        self.resume_parser = ResumeParser()
    
    async def setup_driver(self):
        """Initialize the web driver"""
        if not SELENIUM_AVAILABLE:
            logger.error("Selenium is not installed. Cannot set up web driver.")
            return False
        
        try:
            # Set up Chrome options
            options = Options()
            options.add_argument("--headless")  # Run in headless mode
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1920,1080")
            options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36")
            
            # Initialize Chrome driver
            self.driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=options
            )
            
            # Set up wait
            self.wait = WebDriverWait(self.driver, 10)  # 10 seconds timeout
            logger.info("Web driver set up successfully")
            return True
        
        except Exception as e:
            logger.error(f"Error setting up web driver: {str(e)}")
            return False
    
    async def apply_to_job(self, job_data: Dict[str, Any], resume_content: str) -> Dict[str, Any]:
        """Apply to a job using the provided resume data"""
        if not SELENIUM_AVAILABLE:
            return {
                "status": "failed",
                "reason": "Selenium is not installed. Cannot automate job applications."
            }
        
        if not self.driver:
            success = await self.setup_driver()
            if not success:
                return {
                    "status": "failed",
                    "reason": "Could not set up web driver."
                }
        
        # Parse resume
        parsed_resume = self.resume_parser.parse_resume(resume_content)
        
        # Get job information
        job_url = job_data.get("application_link", "")
        job_title = job_data.get("job_title", "Unknown Position")
        company = job_data.get("company_name", "Unknown Company")
        
        if not job_url or job_url == "#":
            return {
                "status": "failed",
                "reason": "No valid application link provided."
            }
        
        # Check if we've already applied to this job
        application_exists = await self.check_application_exists(job_url)
        if application_exists:
            return {
                "status": "already_applied",
                "message": "You have already applied to this job.",
                "job_url": job_url
            }
        
        # Log the attempt
        logger.info(f"Attempting to apply to job: {job_title} at {company}")
        logger.info(f"Application URL: {job_url}")
        
        try:
            # Navigate to job application page
            self.driver.get(job_url)
            logger.info(f"Navigated to {job_url}")
            
            # Wait for page to load
            await asyncio.sleep(3)
            
            # Log the current URL (may have redirected)
            current_url = self.driver.current_url
            logger.info(f"Current URL after navigation: {current_url}")
            
            # Check if we landed on a job page
            if "linkedin.com" in current_url.lower():
                return await self._handle_linkedin_application(job_data, parsed_resume)
            elif "indeed.com" in current_url.lower():
                return await self._handle_indeed_application(job_data, parsed_resume)
            elif "glassdoor.com" in current_url.lower():
                return await self._handle_glassdoor_application(job_data, parsed_resume)
            else:
                # Generic application process
                return await self._handle_generic_application(job_data, parsed_resume)
        
        except Exception as e:
            logger.error(f"Error applying to job: {str(e)}")
            return {
                "status": "failed",
                "reason": f"Error during application process: {str(e)}",
                "job_url": job_url
            }
    
    async def _handle_linkedin_application(self, job_data: Dict[str, Any], resume_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle application on LinkedIn"""
        job_url = job_data.get("application_link", "")
        job_title = job_data.get("job_title", "Unknown Position")
        company = job_data.get("company_name", "Unknown Company")
        
        try:
            # Look for the Apply button
            apply_buttons = self.driver.find_elements(By.XPATH, "//button[contains(text(), 'Apply') or contains(@aria-label, 'Apply')]")
            easy_apply_buttons = self.driver.find_elements(By.XPATH, "//button[contains(text(), 'Easy Apply') or contains(@aria-label, 'Easy Apply')]")
            
            if easy_apply_buttons:
                # Click Easy Apply button
                easy_apply_buttons[0].click()
                logger.info("Clicked 'Easy Apply' button")
                await asyncio.sleep(2)
                
                # Handle LinkedIn application flow (simplified)
                # In a real implementation, you'd need more complex logic to handle various forms
                
                # Record the application
                await self.record_application(job_data, resume_data)
                
                return {
                    "status": "initiated",
                    "message": "LinkedIn Easy Apply initiated. Manual completion required.",
                    "job_url": job_url
                }
                
            elif apply_buttons:
                # Click Apply button
                apply_buttons[0].click()
                logger.info("Clicked 'Apply' button")
                await asyncio.sleep(2)
                
                # Check if redirected to external site
                current_url = self.driver.current_url
                if current_url != job_url:
                    logger.info(f"Redirected to external application site: {current_url}")
                    
                    # Record the application
                    await self.record_application(job_data, resume_data)
                    
                    return {
                        "status": "redirected",
                        "message": "Redirected to external application site. Manual completion required.",
                        "redirect_url": current_url,
                        "job_url": job_url
                    }
            else:
                return {
                    "status": "failed",
                    "reason": "Could not find apply button on LinkedIn job page.",
                    "job_url": job_url
                }
        
        except Exception as e:
            logger.error(f"Error with LinkedIn application: {str(e)}")
            return {
                "status": "failed",
                "reason": f"Error with LinkedIn application: {str(e)}",
                "job_url": job_url
            }
    
    async def _handle_indeed_application(self, job_data: Dict[str, Any], resume_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle application on Indeed"""
        job_url = job_data.get("application_link", "")
        job_title = job_data.get("job_title", "Unknown Position")
        company = job_data.get("company_name", "Unknown Company")
        
        try:
            # Look for the Apply button
            apply_buttons = self.driver.find_elements(By.XPATH, "//button[contains(text(), 'Apply now') or contains(text(), 'Apply')]")
            
            if apply_buttons:
                # Click Apply button
                apply_buttons[0].click()
                logger.info("Clicked 'Apply now' button on Indeed")
                await asyncio.sleep(2)
                
                # Record the application
                await self.record_application(job_data, resume_data)
                
                return {
                    "status": "initiated",
                    "message": "Indeed application initiated. Manual completion required.",
                    "job_url": job_url
                }
            else:
                return {
                    "status": "failed",
                    "reason": "Could not find apply button on Indeed job page.",
                    "job_url": job_url
                }
        
        except Exception as e:
            logger.error(f"Error with Indeed application: {str(e)}")
            return {
                "status": "failed",
                "reason": f"Error with Indeed application: {str(e)}",
                "job_url": job_url
            }
    
    async def _handle_glassdoor_application(self, job_data: Dict[str, Any], resume_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle application on Glassdoor"""
        job_url = job_data.get("application_link", "")
        job_title = job_data.get("job_title", "Unknown Position")
        company = job_data.get("company_name", "Unknown Company")
        
        try:
            # Look for the Apply button
            apply_buttons = self.driver.find_elements(By.XPATH, "//button[contains(text(), 'Apply Now') or contains(text(), 'Apply')] | //a[contains(text(), 'Apply Now') or contains(text(), 'Apply')]")
            
            if apply_buttons:
                # Click Apply button
                apply_buttons[0].click()
                logger.info("Clicked 'Apply Now' button on Glassdoor")
                await asyncio.sleep(2)
                
                # Record the application
                await self.record_application(job_data, resume_data)
                
                # Check if redirected to external site
                current_url = self.driver.current_url
                if current_url != job_url:
                    logger.info(f"Redirected to external application site: {current_url}")
                    
                    return {
                        "status": "redirected",
                        "message": "Redirected to external application site. Manual completion required.",
                        "redirect_url": current_url,
                        "job_url": job_url
                    }
                
                return {
                    "status": "initiated",
                    "message": "Glassdoor application initiated. Manual completion required.",
                    "job_url": job_url
                }
            else:
                return {
                    "status": "failed",
                    "reason": "Could not find apply button on Glassdoor job page.",
                    "job_url": job_url
                }
        
        except Exception as e:
            logger.error(f"Error with Glassdoor application: {str(e)}")
            return {
                "status": "failed",
                "reason": f"Error with Glassdoor application: {str(e)}",
                "job_url": job_url
            }
    
    async def _handle_generic_application(self, job_data: Dict[str, Any], resume_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle application on generic job site"""
        job_url = job_data.get("application_link", "")
        job_title = job_data.get("job_title", "Unknown Position")
        company = job_data.get("company_name", "Unknown Company")
        
        try:
            # Look for common apply button patterns
            apply_patterns = [
                "//button[contains(text(), 'Apply') or contains(text(), 'apply') or contains(@class, 'apply')]",
                "//a[contains(text(), 'Apply') or contains(text(), 'apply') or contains(@class, 'apply')]",
                "//input[@type='submit' and (contains(@value, 'Apply') or contains(@value, 'apply'))]"
            ]
            
            apply_button = None
            for pattern in apply_patterns:
                buttons = self.driver.find_elements(By.XPATH, pattern)
                if buttons:
                    apply_button = buttons[0]
                    break
            
            if apply_button:
                # Click Apply button
                apply_button.click()
                logger.info(f"Clicked apply button on generic job page: {job_url}")
                await asyncio.sleep(2)
                
                # Record the application
                await self.record_application(job_data, resume_data)
                
                # Check if redirected to external site
                current_url = self.driver.current_url
                if current_url != job_url:
                    logger.info(f"Redirected to external application site: {current_url}")
                    
                    return {
                        "status": "redirected",
                        "message": "Redirected to external application site. Manual completion required.",
                        "redirect_url": current_url,
                        "job_url": job_url
                    }
                
                return {
                    "status": "initiated",
                    "message": "Application initiated. Manual completion required.",
                    "job_url": job_url
                }
            else:
                # If we can't find an apply button, consider this a manual apply situation
                # Record the job anyway
                await self.record_application(job_data, resume_data)
                
                return {
                    "status": "manual_required",
                    "message": "Could not find automatic application method. Manual application required.",
                    "job_url": job_url
                }
        
        except Exception as e:
            logger.error(f"Error with generic application: {str(e)}")
            return {
                "status": "failed",
                "reason": f"Error with application: {str(e)}",
                "job_url": job_url
            }
    
    async def check_application_exists(self, job_url: str) -> bool:
        """Check if an application already exists for the given job URL"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute('SELECT id FROM applications WHERE job_url = ?', (job_url,))
            result = cursor.fetchone()
            
            conn.close()
            
            return result is not None
        
        except Exception as e:
            logger.error(f"Error checking application existence: {str(e)}")
            return False
    
    async def record_application(self, job_data: Dict[str, Any], resume_data: Dict[str, Any]) -> int:
        """Record an application in the database"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Prepare data
            job_url = job_data.get("application_link", "")
            job_title = job_data.get("job_title", "Unknown Position")
            company = job_data.get("company_name", "Unknown Company")
            now = datetime.datetime.now().isoformat()
            
            # Convert data to JSON for storage
            resume_json = json.dumps(resume_data)
            job_json = json.dumps(job_data)
            
            # Insert application record
            cursor.execute('''
            INSERT INTO applications 
            (job_title, company, job_url, application_date, status, resume_data, application_data)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                job_title, 
                company, 
                job_url, 
                now, 
                "initiated", 
                resume_json,
                job_json
            ))
            
            application_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            logger.info(f"Recorded application #{application_id} for {job_title} at {company}")
            return application_id
        
        except sqlite3.IntegrityError:
            # Handle duplicate application
            logger.warning(f"Attempted to add duplicate application for {job_url}")
            conn.close()
            return -1
        
        except Exception as e:
            logger.error(f"Error recording application: {str(e)}")
            if 'conn' in locals():
                conn.close()
            return -1
    
    async def get_all_applications(self) -> List[Dict[str, Any]]:
        """Get all applications from the database"""
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT * FROM applications ORDER BY application_date DESC
            ''')
            
            rows = cursor.fetchall()
            conn.close()
            
            applications = []
            for row in rows:
                application = dict(row)
                
                # Parse JSON fields
                if application.get("resume_data"):
                    application["resume_data"] = json.loads(application["resume_data"])
                
                if application.get("application_data"):
                    application["application_data"] = json.loads(application["application_data"])
                
                applications.append(application)
            
            return applications
        
        except Exception as e:
            logger.error(f"Error getting applications: {str(e)}")
            if 'conn' in locals():
                conn.close()
            return []
    
    def close(self):
        """Close the browser"""
        if self.driver:
            self.driver.quit()
            self.driver = None
            logger.info("Closed web driver")

# Function to use for applying to jobs
async def automated_job_application(job_data: Dict[str, Any], resume_content: str) -> Dict[str, Any]:
    """Apply to a job automatically"""
    if not GEMINI_API_KEY or GEMINI_API_KEY == "your-api-key-here":
        logger.error("Invalid or missing Gemini API key")
        return {
            "error": "The Gemini API key is not configured. Please add a valid API key to the .env file."
        }
    
    # Check if web automation is available
    if not SELENIUM_AVAILABLE:
        return {
            "status": "unavailable",
            "reason": "Web automation is not available. Please install selenium with 'pip install selenium webdriver_manager'",
            "manual_url": job_data.get("application_link", "#")
        }
    
    try:
        # Initialize automator
        automator = JobApplicationAutomator()
        
        # Apply to the job
        result = await automator.apply_to_job(job_data, resume_content)
        
        # Close the browser when done
        automator.close()
        
        return result
    
    except Exception as e:
        logger.error(f"Error in automated job application: {str(e)}")
        return {
            "status": "failed",
            "reason": f"Error: {str(e)}",
            "job_url": job_data.get("application_link", "#")
        }

# Function to get all applications
async def get_applications() -> Dict[str, Any]:
    """Get all recorded job applications"""
    try:
        automator = JobApplicationAutomator()
        applications = await automator.get_all_applications()
        
        return {
            "status": "success",
            "applications": applications
        }
    
    except Exception as e:
        logger.error(f"Error getting applications: {str(e)}")
        return {
            "status": "failed",
            "reason": f"Error: {str(e)}",
            "applications": []
        }
