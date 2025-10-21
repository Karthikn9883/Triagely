# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Backend Setup (FastAPI + SQLite)
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Initialize SQLite database (first time only)
python init_db.py

# Run development server
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

Triagely is a productivity tool with a local-first architecture:

- **Backend**: FastAPI (Python) with SQLite database
- **Web**: React SPA with local JWT authentication
- **Mobile**: React Native app using Expo
- **Database**: SQLite (`triagely.db` in backend root)
- **Authentication**: Local JWT tokens (no AWS dependencies)
- **External APIs**: Gmail API, Slack API
- **AI/LLM**: OpenAI API (configurable, with mock fallback)

### Core Backend Components

#### Authentication (`app/core/auth.py`)
- Local JWT token generation and validation using `python-jose`
- Password hashing with bcrypt via `passlib`
- 7-day token expiration
- Provides `current_user` FastAPI dependency for protected routes
- Requires: `JWT_SECRET_KEY` environment variable

#### Database Layer (`app/core/db.py`)
Three main SQLite tables:
- `users`: Local user accounts
  - Columns: id (UUID), email (unique), password_hash, name, created_at
- `oauth_tokens`: Stores OAuth tokens per user/provider
  - PK: (user_id, provider), e.g., provider='gmail:alice@x.com'
  - Columns: user_id, provider, token (JSON), connected_at
- `messages`: Caches email/Slack messages per user
  - PK: (user_id, message_id)
  - Optimized queries with priority filtering and efficient pagination
  - Messages sorted by date_iso for proper chronological display
  - Automatic cleanup of messages older than 60 days
  - Columns: subject, snippet, sender, date_iso, plain, html, priority, account, ai_summary, ai_checklist

#### Background Services (`app/background/scheduler.py`)
- Polls all Gmail accounts every 5 minutes (`POLL_SEC = 300`)
- Launched at FastAPI startup via `@app.on_event("startup")`
- Fetches up to 20 new threads per account per poll
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
- All AI results are stored in SQLite permanently (no regeneration needed)
- Token usage optimized: max_tokens=200, temperature=0.1
- Graceful degradation: Email sync continues even if AI processing fails
- **Provider**: OpenAI by default, with mock fallback for testing

### API Structure

Main router prefixes:
- `/auth` - User registration, login, profile (new local auth endpoints)
- `/gmail` - Gmail OAuth, message fetching, thread listing
- `/slack` - Slack OAuth and integration endpoints
- `/nlp` - AI services (summaries, checklists, priorities)
- `/health` - Health check endpoint
- `/protected` - Example authenticated endpoint

### Environment Variables

Required for backend (`.env` file):
- `JWT_SECRET_KEY` - Secret key for JWT signing (generate random 32+ chars)
- `GMAIL_CLIENT_ID` - Google OAuth client ID
- `GMAIL_CLIENT_SECRET` - Google OAuth client secret
- `GMAIL_REDIRECT_URL` - OAuth callback URL (default: http://localhost:8000/gmail/callback)
- `AI_PROVIDER` - LLM provider: "openai" or "mock" (default: mock)
- `OPENAI_API_KEY` - OpenAI API key (if using AI_PROVIDER=openai)
- `OPENAI_MODEL` - OpenAI model name (default: gpt-4o-mini)
- `FRONTEND_URL` - CORS origin (default: http://localhost:3000)
- `LOG_LEVEL` - Logging level (default: INFO)

Optional:
- `SLACK_CLIENT_ID` / `SLACK_CLIENT_SECRET` - For Slack integration
- `GMAIL_SCOPES` - Gmail API scopes (default: gmail.readonly)
- `SLACK_SCOPES` - Slack API scopes

### Code Patterns

- All routers use FastAPI's `APIRouter` with consistent prefixes and tags
- Authentication required for most endpoints via `Depends(current_user)`
- SQLite operations abstracted through `app/core/db.py` helpers
- Background tasks use asyncio for non-blocking execution
- LLM operations cached in SQLite to avoid redundant API calls
- OAuth tokens refreshed automatically when expired
- Context managers used for database connections (`with get_db()`)

### Performance Optimizations

#### Memory & Loading Performance
- Database queries optimized to fetch only needed items
- Priority filtering done at SQL level instead of post-processing
- Efficient pagination with proper date-based sorting
- 60-day email window ensures optimal performance vs completeness

#### API Rate Limiting & Efficiency
- Gmail API calls minimized with 100ms delays between requests
- Background polling every 5 minutes (reduced frequency)
- Maximum 20 threads per poll cycle
- Exponential backoff retry logic for rate limit handling
- OAuth callback triggers full 60-day sync for new accounts with immediate AI processing

#### AI Token Optimization
- **Automatic Processing**: All emails get AI summary, checklist, and priority during sync
- Ultra-short summaries: max 2 bullets, 60 chars each
- Limited checklists: max 2 tasks, 50 chars each
- Reduced max_tokens from 1024 to 200 per LLM call
- Lower temperature (0.1) for more consistent, concise responses
- All AI results stored permanently in SQLite (no regeneration needed)
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

- SQLite database file (`triagely.db`) is created in backend root directory
- Run `python init_db.py` to initialize/reset the database
- No AWS credentials needed - fully local development
- Gmail OAuth requires Google Cloud Console setup for client ID/secret
- Use `AI_PROVIDER=mock` for testing without OpenAI API key
- Frontend stores JWT tokens in localStorage
- All API requests include `Authorization: Bearer <token>` header
- Tokens expire after 7 days - users must re-login

### Migration from AWS

This codebase has been migrated from AWS to local-first:
- ✅ Removed AWS Cognito → Local JWT authentication
- ✅ Removed AWS DynamoDB → SQLite database
- ✅ Removed AWS Secrets Manager → Environment variables
- ✅ Removed AWS Bedrock → OpenAI API (or mock)
- ✅ Removed all boto3 dependencies
- ✅ Added passlib for password hashing
- ✅ Added python-jose for JWT handling

### Testing

For local testing without external dependencies:
1. Set `AI_PROVIDER=mock` in `.env` to skip OpenAI API calls
2. Database is fully local (SQLite)
3. Authentication works offline (JWT signing is local)
4. Only Gmail/Slack OAuth require internet connectivity

### Database Schema

```sql
-- Users table
CREATE TABLE users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    name TEXT,
    created_at INTEGER NOT NULL
);

-- OAuth tokens table
CREATE TABLE oauth_tokens (
    user_id TEXT NOT NULL,
    provider TEXT NOT NULL,
    token TEXT NOT NULL,
    connected_at INTEGER NOT NULL,
    PRIMARY KEY (user_id, provider)
);

-- Messages table
CREATE TABLE messages (
    user_id TEXT NOT NULL,
    message_id TEXT NOT NULL,
    subject TEXT,
    snippet TEXT,
    sender TEXT,
    sender_email TEXT,
    date_iso TEXT,
    plain TEXT,
    html TEXT,
    priority TEXT DEFAULT 'Normal',
    account TEXT,
    ai_summary TEXT,  -- JSON array
    ai_checklist TEXT,  -- JSON array
    created_at INTEGER NOT NULL,
    PRIMARY KEY (user_id, message_id)
);
```
