# import libraries
## streamlit
import streamlit as st
from streamlit_chat import message
##langchain
from langchain_openai.chat_models import ChatOpenAI
from langchain_core.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
)
## class definition
from typing import Annotated
from typing_extensions import TypedDict
## langgraph
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
# ## visualize
# from IPython.display import Image, display
## time
from time import sleep
import datetime
import pytz # convert timezone
global now # get time from user's PC
now = datetime.datetime.now(pytz.timezone('Asia/Tokyo'))
# ## library firebase
# import firebase_admin
# from google.oauth2 import service_account
# from google.cloud import firestore
# import json
# ## library calculate tokens
# import tiktoken

# constant
## langsmith（動いていない）
# LANGCHAIN_TRACING_V2=True
# LANGCHAIN_ENDPOINT="https://api.smith.langchain.com"
# LANGCHAIN_API_KEY=userdata.get('langchain_api_key')
# LANGCHAIN_PROJECT="chatapptest202501"
## langchain
OPENAI_API_KEY=st.secrets.openai_api_key
MODEL_NAME="gpt-4o-mini"
## chat act config
FPATH = "prompt.txt" # recommend hidden
with open(file = FPATH, encoding = "utf-8") as f:
    SYSTEM_PROMPT = f.read()
SLEEP_TIME_LIST = [5, 5, 5, 5, 5, 5, 5, 5] # 各対話ターンの待機時間
DISPLAY_TEXT_LIST = ['なにか発言してみてね', 
                     '続けて発言してね'] # 対話ターンの表示テキスト
URL = "https://www.nagoya-u.ac.jp/"
# FIREBASE_APIKEY_DICT = json.loads(st.secrets["firebase"]["textkey"])

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
chain = prompt | llm
if "user_id" in st.session_state:
    config = {"configurable": {"thread_id": st.session_state.user_id}}
if not "memory" in st.session_state:
    st.session_state.memory = MemorySaver()

# ID入力※テスト用フォーム
def input_id():
    st.write("Entering input_id() function")  # デバッグ
    with st.form("id_form", enter_to_submit=False):
        user_id = st.text_input('会話IDを入力し、送信ボタンを押してください')
        submit_id = st.form_submit_button(
            label="送信",
            type="primary")
    if submit_id:
        st.write(f"ID form submitted with user_id: {user_id}")  # デバッグ
        st.session_state.user_id = str(user_id)
        st.session_state.state = 2
        st.rerun()
    else:
        st.write("ID form not submitted yet")  # デバッグ

def chatbot(state: State):
    return {"messages": [chain.invoke({"history":state["messages"]})]}

# The first argument is the unique node name
# The second argument is the function or object that will be called whenever
# the node is used.
graph_builder.add_node("chatbot", chatbot)
graph_builder.add_edge(START, "chatbot")
graph_builder.add_edge("chatbot", END)
graph = graph_builder.compile(checkpointer=st.session_state.memory)

def stream_graph_updates(user_input: str):
    try:
        events = graph.stream({"messages": [("user", user_input)]}, config, stream_mode="values")
        st.info("イベントストリームを開始しました。")
        for event in events:
            st.json(event)  # デバッグ: 各イベント内容を表示
            messages = event["messages"]
            msg_list = []
            for value in range(len(messages)):
                msg_list.append({
                    "role": messages[value].type,
                    "content": messages[value].content
                })
        if not msg_list:
            st.write("No messages collected from events.")  # デバッグ
        return msg_list
    except Exception as e:
        st.error(f"Error occurred: {e}")
        return []


