# Triagely Local Setup Guide

This guide will help you set up Triagely on your local machine with SQLite and local JWT authentication.

## Prerequisites

- **Node.js** (v14 or higher) and npm
- **Python** 3.8+ and pip
- **Git**

## Quick Start

### 1. Clone and Setup

```bash
git clone <repository-url>
cd Triagely
```

### 2. Backend Setup

#### Initialize Database

```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Initialize SQLite database
python init_db.py
```

#### Configure Environment

Edit `backend/.env` and set the following required variables:

```bash
# JWT Secret (generate a strong random key)
JWT_SECRET_KEY=your-secret-key-change-this-in-production-make-it-long-and-random

# Gmail OAuth (from Google Cloud Console)
GMAIL_CLIENT_ID=your-gmail-client-id
GMAIL_CLIENT_SECRET=your-gmail-client-secret

# AI Provider (use "mock" for testing without API key)
AI_PROVIDER=openai  # or "mock"
OPENAI_API_KEY=your-openai-api-key
```

**To get Gmail OAuth credentials:**
1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Create a new OAuth 2.0 Client ID
3. Add `http://localhost:8000/gmail/callback` as an authorized redirect URI
4. Copy the Client ID and Client Secret

#### Run Backend

```bash
uvicorn app.main:app --reload
```

Backend will be available at http://localhost:8000

### 3. Web Frontend Setup

```bash
cd web
npm install
npm start
```

Frontend will be available at http://localhost:3000

### 4. Create Your First User

1. Open http://localhost:3000
2. Click "Sign Up"
3. Enter email, password, and name
4. You'll be automatically logged in

### 5. Connect Gmail Account

1. After logging in, connect your Gmail account
2. Click "Connect Gmail" (if available in UI)
3. Authorize the app
4. Emails will start syncing automatically

## Architecture Changes

### Removed AWS Dependencies

- ✅ **AWS Cognito** → Local JWT authentication with SQLite user storage
- ✅ **AWS DynamoDB** → SQLite database (`triagely.db`)
- ✅ **AWS Secrets Manager** → Environment variables in `.env` file
- ✅ **AWS Bedrock** → OpenAI API (or mock for testing)

### Database Schema

SQLite database with 3 tables:

1. **users** - Local user accounts (email, password_hash, name)
2. **oauth_tokens** - Gmail/Slack OAuth tokens per user
3. **messages** - Cached emails with AI-generated summaries and priorities

### Authentication Flow

1. User registers/logs in via `/auth/register` or `/auth/login`
2. Backend generates JWT token (7-day expiry)
3. Frontend stores token in localStorage
4. All API requests include `Authorization: Bearer <token>` header
5. Backend validates JWT on protected endpoints

## Environment Variables Reference

### Backend (.env)

```bash
# JWT Authentication
JWT_SECRET_KEY=your-secret-key-here

# Server URLs
GMAIL_REDIRECT_URL=http://localhost:8000/gmail/callback
SLACK_REDIRECT_URL=http://localhost:8000/slack/callback
FRONTEND_URL=http://localhost:3000

# Gmail OAuth
GMAIL_CLIENT_ID=your-gmail-client-id
GMAIL_CLIENT_SECRET=your-gmail-client-secret
GMAIL_SCOPES=https://www.googleapis.com/auth/gmail.readonly

# Slack OAuth (optional)
SLACK_CLIENT_ID=your-slack-client-id
SLACK_CLIENT_SECRET=your-slack-client-secret
SLACK_SCOPES=channels:read,channels:history,im:history

# AI Provider
AI_PROVIDER=openai  # or "mock"
OPENAI_API_KEY=your-key
OPENAI_MODEL=gpt-4o-mini

# Logging
LOG_LEVEL=INFO
```

### Frontend (.env)

```bash
REACT_APP_API_BASE_URL=http://localhost:8000
```

## Troubleshooting

### Database Issues

If you encounter database errors, reinitialize:

```bash
cd backend
rm triagely.db  # Delete old database
python init_db.py  # Recreate
```

### Gmail OAuth Issues

- Ensure redirect URI exactly matches: `http://localhost:8000/gmail/callback`
- Check that OAuth consent screen is configured
- Verify API is enabled in Google Cloud Console

### AI/LLM Issues

- Use `AI_PROVIDER=mock` for testing without API keys
- For OpenAI: Ensure `OPENAI_API_KEY` is valid
- Check rate limits if getting 429 errors

## Development

### Backend

```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --log-level debug
```

### Frontend

```bash
cd web
npm start
```

### API Documentation

Once backend is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Production Deployment

For production:

1. Generate a strong JWT secret key (32+ characters)
2. Use HTTPS for all endpoints
3. Configure CORS properly for your domain
4. Use a production-grade database (PostgreSQL recommended)
5. Set up proper backup strategy for SQLite database
6. Use environment-specific OAuth redirect URIs
7. Enable rate limiting on authentication endpoints

## Migration Notes

This version has been migrated from AWS to local-first architecture:

- All AWS services have been removed
- Data is now stored locally in SQLite
- Authentication is handled locally with JWT
- No AWS credentials required
- Suitable for local development and small deployments

For large-scale deployments, consider:
- PostgreSQL instead of SQLite
- Redis for session management
- Load balancers for scaling
- Kubernetes for orchestration
