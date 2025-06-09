<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->

# Dev AI Agent - Copilot Instructions

This is a Model Context Protocol (MCP) server project using Python with FastAPI and Google's Gemini AI. The project implements an AI agent for job seekers with tools for resume ATS scoring, job searching, and cover letter generation.

## Project Structure

- Backend: Python FastAPI server with MCP protocol implementation
- Frontend: HTML/CSS/JS for user interface
- Tools: ATS scoring, job finder, cover letter generator

## Coding Standards

- Follow PEP 8 for Python code
- Use type hints in Python
- Use async/await for asynchronous operations
- Comment complex logic
- Use meaningful variable and function names

## API Structure

The backend implements:
1. MCP protocol endpoint at `/mcp`
2. Direct tool endpoints at `/tools/{tool_name}`
3. Tool execution endpoint at `/execute_tool`

## AI Tools Implementation

For the AI tools (ATS checker, job finder, cover letter generator):
- Keep prompts clear and structured
- Include error handling for API failures
- Use async functions for API calls
- Properly format responses for frontend display

## Frontend Implementation

- Keep UI clean and responsive
- Implement proper error handling
- Show loading states during API calls
- Format tool results for readability

## Dependencies

Key dependencies:
- FastAPI for the backend server
- Google Generative AI for LLM capabilities
- Python-multipart for file uploads
- Pydantic for data validation

You can find more info and examples at https://modelcontextprotocol.io/llms-full.txt
