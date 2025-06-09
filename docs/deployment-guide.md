# Deployment Guide

This document provides instructions for deploying the Dev AI Agent application to production.

## Local Deployment

1. Follow the setup instructions in the README.md file.
2. Update the `.env` file with your production API keys.
3. Run the application using the `start.bat` script or VS Code tasks.

## Production Deployment Options

### Option 1: Deploy on a VPS or Cloud VM

1. Provision a VM (e.g., on AWS EC2, Google Cloud Compute Engine, DigitalOcean)
2. Install Python 3.8+ and required dependencies
3. Clone the repository to the server
4. Set up environment variables including the Gemini API key
5. Install a production ASGI server like Gunicorn:
   ```
   pip install gunicorn uvicorn
   ```
6. Run the backend with Gunicorn:
   ```
   gunicorn -w 4 -k uvicorn.workers.UvicornWorker backend.main:app
   ```
7. Set up Nginx as a reverse proxy to the backend
8. Host the frontend files on Nginx or a static file hosting service

### Option 2: Deploy with Docker

1. Create a Dockerfile in the project root:
   ```
   FROM python:3.9-slim
   
   WORKDIR /app
   
   COPY backend/requirements.txt .
   RUN pip install -r requirements.txt
   
   COPY backend/ .
   COPY frontend/ ./static/
   
   CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
   ```

2. Build and run the Docker image:
   ```
   docker build -t dev-ai-agent .
   docker run -p 8000:8000 -e GEMINI_API_KEY=your-api-key dev-ai-agent
   ```

### Option 3: Deploy on a PaaS (Platform as a Service)

1. Deploy the backend to a service like Heroku, Google App Engine, or Azure App Service
2. Deploy the frontend to a static hosting service like Netlify, Vercel, or GitHub Pages
3. Update the API_BASE_URL in script.js to point to your deployed backend URL

## Security Considerations

For production deployment:

1. Replace the `*` in CORS settings with specific allowed origins
2. Set up proper authentication for API endpoints
3. Use HTTPS for all connections
4. Store API keys in environment variables or a secure secret management system
5. Implement rate limiting to prevent abuse

## Monitoring and Maintenance

1. Set up logging to monitor application performance and errors
2. Implement health check endpoints
3. Configure automated backups if using a database
4. Set up alerts for critical errors or performance issues
