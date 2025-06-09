import json
import uuid
import base64
from typing import Dict, List, Optional, Any, Union
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai
from fastapi.responses import JSONResponse
import asyncio
import logging

# Import configuration
from config import GEMINI_API_KEY, MAX_TOKENS, TEMPERATURE
# Import utilities
from utils import extract_text_from_pdf

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the app
app = FastAPI(title="Dev AI Agent")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Gemini API configuration
genai.configure(api_key=GEMINI_API_KEY)

# Define the model to use with configuration
model = genai.GenerativeModel(
    'gemini-1.5-pro',
    generation_config={
        'max_output_tokens': MAX_TOKENS,
        'temperature': TEMPERATURE
    }
)

# MCP Protocol - Tool definitions
class ToolParameter(BaseModel):
    name: str
    type: str
    description: str
    required: bool = False

class Tool(BaseModel):
    name: str
    description: str
    parameters: List[ToolParameter]

class ToolCallParameter(BaseModel):
    name: str
    value: Any

class ToolCall(BaseModel):
    id: str
    name: str
    parameters: List[ToolCallParameter]

class MCPRequest(BaseModel):
    text: str
    context: Optional[Dict[str, Any]] = None
    tool_choice: Optional[str] = None

class MCPResponse(BaseModel):
    id: str
    text: str
    tool_calls: Optional[List[ToolCall]] = None

# Define our tools
ats_tool = Tool(
    name="ats_score_checker",
    description="Analyzes a resume against a job description to provide an ATS compatibility score",
    parameters=[
        ToolParameter(name="resume_content", type="string", description="The content of the resume", required=True),
        ToolParameter(name="job_description", type="string", description="The job description text", required=True)
    ]
)

job_search_tool = Tool(
    name="job_finder",
    description="Finds relevant job opportunities based on user's experience, skills, and preferences",
    parameters=[
        ToolParameter(name="resume_content", type="string", description="The content of the resume", required=True),
        ToolParameter(name="experience_years", type="number", description="Years of experience", required=True),
        ToolParameter(name="location", type="string", description="Preferred job location", required=True),
        ToolParameter(name="job_type", type="string", description="Type of job (full-time, part-time, remote, etc.)", required=False)
    ]
)

cover_letter_tool = Tool(
    name="cover_letter_generator",
    description="Generates a professional cover letter based on resume and job description",
    parameters=[
        ToolParameter(name="resume_content", type="string", description="The content of the resume", required=True),
        ToolParameter(name="job_description", type="string", description="The job description text", required=True)
    ]
)

available_tools = [ats_tool, job_search_tool, cover_letter_tool]

# Tool implementation functions
async def ats_score_checker(resume_content: str, job_description: str) -> Dict[str, Any]:
    """Analyze resume against job description for ATS score"""
    if not GEMINI_API_KEY or GEMINI_API_KEY == "your-api-key-here":
        logger.error("Invalid or missing Gemini API key in ats_score_checker")
        return {
            "error": "The Gemini API key is not configured. Please add a valid API key to the .env file.",
            "score": 0
        }
        
    prompt = f"""
    You are an ATS (Applicant Tracking System) expert. 
    Analyze the following resume against the job description provided.
    
    RESUME:
    {resume_content}
    
    JOB DESCRIPTION:
    {job_description}
    
    Provide a detailed analysis with:
    1. Overall ATS compatibility score (0-100)
    2. Key matching keywords found
    3. Missing important keywords
    4. Formatting issues that might affect ATS scanning
    5. Specific recommendations to improve the score
    
    Format your response as JSON with these exact fields:
    {{
        "score": 75,
        "matching_keywords": ["keyword1", "keyword2"],
        "missing_keywords": ["keyword3", "keyword4"],
        "formatting_issues": "Description of formatting issues",
        "recommendations": "Specific recommendations to improve"
    }}
    
    Make sure to return valid JSON.
    """
    
    try:
        response = await asyncio.to_thread(
            lambda: model.generate_content(prompt).text
        )
        # Convert string response to JSON if possible
        try:
            result = json.loads(response)
            # Ensure we have all expected fields with defaults if missing
            return {
                "score": result.get("score", 50),
                "matching_keywords": result.get("matching_keywords", []),
                "missing_keywords": result.get("missing_keywords", []),
                "formatting_issues": result.get("formatting_issues", "No specific issues detected"),
                "recommendations": result.get("recommendations", "No specific recommendations")
            }
        except json.JSONDecodeError:
            # If response is not valid JSON, extract a score if possible and return as text
            import re
            score_match = re.search(r"score.*?(\d+)", response, re.IGNORECASE)
            score = int(score_match.group(1)) if score_match else 50
            return {
                "score": score,
                "analysis": response
            }
    except Exception as e:
        logger.error(f"Error in ATS scoring: {str(e)}")
        return {"error": str(e), "score": 0}

