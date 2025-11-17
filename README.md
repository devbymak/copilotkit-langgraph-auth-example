# CopilotKit <> LangGraph Integration Example

Secure your LangGraph agents with user authentication. Shows how to:

- 🔐 Authenticate users before agent interaction
- 🛡️ Secure agent endpoints and tools based on user identity
- 👤 Access user information within LangGraph agents
- 🎯 Conditionally enable/disable agent capabilities
- 📁 Upload and process files (PDF, Excel, CSV) with the agent

## Prerequisites

- Node.js 18+ & Python 3.8+
- Package manager (pnpm/npm/yarn/bun)
- OpenAI API Key

## Getting Started

1. Install dependencies:

```bash
pnpm install  # or npm/yarn/bun install
```

2. Set up your OpenAI API key:

```bash
echo 'OPENAI_API_KEY=your-api-key' > backend/.env
```

3. Start the development server:

```bash
pnpm dev  # starts both UI and agent servers
```

## Available Scripts

- `dev` - Start both servers
- `dev:debug` - Start with debug logging
- `dev:ui` - Start Next.js server only
- `dev:agent` - Start LangGraph agent only
- `install:agent` - Install Python dependencies

## Project Structure

- **Frontend** (`src/app/`)

  - `page.tsx` - Main UI with authenticated agent
  - `components/fake-auth-provider.tsx` - Auth provider (replace with real auth)
  - `components/user-menu.tsx` - Login/logout menu
  - `api/copilotkit/route.ts` - API route handling auth & forwarding to agent

- **Backend** (`backend/`)
  - `agent.py` - LangGraph agent with auth-aware tools
  - `server.py` - FastAPI server receiving user context
  - `file_routes.py` - File upload and processing endpoints

## Authentication Flow

1. User logs in via frontend auth provider
2. User identity passed to CopilotKit
3. CopilotKit forwards user info to agent
4. Agent tools access user identity and adjust behavior

## File Upload Support

The agent supports file uploads with automatic processing:

- **PDF Files** - Text extraction with page-by-page content
- **Excel Files** (.xlsx, .xls) - Sheet parsing, column analysis, and data preview
- **CSV Files** (.csv) - Data parsing, column analysis, and data preview

Files are processed and stored per conversation thread, allowing the agent to:
- Answer questions about file content
- Analyze data from uploaded spreadsheets
- Extract and reference information from documents

File processing endpoints:
- `/process-file` - Upload and process PDF, Excel, or CSV files
- `/files/{thread_id}` - List all uploaded files for a thread
- `/file/{thread_id}/{file_id}` - Retrieve file content
- `/file/{thread_id}/{file_id}` (DELETE) - Remove uploaded files

## Implementing Your Own Auth

Replace `fake-auth-provider.tsx` with your auth system (NextAuth.js, Auth0, Clerk, Supabase, etc.)

## Troubleshooting

- **Agent issues**: Check agent is running on port 8000 and OpenAI API key is set in `backend/.env`
- **Auth issues**: Verify user is logged in and context is passed to CopilotKit
- **Python errors**: Run `pnpm install:agent`

## License

MIT License