# 入力時の動作
def submitted():
    st.write("Entering submitted() function")  # デバッグ
    st.write(f"Current state: {st.session_state.state}")  # デバッグ
    chat_placeholder = st.empty()
    with chat_placeholder.container():
        st.write(f"Log before displaying: {st.session_state.log}")  # デバッグ
        for i in range(len(st.session_state.log)):
            msg = st.session_state.log[i]
            if msg["role"] == "human":
                message(msg["content"], is_user=True, avatar_style="adventurer", seed="Nala", key=f"user_{i}")
            else:
                message(msg["content"], is_user=False, avatar_style="micah", key=f"ai_{i}")
    with st.spinner("相手からの返信を待っています..."):
        sleep(SLEEP_TIME_LIST[st.session_state.talktime])
        st.session_state.return_time = str(datetime.datetime.now(pytz.timezone('Asia/Tokyo')))
        user_input = st.session_state.log[-1]["content"]
        st.write(f"User input for stream_graph_updates: {user_input}")  # デバッグ
        new_messages = stream_graph_updates(user_input)
        st.write(f"New messages from stream_graph_updates: {new_messages}")  # デバッグ
        if new_messages:
            st.session_state.log.extend(new_messages)
        else:
            st.write("No new messages received")  # デバッグ
        sleep(5)
        st.session_state.talktime += 1
        st.session_state.state = 2
        st.rerun()

# チャット画面
def chat_page():
    st.write("Entering chat_page() function")  # デバッグ
    if "talktime" not in st.session_state:
        st.session_state.talktime = 0
        st.write("talktime initialized to 0")  # デバッグ
    if "log" not in st.session_state:
        st.session_state.log = []
        st.write("log initialized to empty list")  # デバッグ
    st.write(f"Current log: {st.session_state.log}")  # デバッグ
    st.write(f"Current talktime: {st.session_state.talktime}")  # デバッグ
    chat_placeholder = st.empty()
    with chat_placeholder.container():
        for i in range(len(st.session_state.log)):
            msg = st.session_state.log[i]
            if msg["role"] == "human":
                message(msg["content"], is_user=True, avatar_style="adventurer", seed="Nala", key=f"user_{i}")
            else:
                message(msg["content"], is_user=False, avatar_style="micah", key=f"ai_{i}")
    if st.session_state.talktime < 5:  # 会話時
        if not "user_input" in st.session_state:
            st.session_state.user_input = "hogehoge"
            st.write("user_input initialized to 'hogehoge'")  # デバッグ
        with st.container():
            with st.form("chat_form", clear_on_submit=True, enter_to_submit=False):
                if st.session_state.talktime == 0:
                    user_input = st.text_area(DISPLAY_TEXT_LIST[0])
                else:
                    user_input = st.text_area(DISPLAY_TEXT_LIST[1])
                submit_msg = st.form_submit_button(
                    label="送信",
                    type="primary")
            if submit_msg:
                st.write(f"Form submitted with user_input: {user_input}")  # デバッグ
                st.session_state.send_time = str(datetime.datetime.now(pytz.timezone('Asia/Tokyo')))
                st.session_state.log.append({"role": "human", "content": user_input})
                st.write(f"Updated log after appending: {st.session_state.log}")  # デバッグ
                st.session_state.state = 3
                st.rerun()
            else:
                st.write("Chat form not submitted yet")  # デバッグ
    elif st.session_state.talktime == 5:  # 会話終了時
        st.markdown(
            f"""
            5回会話したので終了します。\n\n
            <a href="{URL}" target="_blank">アンケートに戻る</a>
            """,
            unsafe_allow_html=True)

def main():
    hide_streamlit_style = """
                <style>
                div[data-testid="stToolbar"] {
                visibility: hidden;
                height: 0%;
                position: fixed;
                }
                div[data-testid="stDecoration"] {
                visibility: hidden;
                height: 0%;
                position: fixed;
                }
                div[data-testid="stStatusWidget"] {
                visibility: hidden;
                height: 0%;
                position: fixed;
                }
                #MainMenu {
                visibility: hidden;
                height: 0%;
                }
                header {
                visibility: hidden;
                height: 0%;
                }
                footer {
                visibility: hidden;
                height: 0%;
                }
                </style>
                """
    st.markdown(hide_streamlit_style, unsafe_allow_html=True) 
    st.write("Entering main() function")  # デバッグ
    if "state" not in st.session_state:
        st.session_state.state = 1
        st.write("State initialized to 1")  # デバッグ
    st.write(f"Current state: {st.session_state.state}")  # デバッグ
    if st.session_state.state == 1:
        input_id()
    elif st.session_state.state == 2:
        chat_page()
    elif st.session_state.state == 3:
        submitted()

if __name__ == "__main__":
    main()
