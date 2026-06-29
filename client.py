import asyncio
import os
from utils.cli import *
from rich.console import Console
console = Console()

from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_mcp_adapters.client import MultiServerMCPClient

from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

def extract_text(content):

    if isinstance(content, str):
        return content

    if isinstance(content, list):

        text = ""

        for item in content:

            if isinstance(item, dict):

                text += item.get("text", "")

        return text

    return ""

# -----------------------
# MCP Client
# -----------------------

client = MultiServerMCPClient(
    {
        "math": {
            "transport": "stdio",
            "command": "python",
            "args": ["servers/math_server.py"],
        },
        "market": {
            "transport": "stdio",
            "command": "python",
            "args": ["servers/market_server.py"],
        },
        "weather": {
            "transport": "stdio",
            "command": "python",
            "args": ["servers/weather_server.py"],
        },
        "search": {
            "transport": "stdio",
            "command": "python",
            "args": ["servers/search_server.py"],
        },
        "rag": {
            "transport": "stdio",
            "command": "python",
            "args": ["servers/rag_server.py"],
        },
    }
)


async def main():

    # print("Loading MCP tools...")
    loading()

    tools = await client.get_tools()
    loaded(len(tools))
    # print(f"Loaded {len(tools)} tools")

    llm = ChatGoogleGenerativeAI(
            model="gemini-3.1-flash-lite",
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            temperature=0.2,
        )

    memory = MemorySaver()

    agent = create_react_agent(
        model=llm,
        tools=tools,
        checkpointer=memory,
    )

    config = {
        "configurable": {
            "thread_id": "demo-session"
        }
    }
    title()
    ready()
    # print("\nReady!")
    # print("Type 'exit' to quit.\n")

    while True:
        user()

        question = input()
        # question = input("You: ")

        if question.lower() in {"exit", "quit"}:
            break

        print()
        assistant()

        async for event in agent.astream_events(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": question,
                    }
                ]
            },
            config=config,
            version="v2",
        ):

            event_type = event["event"]

            # --------------------
            # Tool Start
            # --------------------

            if event_type == "on_tool_start":

                tool = event["name"]

                # print(f"\n🛠 Calling: {tool}")
                tool_cli(event["name"])

            # --------------------
            # Tool End
            # --------------------

            elif event_type == "on_tool_end":

                # print("✓ Tool Finished")
                tool_done()

            # --------------------
            # Stream Tokens
            # --------------------

            elif event_type == "on_chat_model_stream":

                chunk = event["data"]["chunk"]

                if hasattr(chunk, "content") and chunk.content:

                    # print(chunk.content, end="", flush=True)
                    piece = extract_text(chunk.content)
                    # print(piece, end="", flush=True)
                    console.out(
                        piece,
                        end=""
                    )

        print("\n")


if __name__ == "__main__":
    asyncio.run(main())