import os
from fastapi import FastAPI
import uvicorn
from copilotkit import LangGraphAGUIAgent 
from ag_ui_langgraph import add_langgraph_fastapi_endpoint 
from agent import graph

from dotenv import load_dotenv
load_dotenv()

# Ensure OpenAI API key is loaded from environment
# The ChatOpenAI in agent.py will automatically use OPENAI_API_KEY from environment
if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("OPENAI_API_KEY environment variable is required. Please set it in your .env file.")

app = FastAPI()
add_langgraph_fastapi_endpoint(
  app=app,
  agent=LangGraphAGUIAgent(
    name="sample_agent", # the name of your agent defined in langgraph.json
    description="Describe your agent here, will be used for multi-agent orchestration",
    graph=graph, # the graph object from your langgraph import
  ),
  path="/", # the endpoint you'd like to serve your agent on
)

# add new route for health check
@app.get("/health")
def health():
    """Health check."""
    return {"status": "ok"}

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