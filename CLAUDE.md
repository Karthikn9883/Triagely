# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Backend (FastAPI)
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload  # Runs on http://localhost:8000
```

### Web Frontend (React)
```bash
cd web
npm install
npm start      # Runs on http://localhost:3000
npm run build  # Production build
npm test       # Run tests
```

### Mobile App (React Native/Expo)
```bash
cd mobile
npm install
npm start      # Opens Expo developer tools
```

## Architecture Overview

Triagely is a productivity tool with a multi-tier architecture:

- **Backend**: FastAPI (Python) with AWS integrations
- **Web**: React SPA with AWS Amplify authentication
- **Mobile**: React Native app using Expo
- **Database**: AWS DynamoDB (2 main tables)
- **Authentication**: AWS Cognito User Pools with JWT validation
- **External APIs**: Gmail API, Slack API

### Core Backend Components

#### Authentication (`app/core/auth.py`)
- JWT validation against AWS Cognito User Pool
- Caches JWKS keys for 6 hours to avoid frequent API calls
- Provides `current_user` FastAPI dependency for protected routes
- Requires: `AWS_REGION`, `COG_USER_POOL_ID`, `COG_APP_CLIENT_ID`

#### Database Layer (`app/core/db.py`)
Two main DynamoDB tables:
- `triagely-oauth`: Stores OAuth tokens per user/provider
  - PK: UserID (Cognito sub), SK: provider_key (e.g., 'gmail:alice@x.com')
- `triagely-messages`: Caches email/Slack messages per user
  - PK: UserID, SK: MessageID
  - Optimized queries with priority filtering and efficient pagination
  - Messages sorted by dateISO for proper chronological display
  - Automatic cleanup of messages older than 60 days

#### Background Services (`app/background/scheduler.py`)
- Polls all Gmail accounts every 5 minutes (`POLL_SEC = 300`) - optimized to reduce API usage
- Launched at FastAPI startup via `@app.on_event("startup")`
- Fetches up to 20 new threads per account per poll (reduced from 30 for efficiency)
- Includes daily cleanup of messages older than 60 days

#### Integrations
- **Gmail** (`app/integrations/gmail/`): OAuth flow, message fetching, thread processing
- **Slack** (`app/integrations/slack/`): OAuth integration and message handling

#### NLP Services (`app/nlp/`)
AI-powered features using LLM providers (optimized for token efficiency):
- **Summary** (`llm/summary.py`): Ultra-concise email summarization (max 2 bullets, 60 chars each)
- **Checklist** (`llm/checklist.py`): Action item extraction (max 2 tasks, 50 chars each)
- **Priority** (`llm/priority.py`): Message priority classification (High/Normal)
- **Automatic AI Processing**: All emails get AI summary, checklist, and priority during initial sync
- All AI results are stored in DynamoDB permanently (no regeneration needed)
- Token usage optimized: max_tokens=200, temperature=0.1
- Graceful degradation: Email sync continues even if AI processing fails

### API Structure

Main router prefixes:
- `/gmail` - Gmail OAuth, message fetching, thread listing
- `/slack` - Slack OAuth and integration endpoints  
- `/nlp` - AI services (summaries, checklists, priorities)
- `/health` - Health check endpoint
- `/protected` - Example authenticated endpoint

### Environment Variables

Required for backend:
- `AWS_REGION` - AWS region for DynamoDB/Cognito
- `COG_USER_POOL_ID` - Cognito User Pool ID
- `COG_APP_CLIENT_ID` - Cognito App Client ID
- `FRONTEND_URL` - CORS origin (default: http://localhost:3000)
- `LOG_LEVEL` - Logging level (default: INFO)

### Code Patterns

- All routers use FastAPI's `APIRouter` with consistent prefixes and tags
- Authentication required for most endpoints via `Depends(current_user)`
- DynamoDB operations abstracted through `app/core/db.py` helpers
- Background tasks use asyncio for non-blocking execution
- LLM operations cached in DynamoDB to avoid redundant API calls
- OAuth tokens refreshed automatically when expired

### Performance Optimizations

#### Memory & Loading Performance
- Database queries optimized to fetch only needed items (max 250 items at once)
- Priority filtering done at DynamoDB level instead of post-processing
- Efficient pagination with proper date-based sorting
- Reduced memory usage by avoiding loading all messages at once
- 60-day email window ensures optimal performance vs completeness

#### API Rate Limiting & Efficiency
- Gmail API calls minimized with 100ms delays between requests (increased due to AI processing)
- Background polling reduced to every 5 minutes (was 2 minutes)
- Maximum 20 threads per poll cycle (reduced from 30)
- Exponential backoff retry logic for rate limit handling
- OAuth callback triggers full 60-day sync for new accounts with immediate AI processing

#### AI Token Optimization
- **Automatic Processing**: All emails get AI summary, checklist, and priority during sync (no manual generation)
- Ultra-short summaries: max 2 bullets, 60 chars each (was 5 bullets, 80 chars)
- Limited checklists: max 2 tasks, 50 chars each (was unlimited)
- Reduced max_tokens from 1024 to 200 per LLM call
- Lower temperature (0.1) for more consistent, concise responses
- All AI results stored permanently in DynamoDB (no regeneration needed)
- Priority classification done once during initial email sync
- Graceful error handling: email sync continues even if AI processing fails

#### Full Sync Features
- OAuth callback performs complete 60-day email sync for new accounts with automatic AI processing
- Manual refresh button triggers full 60-day sync with pagination and AI processing
- Email sync continues even if AI processing fails (graceful degradation)
- Background cleanup removes messages older than 60 days daily
- All emails automatically get AI summary, checklist, and priority during sync
- No manual AI generation required - everything is processed immediately

### Development Notes

- The app uses AWS services heavily - ensure proper AWS credentials are configured
- Gmail API requires OAuth 2.0 setup with Google Cloud Console
- DynamoDB tables must exist before running the backend
- Background Gmail polling starts automatically with the FastAPI server
- All integrations store tokens per user to support multi-user scenarios
- AI features are optimized for minimal token usage while maintaining functionality