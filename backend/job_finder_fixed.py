async def job_finder(resume_content: str, experience_years: float, location: str, job_type: str = None) -> Dict[str, Any]:
    """Find relevant job opportunities"""
    if not GEMINI_API_KEY or GEMINI_API_KEY == "your-api-key-here":
        logger.error("Invalid or missing Gemini API key in job_finder")
        return {
            "error": "The Gemini API key is not configured. Please add a valid API key to the .env file."
        }
        
    job_type_text = f", job type: {job_type}" if job_type else ""
    
    prompt = f"""
    You are an expert job search assistant.
    Find relevant job opportunities based on the following:
    
    RESUME:
    {resume_content}
    
    YEARS OF EXPERIENCE: {experience_years}
    LOCATION: {location}{job_type_text}
    
    Provide a list of EXACTLY 5-10 relevant job opportunities with the following information for each:
    - Job title
    - Company name
    - Location (including remote status if applicable)
    - Brief job description
    - Required qualifications
    - Required experience in years
    - Required skills as a comma-separated list
    - Estimated salary range
    - Application link (use real job board URLs like linkedin.com, indeed.com, glassdoor.com)
    
    Format your response as a JSON array of job objects with these field names:
    job_title, company_name, location, job_description, required_qualifications, experience_required, 
    skills_required, estimated_salary_range, application_link
    
    Make sure to escape all quotes in string values.
    IMPORTANT: You must include ALL of the fields listed above for EACH job.
    You must return at least 5 job listings.
    """
    
    try:
        response = await asyncio.to_thread(
            lambda: model.generate_content(prompt).text
        )
        logger.info(f"Raw job finder response received: {response[:100]}...")
        
        # Try to clean up the response before parsing
        response = response.strip()
        
        # Handle cases where the response has markdown code blocks
        if response.startswith("```json") and "```" in response:
            response = response.split("```json")[1].split("```")[0].strip()
        elif response.startswith("```") and "```" in response:
            response = response.split("```")[1].split("```")[0].strip()
        
        # Convert string response to JSON if possible
        try:
            # First attempt: direct JSON parsing
            json_response = json.loads(response)
            
            # Handle different response formats
            # If it's an array, return it directly
            if isinstance(json_response, list):
                return json_response
            # If it's an object with job-related keys, wrap it in an array
            elif isinstance(json_response, dict) and any(key in json_response for key in ['job_title', 'title', 'company', 'company_name']):
                return [json_response]
            # Otherwise, return it as is
            else:
                return json_response
                
        except json.JSONDecodeError as json_err:
            logger.warning(f"Could not parse job finder response as JSON: {str(json_err)}")
            
            # Try to extract JSON array from response
            import re
            
            # Look for a JSON array pattern
            array_match = re.search(r'\[\s*\{.*?\}\s*\]', response, re.DOTALL)
            if array_match:
                try:
                    json_array = array_match.group(0)
                    jobs = json.loads(json_array)
                    logger.info(f"Successfully extracted JSON array with {len(jobs)} jobs")
                    return jobs
                except json.JSONDecodeError as arr_err:
                    logger.warning(f"Failed to parse extracted array: {str(arr_err)}")
            
            # If we can't extract valid JSON, create a structured response from the text
            try:
                logger.info("Attempting to create structured job data from text")
                # Attempt to create a fallback response with structured data
                fallback_jobs = []
                
                # Parse job information from text using regex patterns
                job_blocks = re.findall(r'(?:Job Title|Title|job_title):\s*(.+?)(?:\n|$).*?(?:Company|Company Name|company_name):\s*(.+?)(?:\n|$).*?(?:Location|location):\s*(.+?)(?:\n|$)', 
                                       response, re.DOTALL | re.IGNORECASE)
                
                for i, (title, company, location) in enumerate(job_blocks[:5]):
                    # Create a more realistic application link
                    company_slug = ''.join(e for e in company.strip().lower().replace(' ', '-') if e.isalnum() or e == '-')
                    title_slug = ''.join(e for e in title.strip().lower().replace(' ', '-') if e.isalnum() or e == '-')
                    job_id = i + 100000 + (hash(title + company) % 900000)  # Use hash for more unique IDs
                    
                    fallback_jobs.append({
                        "job_title": title.strip(),
                        "company_name": company.strip(),
                        "location": location.strip(),
                        "job_description": f"See full description on job posting site",
                        "required_qualifications": "See full job posting for details",
                        "experience_required": "Not specified",
                        "skills_required": "Not specified",
                        "estimated_salary_range": "Not specified",
                        "application_link": f"https://www.linkedin.com/jobs/view/{company_slug}-{title_slug}-{job_id}"
                    })
                
                # If we found at least one job, return the fallback array
                if fallback_jobs:
                    logger.info(f"Created {len(fallback_jobs)} fallback job entries from text response")
                    return fallback_jobs
            except Exception as e:
                logger.error(f"Error creating fallback job entries: {str(e)}")
            
            # If all else fails, return the raw text
            return {"jobs": response}
    except Exception as e:
        logger.error(f"Error in job finding: {str(e)}")
        return {"error": str(e)}