async def job_finder(resume_content: str, experience_years: float, location: str, job_type: str = None) -> Dict[str, Any]:
    """Find relevant job opportunities"""
    if not GEMINI_API_KEY or GEMINI_API_KEY == "your-api-key-here":
        logger.error("Invalid or missing Gemini API key in job_finder")
        return {
            "error": "The Gemini API key is not configured. Please add a valid API key to the .env file."
        }
        
    job_type_text = f", job type: {job_type}" if job_type else ""
    
    # Using format() method instead of f-string to avoid issues with nested curly braces
    prompt = """
    You are an expert job search assistant.
    Find relevant job opportunities based on the following:
    
    RESUME:
    {resume_content}
    
    YEARS OF EXPERIENCE: {experience_years}
    LOCATION: {location}{job_type_text}
    
    Provide a list of EXACTLY 5-10 relevant job opportunities with:
    1. Job title (job_title)
    2. Company name (company_name)
    3. Location including remote status if applicable (location)
    4. Brief job description (job_description)
    5. Required qualifications (required_qualifications)
    6. Required experience in years (experience_required)
    7. Required skills as a comma-separated list (skills_required)
    8. Estimated salary range (estimated_salary_range)
    9. Application link (application_link) - IMPORTANT: provide REAL job board URLs from LinkedIn, Indeed, Glassdoor, etc.
       For example: https://www.linkedin.com/jobs/view/123456789 or https://www.indeed.com/viewjob?jk=abcdef123456
       Do NOT use placeholder, example.com, or localhost URLs.
       This is critical - the user needs real links to apply to jobs.
    
    Format your response as a JSON array of job objects with EXACTLY these field names.
    Make sure to escape all quotes in string values.
    IMPORTANT: You must include ALL of the fields listed above for EACH job.
    You must return at least 5 job listings.
    
    Example format (DO NOT COPY THIS EXAMPLE VERBATIM):
    [
      {{
        "job_title": "Software Engineer",
        "company_name": "Tech Company",
        "location": "San Francisco, CA (Remote)",
        "job_description": "Description of the role",
        "required_qualifications": "Bachelor's degree in CS",
        "experience_required": "3-5",
        "skills_required": "JavaScript, React",
        "estimated_salary_range": "$100,000 - $130,000",
        "application_link": "https://www.linkedin.com/jobs/view/3579246352"
      }}
    ]
    """.format(
        resume_content=resume_content,
        experience_years=experience_years,
        location=location,
        job_type_text=job_type_text
    )
    
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

async def cover_letter_generator(resume_content: str, job_description: str) -> Dict[str, Any]:
    """Generate a professional cover letter"""
    if not GEMINI_API_KEY or GEMINI_API_KEY == "your-api-key-here":
        logger.error("Invalid or missing Gemini API key in cover_letter_generator")
        return {
            "error": "The Gemini API key is not configured. Please add a valid API key to the .env file."
        }
        
    prompt = f"""
    You are an expert cover letter writer.
    Create a professional, personalized cover letter based on the following:
    
    RESUME:
    {resume_content}
    
    JOB DESCRIPTION:
    {job_description}
    
    Create a compelling cover letter that:
    1. Addresses the specific requirements in the job description
    2. Highlights relevant experience and skills from the resume
    3. Shows enthusiasm for the position and company
    4. Has a professional tone and format
    5. Is concise (around 300-400 words)
    
    Return just the text of the cover letter, properly formatted with paragraphs.
    """
    
    try:
        response = await asyncio.to_thread(
            lambda: model.generate_content(prompt).text
        )
        return {"cover_letter": response}
    except Exception as e:
        logger.error(f"Error in cover letter generation: {str(e)}")
        return {"error": str(e)}

