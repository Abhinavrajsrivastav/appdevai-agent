# Troubleshooting Guide
This guide helps you resolve common issues with the Dev AI Agent.

## Common Issues

### 500 Internal Server Error When Sending Messages

**Symptoms:**
- You get a "500 Internal Server Error" when sending a message in the chat interface
- The AI doesn't respond to your messages

**Causes:**
1. Invalid or missing Gemini API key
2. Network connectivity issues
3. Server configuration problems

**Solutions:**

#### 1. Check your Gemini API Key

The most common cause of 500 errors is an invalid or missing Gemini API key. To fix this:

1. Go to https://makersuite.google.com/app/apikey to get a valid API key
2. Open the `.env` file in the `backend` directory
3. Replace the existing API key with your new one:
   ```
   GEMINI_API_KEY=your-new-api-key-here
   ```
4. Restart the backend server

#### 2. Check Server Logs

If you're still experiencing issues, check the server logs for more detailed error messages:

1. Run the backend with debug logging:
   ```
   cd backend
   venv\Scripts\activate
   uvicorn main:app --reload --log-level debug
   ```
2. Try sending a message again and check the terminal for error messages

#### 3. Verify Network Connectivity

Ensure that:
- The backend server is running on port 8000
- Your browser can access localhost:8000
- There are no firewalls blocking the connection

### PDF Resume Not Being Processed Correctly

**Symptoms:**
- The AI can't read your resume
- You get errors when uploading PDF files

**Solutions:**

1. Make sure your PDF is text-based (not scanned)
2. Try converting the PDF to text first using an online converter
3. Ensure PyPDF2 is installed:
   ```
   pip install PyPDF2
   ```

### Frontend Not Connecting to Backend

**Symptoms:**
- The frontend loads but can't communicate with the backend
- You see network errors in the browser console

**Solutions:**

1. Make sure the backend server is running
2. Check that the API_BASE_URL in `frontend/script.js` is correct
3. Ensure CORS is properly configured in the backend

## Getting Help

If you're still experiencing issues:

1. Check the browser console for errors (F12 > Console)
2. Look at the backend logs for error messages
3. Make sure all dependencies are installed correctly
