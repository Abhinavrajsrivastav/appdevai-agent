# Extending the Dev AI Agent

This guide explains how to add new tools to the Dev AI Agent.

## Adding a New Tool

Follow these steps to add a new tool to the agent:

### 1. Define the Tool Schema

In `main.py`, add a new tool definition to the `available_tools` list:

```python
new_tool = Tool(
    name="your_tool_name",
    description="Description of what your tool does",
    parameters=[
        ToolParameter(name="param1", type="string", description="Description of parameter 1", required=True),
        ToolParameter(name="param2", type="number", description="Description of parameter 2", required=False),
        # Add more parameters as needed
    ]
)

available_tools = [ats_tool, job_search_tool, cover_letter_tool, new_tool]
```

### 2. Implement the Tool Function

Create a new async function to implement your tool's functionality:

```python
async def your_tool_name(param1: str, param2: float = None) -> Dict[str, Any]:
    """Description of what your tool does"""
    prompt = f"""
    You are an expert at [specific task].
    
    INPUT PARAMETER 1:
    {param1}
    
    INPUT PARAMETER 2:
    {param2}
    
    Provide [specific output format].
    """
    
    try:
        response = await asyncio.to_thread(
            lambda: model.generate_content(prompt).text
        )
        # Process response as needed
        return {"result": response}
    except Exception as e:
        logger.error(f"Error in your tool: {str(e)}")
        return {"error": str(e)}
```

### 3. Add a Direct API Endpoint

Create a new endpoint for direct tool access:

```python
@app.post("/tools/your_tool_name")
async def api_your_tool_name(
    param1: str = Form(...),
    param2: Optional[float] = Form(None)
):
    """API endpoint for your tool"""
    try:
        result = await your_tool_name(param1, param2)
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Error in your tool API: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
```

### 4. Update the Tool Execution Logic

Add your tool to the `execute_tool` function:

```python
@app.post("/execute_tool")
async def execute_tool(tool_call: ToolCall) -> Dict[str, Any]:
    """Execute a tool based on the tool call"""
    try:
        tool_name = tool_call.name
        params = {param.name: param.value for param in tool_call.parameters}
        
        # Add your tool to this conditional block
        if tool_name == "ats_score_checker":
            result = await ats_score_checker(...)
        elif tool_name == "job_finder":
            result = await job_finder(...)
        elif tool_name == "cover_letter_generator":
            result = await cover_letter_generator(...)
        elif tool_name == "your_tool_name":
            result = await your_tool_name(
                params.get("param1", ""),
                params.get("param2", None)
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
```

### 5. Update the Intent Detection Logic

Update the MCP endpoint to detect when to use your new tool:

```python
# In the mcp_endpoint function
user_message_lower = user_message.lower()
if "your tool keyword" in user_message_lower or "another keyword" in user_message_lower:
    tool_calls = [
        ToolCall(
            id=str(uuid.uuid4()),
            name="your_tool_name",
            parameters=[
                ToolCallParameter(name="param1", value="${param1}"),
                ToolCallParameter(name="param2", value="${param2}")
            ]
        )
    ]
```

### 6. Add Result Formatting

Add formatting for your tool's results in the MCP endpoint:

```python
# In the mcp_endpoint function where tool results are processed
elif tool_results.get("name") == "your_tool_name":
    formatted_response = "Here is the result from your tool:\n\n"
    # Format the response appropriately for your tool
    formatted_response += str(tool_results.get("result", {}))
```

### 7. Add a UI Component (Optional)

If you want a dedicated UI for your tool, add a new tab in `frontend/index.html` and implement the corresponding form handling in `frontend/script.js`.

## Example: Adding a Salary Negotiation Tool

Here's an example of adding a salary negotiation tool:

### Tool Definition

```python
salary_tool = Tool(
    name="salary_negotiator",
    description="Provides advice on salary negotiation based on job details and candidate experience",
    parameters=[
        ToolParameter(name="job_title", type="string", description="The job title", required=True),
        ToolParameter(name="experience_years", type="number", description="Years of experience", required=True),
        ToolParameter(name="location", type="string", description="Job location", required=True),
        ToolParameter(name="offered_salary", type="string", description="Salary offered", required=True)
    ]
)
```

### Implementation Function

```python
async def salary_negotiator(job_title: str, experience_years: float, location: str, offered_salary: str) -> Dict[str, Any]:
    """Provide salary negotiation advice"""
    prompt = f"""
    You are an expert salary negotiation coach.
    Provide advice for negotiating a salary for the following:
    
    JOB TITLE: {job_title}
    YEARS OF EXPERIENCE: {experience_years}
    LOCATION: {location}
    OFFERED SALARY: {offered_salary}
    
    Provide advice that includes:
    1. Whether the offered salary is below, at, or above market rate
    2. A suggested salary range to target
    3. Specific negotiation talking points
    4. Benefits beyond salary to consider negotiating
    
    Format your response as structured advice with sections.
    """
    
    try:
        response = await asyncio.to_thread(
            lambda: model.generate_content(prompt).text
        )
        return {"negotiation_advice": response}
    except Exception as e:
        logger.error(f"Error in salary negotiation: {str(e)}")
        return {"error": str(e)}
```

Follow similar patterns for adding the API endpoint, tool execution logic, and UI components as needed.
