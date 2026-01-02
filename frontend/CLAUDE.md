# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Next.js 16 frontend application for a Digital Twin portfolio website that interfaces with a FastAPI backend. The application features an AI-powered chat interface that communicates with AWS Bedrock (Amazon Nova models) and includes resume request functionality with reCAPTCHA v3 protection.

## Architecture

### Frontend-Backend Integration
- **Frontend**: Next.js 16 with TypeScript, React 19, Tailwind CSS v4
- **Backend**: FastAPI server (`../backend/server.py`) with AWS Bedrock integration
- **API Communication**: Frontend calls backend at `NEXT_PUBLIC_API_URL` (defaults to `http://localhost:8000`)
- **Static Export**: Configured with `output: 'export'` in `next.config.ts` for static site generation

### Key Components
- `components/digitial-twin-portfolio.tsx`: Main portfolio component with chat interface
  - Manages chat state with session IDs
  - Handles message streaming from backend
  - Integrates reCAPTCHA v3 for form submissions
  - Contains resume request modal with contact form
- `components/twin.tsx`: Additional twin-related component
- `app/page.tsx`: Entry point that renders the DigitalTwin component
- `app/layout.tsx`: Root layout with Google Fonts (Geist), reCAPTCHA script loading

### State Management
- Chat sessions use session IDs returned from the backend (`/chat` endpoint)
- Messages stored locally in component state with Message interface (`role`, `content`, `timestamp`)
- Backend maintains conversation history via S3 or local file system (configurable via `USE_S3` env var)

### Backend Integration Points
1. **Chat API** (`POST /chat`):
   - Sends: `{ message: string, session_id?: string }`
   - Receives: `{ response: string, session_id: string }`
   - Backend uses AWS Bedrock (configurable model via `BEDROCK_MODEL_ID`)

2. **Resume Request** (`POST /resume/request`):
   - Requires reCAPTCHA token
   - Sends: `{ name, email, message, honeypot, recaptchaToken, timestamp }`
   - Protected by rate limiting and reCAPTCHA verification on backend

### Environment Configuration
Required environment variables in `.env.local`:
- `NEXT_PUBLIC_SITE_KEY`: Google reCAPTCHA v3 site key
- `NEXT_PUBLIC_API_URL`: Backend API URL (production: set in `.env.production`)

Backend uses AWS services and requires:
- AWS Bedrock access (model: `amazon.nova-2-lite-v1:0` by default)
- SES for email sending (resume requests)
- Optional S3 for conversation memory storage

## Development Commands

### Install dependencies
```bash
npm install
```

### Run development server
```bash
npm run dev
# Note: Uses --webpack flag explicitly
# Access at http://localhost:3000
```

### Build for production
```bash
npm run build
# Creates static export in /out directory
```

### Start production server
```bash
npm start
```

### Run linter
```bash
npm run lint
# Uses ESLint with Next.js config
```

### Run backend server (required for chat functionality)
```bash
cd ../backend
# Ensure .venv is activated and dependencies installed
python server.py  # or uvicorn server:app --reload
```

## TypeScript Configuration
- Path alias: `@/*` maps to root directory
- Strict mode enabled
- Module resolution: bundler
- React JSX runtime (react-jsx)

## Styling
- Tailwind CSS v4 with PostCSS
- Global styles in `app/globals.css`
- Uses Geist Sans and Geist Mono fonts from Google Fonts

## Image Handling
- Image optimization disabled (`unoptimized: true`) due to static export
- Public assets in `/public` directory

## Important Notes
- The application exports as a static site, so server-side features are limited to client-side API calls
- Chat sessions persist via backend session management, not frontend state
- reCAPTCHA is loaded conditionally based on `NEXT_PUBLIC_SITE_KEY` presence
- Backend must be running for chat and resume request features to work