# MCP Protocol endpoints
@app.post("/mcp")
async def mcp_endpoint(request: MCPRequest) -> MCPResponse:
    """Main MCP endpoint for handling agent requests"""
    try:
        # Check if API key is valid
        if not GEMINI_API_KEY or GEMINI_API_KEY == "your-api-key-here":
            logger.error("Invalid or missing Gemini API key")
            return MCPResponse(
                id=str(uuid.uuid4()),
                text="Error: The Gemini API key is not configured. Please add a valid API key to the .env file.",
                tool_calls=None
            )
            
        # Generate response to user query with tool definitions
        system_prompt = """You are an AI assistant for job seekers. You have access to these tools:
        1. ats_score_checker - Analyzes a resume against a job description for ATS compatibility
        2. job_finder - Finds relevant job opportunities based on user criteria
        3. cover_letter_generator - Creates a professional cover letter based on resume and job description
        
        Help the user with job applications by asking for necessary information and using the appropriate tool.
        """
        
        user_message = request.text
        context = request.context or {}
        
        # Check if this is a tool response call
        if 'tool_results' in context:
            logger.info(f"Received tool results: {context['tool_results']}")
            tool_results = context['tool_results']
            
            # Format a response based on the tool results
            formatted_response = ""
            if tool_results.get("name") == "ats_score_checker":
                result = tool_results.get("result", {})
                score = result.get("score", "N/A")
                formatted_response = f"Here is your ATS analysis:\n\n"
                
                if "analysis" in result:
                    formatted_response += result["analysis"]
                else:
                    # Detailed formatting for structured JSON response
                    formatted_response += f"Score: {score}/100\n\n"
                    if "matching_keywords" in result:
                        formatted_response += f"Matching Keywords: {', '.join(result['matching_keywords'])}\n\n"
                    if "missing_keywords" in result:
                        formatted_response += f"Missing Keywords: {', '.join(result['missing_keywords'])}\n\n"
                    if "formatting_issues" in result:
                        formatted_response += f"Formatting Issues: {result['formatting_issues']}\n\n"
                    if "recommendations" in result:
                        formatted_response += f"Recommendations: {result['recommendations']}\n\n"
            
            elif tool_results.get("name") == "job_finder":
                formatted_response = "Here are the job opportunities I found for you:\n\n"
                jobs = tool_results.get("result", [])
                
                if isinstance(jobs, list):
                    for i, job in enumerate(jobs, 1):
                        formatted_response += f"**{i}. {job.get('title', 'Job Title')} - {job.get('company', 'Company')}**\n"
                        formatted_response += f"Location: {job.get('location', 'N/A')}\n"
                        formatted_response += f"Description: {job.get('description', 'N/A')}\n"
                        formatted_response += f"Required Qualifications: {job.get('qualifications', 'N/A')}\n"
                        formatted_response += f"Salary Range: {job.get('salary_range', 'N/A')}\n"
                        formatted_response += f"Apply at: {job.get('application_link', 'N/A')}\n\n"
                else:
                    formatted_response += str(jobs)
            
            elif tool_results.get("name") == "cover_letter_generator":
                formatted_response = "Here is your generated cover letter:\n\n"
                formatted_response += tool_results.get("result", {}).get("cover_letter", "Could not generate cover letter.")
            
            return MCPResponse(
                id=str(uuid.uuid4()),
                text=formatted_response,
                tool_calls=None
            )
        
        # No tool results, this is an initial user query
        prompt = f"{system_prompt}\n\nUser: {user_message}"
        try:
            response = await asyncio.to_thread(
                lambda: model.generate_content(prompt).text
            )
        except Exception as e:
            logger.error(f"Error generating content with Gemini API: {str(e)}")
            return MCPResponse(
                id=str(uuid.uuid4()),
                text=f"Sorry, there was an error communicating with the AI service: {str(e)}. Please check your API key configuration.",
                tool_calls=None
            )
        
        # Check if we need to call a tool based on the user's request
        tool_calls = None
        
        # Simple intent detection
        user_message_lower = user_message.lower()
        if "ats" in user_message_lower or "score" in user_message_lower or "resume review" in user_message_lower:
            # Need resume and job description
            tool_calls = [
                ToolCall(
                    id=str(uuid.uuid4()),
                    name="ats_score_checker",
                    parameters=[
                        ToolCallParameter(name="resume_content", value="${resume_content}"),
                        ToolCallParameter(name="job_description", value="${job_description}")
                    ]
                )
            ]
        elif "job" in user_message_lower or "find" in user_message_lower or "search" in user_message_lower:
            # Need resume, experience, location
            tool_calls = [
                ToolCall(
                    id=str(uuid.uuid4()),
                    name="job_finder",
                    parameters=[
                        ToolCallParameter(name="resume_content", value="${resume_content}"),
                        ToolCallParameter(name="experience_years", value="${experience_years}"),
                        ToolCallParameter(name="location", value="${location}"),
                        ToolCallParameter(name="job_type", value="${job_type}")
                    ]
                )
            ]
        elif "cover letter" in user_message_lower or "letter" in user_message_lower:
            # Need resume and job description
            tool_calls = [
                ToolCall(
                    id=str(uuid.uuid4()),
                    name="cover_letter_generator",
                    parameters=[
                        ToolCallParameter(name="resume_content", value="${resume_content}"),
                        ToolCallParameter(name="job_description", value="${job_description}")
                    ]
                )
            ]
            
        return MCPResponse(
            id=str(uuid.uuid4()),
            text=response,
            tool_calls=tool_calls
        )
    
    except Exception as e:
        logger.error(f"Error in MCP endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# API endpoints for direct tool access
@app.post("/tools/ats_score_checker")
async def api_ats_score_checker(
    resume: UploadFile = File(...),
    job_description: str = Form(...)
):
    """API endpoint for ATS score checking"""
    try:
        # Read the file content
        resume_content = await resume.read()
        
        # Check if it's a PDF
        if resume.filename.lower().endswith('.pdf'):
            # Extract text from PDF
            resume_text = extract_text_from_pdf(resume_content)
            if not resume_text:
                resume_text = "[Could not extract text from the PDF. Please ensure it's a valid PDF with text content.]"
        else:
            # Try to decode as text
            try:
                resume_text = resume_content.decode("utf-8")
            except UnicodeDecodeError:
                # Not a text file
                resume_text = f"[Could not decode file {resume.filename}. Please upload a PDF or text file.]"
        
        # Log the first 200 characters of the extracted text for debugging
        logger.info(f"Extracted resume text (first 200 chars): {resume_text[:200]}...")
        
        # Call the ATS scorer with the extracted text
        result = await ats_score_checker(resume_text, job_description)
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Error in ATS score API: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tools/job_finder")
async def api_job_finder(
    resume: UploadFile = File(...),
    experience_years: float = Form(...),
    location: str = Form(...),
    job_type: Optional[str] = Form(None)
):
    """API endpoint for job finding"""
    try:
        # Read the file content
        resume_content = await resume.read()
        
        # Extract text based on file type
        if resume.filename.lower().endswith('.pdf'):
            resume_text = extract_text_from_pdf(resume_content)
            if not resume_text:
                resume_text = "[Could not extract text from the PDF]"
        else:
            try:
                resume_text = resume_content.decode("utf-8")
            except UnicodeDecodeError:
                resume_text = f"[Could not decode file {resume.filename}]"
        
        result = await job_finder(resume_text, experience_years, location, job_type)
        
        # Log response type and partial content for debugging
        if isinstance(result, list):
            logger.info(f"Job finder returned a list with {len(result)} jobs")
        elif isinstance(result, dict):
            logger.info(f"Job finder returned a dict with keys: {result.keys()}")
        else:
            logger.info(f"Job finder returned a {type(result)}: {str(result)[:100]}...")
        
        # Ensure consistent response format
        if isinstance(result, list):
            # If the list is already formatted properly, return it directly
            # Make sure it's serializable
            for job in result:
                if isinstance(job, dict):
                    # Ensure all values are strings or basic types
                    for key, value in job.items():
                        if not isinstance(value, (str, int, float, bool, type(None))):
                            job[key] = str(value)
            return result  # FastAPI will automatically convert to JSON
        elif isinstance(result, dict):
            if "error" in result:
                # Error response
                return result
            elif "jobs" in result:
                # Extract jobs array if it exists
                jobs = result["jobs"]
                if isinstance(jobs, list):
                    return jobs
                elif isinstance(jobs, str):
                    # Try to parse it as JSON
                    try:
                        parsed_jobs = json.loads(jobs)
                        return parsed_jobs
                    except json.JSONDecodeError:
                        # If it can't be parsed, return the string as is
                        return [{"job_description": jobs}]
                else:
                    # Unknown format, wrap in an object
                    return [{"job_description": str(jobs)}]
            else:
                # Other dict structure, return as is
                return result
        else:
            # Unknown format, convert to string and wrap in an object
            return [{"job_description": str(result)}]
            
    except Exception as e:
        logger.error(f"Error in job finder API: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tools/cover_letter_generator")
async def api_cover_letter_generator(
    resume: UploadFile = File(...),
    job_description: str = Form(...)
):
    """API endpoint for cover letter generation"""
    try:
        # Read the file content
        resume_content = await resume.read()
        
        # Extract text based on file type
        if resume.filename.lower().endswith('.pdf'):
            resume_text = extract_text_from_pdf(resume_content)
            if not resume_text:
                resume_text = "[Could not extract text from the PDF]"
        else:
            try:
                resume_text = resume_content.decode("utf-8")
            except UnicodeDecodeError:
                resume_text = f"[Could not decode file {resume.filename}]"
        
        result = await cover_letter_generator(resume_text, job_description)
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Error in cover letter API: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Tool execution endpoint - used by MCP protocol
@app.post("/execute_tool")
async def execute_tool(tool_call: ToolCall) -> Dict[str, Any]:
    """Execute a tool based on the tool call"""
    try:
        tool_name = tool_call.name
        params = {param.name: param.value for param in tool_call.parameters}
        
        if tool_name == "ats_score_checker":
            result = await ats_score_checker(
                params.get("resume_content", ""),
                params.get("job_description", "")
            )
        elif tool_name == "job_finder":
            result = await job_finder(
                params.get("resume_content", ""),
                params.get("experience_years", 0),
                params.get("location", ""),
                params.get("job_type", None)
            )
        elif tool_name == "cover_letter_generator":
            result = await cover_letter_generator(
                params.get("resume_content", ""),
                params.get("job_description", "")
            )
        else:
            raise HTTPException(status_code=400, detail=f"Unknown tool: {tool_name}")
        
        return {
            "id": tool_call.id,
            "name": tool_name,
            "result": result
        }
    except Exception as e:
        logger.error(f"Error executing tool: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Root endpoint with tools information
@app.get("/")
async def get_tools_info():
    """Return information about available tools"""
    return {
        "name": "Dev AI Agent",
        "description": "AI agent with ATS scoring, job search, and cover letter generation tools",
        "tools": [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": [
                    {
                        "name": param.name,
                        "type": param.type,
                        "description": param.description,
                        "required": param.required
                    }
                    for param in tool.parameters
                ]
            }
            for tool in available_tools
        ]
    }

# Run the server with: uvicorn main:app --reload
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
