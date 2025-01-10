# library streamlit
import streamlit as st
from streamlit_chat import message

# library langchain
from langchain_openai.chat_models import ChatOpenAI
# from langchain.chains import ConversationChain
# from langchain.memory import ConversationBufferWindowMemory
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate
)
from langchain_core.runnables.history import RunnableWithMessageHistory

# library time
from time import sleep
import datetime
import pytz # convert timezone
global now # get time from user's PC
now = datetime.datetime.now(pytz.timezone('Asia/Tokyo'))

# library firebase
import firebase_admin
from google.oauth2 import service_account
from google.cloud import firestore
import json

# library calculate tokens
import tiktoken

# プロンプト
prompt_list = ["prompt.txt", "preprompt_affirmative_individualizing_nuclear.txt", "preprompt_negative_binding_nuclear.txt"]
# モデル
model_list = ["gpt-4-1106-preview", "gpt-4o", "gpt-4o-mini"]
# 待機時間
sleep_time_list = [5, 5, 5, 5, 5, 5, 5, 5]
# 表示テキスト
text_list = ['「原子力発電を廃止すべきか否か」という意見に対して、あなたの意見を入力し、送信ボタンを押してください。', 'あなたの意見を入力し、送信ボタンを押してください。']

# メモリ初期化
# if not "memory" in st.session_state:
#     st.session_state.memory = ConversationBufferWindowMemory(k=8, return_messages=True)

# ID入力※テスト用フォーム
def input_id():
    if not "user_id" in st.session_state:
        st.session_state.user_id = "hogehoge"
    with st.form("id_form", enter_to_submit=False):
        # prompt_option = st.selectbox(
            # "プロンプトファイル選択※テスト用フォーム",
            # ("{}".format(prompt_list[0]), "{}".format(prompt_list[1])),)
        model_option = st.selectbox(
            "モデル選択※テスト用フォーム",
            ("{}".format(model_list[0]), "{}".format(model_list[1]), "{}".format(model_list[2])),)
        user_id = st.text_input('学籍番号を入力し、送信ボタンを押してください')
        submit_id = st.form_submit_button(
            label="送信",
            type="primary")
    if submit_id:
        with open(prompt_list[0], 'r', encoding='utf-8') as f:
            st.session_state.systemprompt = f.read()
        st.session_state.model = model_option
        st.session_state.user_id = str(user_id)
        st.session_state.state = 2
        st.rerun()

# プロンプト設定
if "systemprompt" in st.session_state:
    template = st.session_state.systemprompt # st.session_state.systemprompt
    st.session_state.prompt = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(template),
        MessagesPlaceholder(variable_name="history"),
        HumanMessagePromptTemplate.from_template("{input}")
    ])

# モデル設定
if "model" in st.session_state:
    # モデルのインスタンス生成
    chat = ChatOpenAI(
        model=st.session_state.model,
        temperature=0,
        max_tokens=None,
        timeout=None,
        max_retries=0,
        api_key= st.secrets.openai_api_key
    )
    # チェインを設定
    st.session_state.runnable = st.session_state.prompt | chat
    st.session_state.store = {}
    def get_session_history(session_id: str) -> BaseChatMessageHistory:
        if session_id not in st.session_state.store:
            st.session_state.store[session_id] = ChatMessageHistory()
        return st.session_state.store[session_id]
    st.session_state.with_message_history = RunnableWithMessageHistory(
        st.session_state.runnable,
        get_session_history,
        input_messages_key="input",
        history_messages_key="history",
    )
    # encoding = tiktoken.encoding_for_model(st.session_state.model)

# Firebase 設定の読み込み
key_dict = json.loads(st.secrets["firebase"]["textkey"])
creds = service_account.Credentials.from_service_account_info(key_dict)
project_id = key_dict["project_id"]
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
        st.session_state.response = st.session_state.with_message_history.invoke({"input": st.session_state.user_input},
                                                            config={"configurable": {"session_id": st.session_state.user_id}},
                                                           )
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
                    user_input = st.text_area(text_list[0])
                else:
                    user_input = st.text_area(text_list[1])
                submit_msg = st.form_submit_button(
                    label="送信",
                    type="primary")
            if submit_msg:
                st.session_state.user_input = user_input
                st.session_state.log.append({"role": "user", "content": st.session_state.user_input})
                # count token
                # if not "total_input_tokens" in st.session_state:
                    # st.session_state.total_input_tokens = 0
                # st.session_state.input_tokens = 0
                # system_tokens = encoding.encode(template)
                # st.session_state.input_tokens += len(system_tokens)
                # st.session_state.total_input_tokens += len(system_tokens)
                # for msg in st.session_state.log:
                    # tokens = encoding.encode(msg["content"])
                    # st.session_state.input_tokens += len(tokens)
                    # st.session_state.total_input_tokens += len(tokens)
                st.session_state.state = 3
                st.rerun()
    elif st.session_state.talktime == 5: # 会話終了時
        url = "https://nagoyapsychology.qualtrics.com/jfe/form/SV_87jQ6Hj2rjLDdSm"
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
