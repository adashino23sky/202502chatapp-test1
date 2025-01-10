# import libraries
## langchain
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
## class definition
from typing import Annotated
from typing_extensions import TypedDict
## langgraph
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
## colab
from google.colab import userdata
## visualize
from IPython.display import Image, display

# constant
## langsmith（動いていない）
LANGCHAIN_TRACING_V2=True
LANGCHAIN_ENDPOINT="https://api.smith.langchain.com"
LANGCHAIN_API_KEY=userdata.get('langchain_api_key')
LANGCHAIN_PROJECT="chatapptest202501"
## langchain
OPENAI_API_KEY=userdata.get('openai_api_key')
MODEL_NAME="gpt-4o-mini"
## setting
FPATH = "prompt.txt"
with open(file = FPATH, encoding = "utf-8") as f:
    SYSTEM_PROMPT = f.read()

class State(TypedDict):
    # Messages have the type "list". The `add_messages` function
    # in the annotation defines how this state key should be updated
    # (in this case, it appends messages to the list, rather than overwriting them)
    messages: Annotated[list, add_messages]

graph_builder = StateGraph(State)
llm = ChatOpenAI(model=MODEL_NAME,
                 api_key=OPENAI_API_KEY)
prompt = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder("history"),
    ]
)

memory = MemorySaver()
config = {"configurable": {"thread_id": "1"}}
chain = prompt | llm

def chatbot(state: State):
    return {"messages": [chain.invoke({"history":state["messages"]})]}

# The first argument is the unique node name
# The second argument is the function or object that will be called whenever
# the node is used.
graph_builder.add_node("chatbot", chatbot)
graph_builder.add_edge(START, "chatbot")
graph_builder.add_edge("chatbot", END)
graph = graph_builder.compile(checkpointer=memory)

try:
    display(Image(graph.get_graph().draw_mermaid_png()))
except Exception:
    # This requires some extra dependencies and is optional
    pass

def stream_graph_updates(user_input: str):
    # The config is the **second positional argument** to stream() or invoke()!
    events = graph.stream(
        {"messages": [("user", user_input)]}, config, stream_mode="values"
    )
    for event in events:
        print(event["messages"])
        event["messages"][-1].pretty_print()

while True:
    try:
        user_input = input("user: ")
        if user_input.lower() in ["quit", "exit", "q"]:
            print("Goodbye!")
            break

        stream_graph_updates(user_input)
    except:
        # fallback if input() is not available
        user_input = "What do you know about LangGraph?"
        print("User: " + user_input)
        stream_graph_updates(user_input)
        break
