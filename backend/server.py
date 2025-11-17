import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from ag_ui_langgraph import add_langgraph_fastapi_endpoint 
from agent import graph, CustomLangGraphAGUIAgent
from file_routes import router as file_router

from dotenv import load_dotenv
load_dotenv()

# Ensure OpenAI API key is loaded from environment
# The ChatOpenAI in agent.py will automatically use OPENAI_API_KEY from environment
if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("OPENAI_API_KEY environment variable is required. Please set it in your .env file.")

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# add new route for health check (must be defined before langgraph endpoint)
@app.get("/health")
def health():
    """Health check."""
    return {"status": "ok"}

app.include_router(file_router)

add_langgraph_fastapi_endpoint(
  app=app,
  agent=CustomLangGraphAGUIAgent(
    name="agent_with_auth", # the name of your agent defined in langgraph.json
    description="Describe your agent here, will be used for multi-agent orchestration",
    graph=graph, # the graph object from your langgraph import
  )
)

def main():
    """Run the uvicorn server."""
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(
        "server:app", # the path to your FastAPI file
        host="0.0.0.0",
        port=port,
        reload=True,
    )

if __name__ == "__main__":
    main()
