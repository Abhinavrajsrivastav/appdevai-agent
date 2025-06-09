# Environment Variables Management

## Overview

This project uses environment variables to manage sensitive information like API keys. These variables are stored in a `.env` file which is **excluded from version control** to prevent exposing sensitive information.

## Setup

1. Create a `.env` file in the `backend/` directory
2. Add your environment variables in the format `KEY=VALUE`

Example `.env` file content:
```
GEMINI_API_KEY=your-api-key-here
OTHER_SECRET_KEY=another-secret-value
```

## Handling in Code

Environment variables are loaded in the `config.py` file using the `python-dotenv` package.

## Security Practices

- The `.env` file is listed in `.gitignore` to prevent it from being committed to the repository
- Never commit API keys, passwords, or other sensitive information directly in the code
- A pre-commit hook is in place to check for potentially sensitive information before commits
- For deployment, use the environment variable features of your hosting provider rather than deploying the `.env` file

## What to Do If You Accidentally Commit Sensitive Information

If you accidentally commit sensitive information:

1. Immediately invalidate/rotate the exposed credentials
2. Use `git filter-branch` or the BFG Repo-Cleaner to remove the sensitive information from Git history
3. Force push to update the repository

## For New Team Members

When setting up the project for development:

1. Ask a team member for the required environment variables
2. Create your own `.env` file with these variables
3. Never share your `.env` file
