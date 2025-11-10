"""
This is the main entry point for the agent.
It defines the workflow graph, state, tools, nodes and edges.
"""

from typing import Any, List, Dict, Optional
from typing_extensions import Literal
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, BaseMessage
from langchain_core.runnables import RunnableConfig
from langchain.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.types import Command
from langgraph.graph import MessagesState
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver

from copilotkit import LangGraphAGUIAgent

# This custom agent is used to forward the authorization token from the client to the agent's config.
# It is a necessary component for the authentication to work in a self-hosted environment.
class CustomLangGraphAGUIAgent(LangGraphAGUIAgent):
    async def prepare_stream(
        self, input, agent_state, config: RunnableConfig
    ):
        forwarded_props = input.forwarded_props or {}
        
        # Start with the existing configurable values
        new_configurable = config.get("configurable", {}).copy()
        
        # Merge configurable from forwarded_props.config
        runtime_configurable = forwarded_props.get("config", {}).get("configurable", {})
        new_configurable.update(runtime_configurable)
        
        # Merge top-level authorization from forwarded_props
        if "authorization" in forwarded_props:
            new_configurable["authorization"] = forwarded_props["authorization"]
            
        config["configurable"] = new_configurable
        
        return await super().prepare_stream(input, agent_state, config)


class AgentState(MessagesState):
    """
    Here we define the state of the agent

    In this instance, we're inheriting from CopilotKitState, which will bring in
    the CopilotKitState fields. We're also adding a custom field, `language`,
    which will be used to set the language of the agent.
    """
    proverbs: List[str] = []
    tools: List[Any]
    authorization: Optional[Dict[str, Any]] = None
    # your_custom_agent_state: str = ""

@tool
def get_weather(location: str):
    """
    Get the weather for a given location.
    """
    return f"The weather for {location} is 70 degrees."

# @tool
# def your_tool_here(your_arg: str):
#     """Your tool description here."""
#     print(f"Your tool logic here")
#     return "Your tool response here."

backend_tools = [
    get_weather
    # your_tool_here
]

# Extract tool names from backend_tools for comparison
backend_tool_names = [tool.name for tool in backend_tools]


def get_user_info_from_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decodes user information from a JWT-like token.

    NOTE: This is a simplified decoder for demonstration purposes and does NOT
    perform signature verification. In a production environment, always use a
    trusted JWT library (e.g., PyJWT) to validate the token's signature
    and claims.
    """
    if not token:
        return None
    
    try:
        import base64
        import json

        parts = token.split('.')
        if len(parts) != 3:
            # Not a valid JWT format
            return None
            
        payload = parts[1]
        
        # Add padding if necessary and decode
        padded_payload = payload + '=' * (-len(payload) % 4)
        decoded_payload = base64.b64decode(padded_payload).decode('utf-8')
        user_data = json.loads(decoded_payload)
        
        return {
            "user_id": user_data.get("sub") or user_data.get("user_id"),
            "name": user_data.get("name"),
            "email": user_data.get("email"),
            "role": user_data.get("role"),
        }
    except (IndexError, base64.binascii.Error, json.JSONDecodeError, UnicodeDecodeError) as e:
        print(f"Failed to decode token: {e}")
        return None


def get_user_info_from_config(config: RunnableConfig) -> Optional[Dict[str, Any]]:
    """
    Extracts user information from the RunnableConfig by looking for an authorization token.
    """
    configurable = config.get("configurable", {})
    auth_token = configurable.get("authorization")

    if not auth_token:
        return None

    # Handle bearer token format
    token = (
        auth_token.replace("Bearer ", "")
        if isinstance(auth_token, str) and auth_token.startswith("Bearer ")
        else auth_token
    )
    
    user_info = get_user_info_from_token(token)
    
    if user_info:
        print(f"✅ Authenticated user: {user_info.get('name')} (ID: {user_info.get('user_id')})")
    else:
        print("⚠️  Failed to authenticate user from token.")
        
    return user_info


def auth_node(state: AgentState, config: RunnableConfig) -> AgentState:
    """
    Authenticates the user and updates the state with user information.
    If no authentication is found, it defaults to an anonymous user.
    """
    user_data = get_user_info_from_config(config)
    
    if user_data:
        state["authorization"] = user_data
    else:
        print("⚠️  No authentication found - using anonymous user")
        state["authorization"] = {
            "user_id": "anonymous",
            "name": None,
            "email": None,
            "role": None,
        }
    return state


async def chat_node(state: AgentState, config: RunnableConfig) -> Command[Literal["tool_node", "__end__"]]:
    """
    Standard chat node based on the ReAct design pattern. It handles:
    - The model to use (and binds in CopilotKit actions and the tools defined above)
    - The system prompt
    - Getting a response from the model
    - Handling tool calls

    For more about the ReAct design pattern, see:
    https://www.perplexity.ai/search/react-agents-NcXLQhreS0WDzpVaS4m9Cg
    """

    # 1. Define the model
    model = ChatOpenAI(model="gpt-4o")

    # Get user information from the state, which was set in the auth_node
    user_data = state.get("authorization")
    is_authenticated = user_data and user_data.get("user_id") != "anonymous"

    # 2. Bind the tools to the model
    # Conditionally include backend_tools if the user is authenticated
    tools_to_bind = list(state.get("tools", []))
    if is_authenticated:
        tools_to_bind.extend(backend_tools)

    model_with_tools = model.bind_tools(
        tools_to_bind,
        # 2.1 Disable parallel tool calls to avoid race conditions,
        #     enable this for faster performance if you want to manage
        #     the complexity of running tool calls in parallel.
        parallel_tool_calls=False,
    )

    # 3. Define the system message
    user_info = ""
    if is_authenticated:
        user_id = user_data.get("user_id")
        user_name = user_data.get("name") or "Unknown"
        user_email = user_data.get("email") or "not provided"
        user_role = user_data.get("role") or "user"
        user_info = f"The current user is {user_name} (ID: {user_id}, Email: {user_email}, Role: {user_role})."
    else:
        user_info = "The user is not authenticated. The `get_weather` tool is only available to authenticated users. If asked for the weather, tell the user they need to sign in to use this feature."
    
    system_message = SystemMessage(
        content=f"""You are a helpful assistant.
{user_info}
When asked about the current user's identity (e.g., 'who am I?'), provide the user's details from the information above.
The current proverbs are {state.get('proverbs', [])}."""
    )

    # 4. Run the model to generate a response
    response = await model_with_tools.ainvoke([
        system_message,
        *state["messages"],
    ], config)

    # only route to tool node if tool is not in the tools list
    if route_to_tool_node(response):
        print("routing to tool node")
        return Command(
            goto="tool_node",
            update={
                "messages": [response],
            }
        )

    # 5. We've handled all tool calls, so we can end the graph.
    return Command(
        goto=END,
        update={
            "messages": [response],
        }
    )

def route_to_tool_node(response: BaseMessage):
    """
    Route to tool node if any tool call in the response matches a backend tool name.
    """
    tool_calls = getattr(response, "tool_calls", None)
    if not tool_calls:
        return False

    for tool_call in tool_calls:
        if tool_call.get("name") in backend_tool_names:
            return True
    return False

# Define the workflow graph
workflow = StateGraph(AgentState)
workflow.add_node("auth_node", auth_node)
workflow.add_node("chat_node", chat_node)
workflow.add_node("tool_node", ToolNode(tools=backend_tools))
workflow.add_edge("auth_node", "chat_node")
workflow.add_edge("tool_node", "chat_node")
workflow.set_entry_point("auth_node")

graph = workflow.compile(checkpointer=MemorySaver())
