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
## visualize
from IPython.display import Image, display
## time
from time import sleep
import datetime
import pytz # convert timezone
global now # get time from user's PC
now = datetime.datetime.now(pytz.timezone('Asia/Tokyo'))
## library firebase
import firebase_admin
from google.oauth2 import service_account
from google.cloud import firestore
import json
## library calculate tokens
import tiktoken

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
DISPLAY_TEXT_LIST = [
'「原子力発電を廃止すべきか否か」という意見に対して、あなたの意見を入力し、送信ボタンを押してください。', 
'あなたの意見を入力し、送信ボタンを押してください。'] # 対話ターンの表示テキスト
URL = "https://www.nagoya-u.ac.jp/"
FIREBASE_APIKEY_DICT = json.loads(st.secrets["firebase"]["textkey"])

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
st.session_state.memory = MemorySaver()

def stream_graph_updates(user_input: str):
    # The config is the **second positional argument** to stream() or invoke()!
    events = graph.stream(
        {"messages": [("user", user_input)]}, config, stream_mode="values"
    )
    for event in events:
        print(event["messages"])
        event["messages"][-1].pretty_print()

# ID入力※テスト用フォーム
def input_id():
    with st.form("id_form", enter_to_submit=False):
        user_id = st.text_input('学籍番号を入力し、送信ボタンを押してください')
        submit_id = st.form_submit_button(
            label="送信",
            type="primary")
    if submit_id:
        st.session_state.user_id = str(user_id)
        st.session_state.state = 2
        st.rerun()

def chatbot(state: State):
    return {"messages": [chain.invoke({"history":state["messages"]})]}

# The first argument is the unique node name
# The second argument is the function or object that will be called whenever
# the node is used.
graph_builder.add_node("chatbot", chatbot)
graph_builder.add_edge(START, "chatbot")
graph_builder.add_edge("chatbot", END)
graph = graph_builder.compile(checkpointer=st.session_state.memory)

# Firebase 設定の読み込み
creds = service_account.Credentials.from_service_account_info(FIREBASE_APIKEY_DICT)
project_id = FIREBASE_APIKEY_DICT["project_id"]
db = firestore.Client(credentials=creds, project=project_id)

# 入力時の動作
def click_to_submit():
    st.write(st.session_state.log)
    # 待機中にも履歴を表示
    chat_placeholder = st.empty()
    with chat_placeholder.container():
        for i in range(len(st.session_state.log)):
            msg = st.session_state.log[i]
            if msg["role"] == "user":
                message(msg["content"], is_user=True, avatar_style="adventurer", seed="Nala", key = "user_{}".format(i))
            else:
                message(msg["content"], is_user=False, avatar_style="micah", key = "ai_{}".format(i))
    with st.spinner("相手からの返信を待っています..."):
        st.session_state.send_time = str(datetime.datetime.now(pytz.timezone('Asia/Tokyo')))
        st.session_state.user_input
            while True:
                try:
                    stream_graph_updates(user_input)
                    st.session_state.log = stream_graph_updates(user_input)
                    st.session_state.response = st.session_state.with_message_history.invoke({"input": st.session_state.user_input},
                                                            config={"configurable": {"session_id": st.session_state.user_id}},
                                                           )
                except:
                    stream_graph_updates(user_input)
                    break
                stream_graph_updates(user_input)

        st.session_state.response = st.session_state.response.content
        # st.session_state.response = conversation.predict(input=st.session_state.user_input)
        # count token
        # if not "total_output_tokens" in st.session_state:
            # st.session_state.total_output_tokens = 0
        # st.session_state.output_tokens = len(encoding.encode(st.session_state.response))
        # st.session_state.total_output_tokens += st.session_state.output_tokens
        st.session_state.log.append({"role": "AI", "content": st.session_state.response})
        sleep(sleep_time_list[st.session_state.talktime])
        st.session_state.return_time = str(datetime.datetime.now(pytz.timezone('Asia/Tokyo')))
        doc_ref = db.collection(str(st.session_state.user_id)).document(str(st.session_state.talktime))
        doc_ref.set({
            "Human": st.session_state.user_input,
            "AI": st.session_state.response,
            "Human_msg_sended": st.session_state.send_time,
            "AI_msg_returned": st.session_state.return_time,
        })
        st.session_state.talktime += 1
        st.session_state.state = 2
        st.rerun()

# チャット画面
def chat_page():
    # 会話回数とログ初期化
    if not "talktime" in st.session_state:
        st.session_state.talktime = 0
    if not "log" in st.session_state:
        st.session_state.log = []
    while True:
    try:
        stream_graph_updates(user_input)
        st.session_state.log = stream_graph_updates(user_input)
    except:
        stream_graph_updates(user_input)
        break
    stream_graph_updates(user_input)
    # 履歴表示
    chat_placeholder = st.empty()
    with chat_placeholder.container():
        for i in range(len(st.session_state.log)):
            msg = st.session_state.log[i]
            if msg["role"] == "user":
                message(msg["content"], is_user=True, avatar_style="adventurer", seed="Nala", key = "user_{}".format(i))
            else:
                message(msg["content"], is_user=False, avatar_style="micah", key = "ai_{}".format(i))
        # print token
        # if "input_tokens" in st.session_state:
            # st.write("input tokens : {}※テスト用".format(st.session_state.input_tokens))
            # st.write("output tokens : {}※テスト用".format(st.session_state.output_tokens))
    # 入力フォーム
    if st.session_state.talktime < 5: # 会話時
        # 念のため初期化
        if not "user_input" in st.session_state:
            st.session_state.user_input = "hogehoge"
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
                st.session_state.user_input = user_input
                st.session_state.log.append({"role": "user", "content": st.session_state.user_input}
                st.session_state.state = 3
                st.rerun()
    elif st.session_state.talktime == 5: # 会話終了時

        # print total token counts
        # st.write("total input tokens : {}※テスト用".format(st.session_state.total_input_tokens))
        # st.write("total output tokens : {}※テスト用".format(st.session_state.total_output_tokens))
        st.markdown(
            f"""
            会話が規定回数に達しました。\n\n
            以下の"アンケートに戻る"をクリックして、アンケートに回答してください。\n\n
            アンケートページは別のタブで開きます。\n\n
            <a href="{url}" target="_blank">アンケートに戻る</a>
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
    if not "state" in st.session_state:
        st.session_state.state = 1
    if st.session_state.state == 1:
        input_id()
    elif st.session_state.state == 2:
        chat_page()
    elif st.session_state.state == 3:
        click_to_submit()

if __name__ == "__main__":
    main()
