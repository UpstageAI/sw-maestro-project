import streamlit as st
from utils.document_parser import parse_pdf
from utils.rag_chain import ask_question

st.set_page_config(page_title="학습 도우미 챗봇", page_icon="📚")
st.title("📚 AI 학습 도우미 챗봇")

uploaded_file = st.file_uploader("교재 PDF를 업로드하세요", type=["pdf"])

if uploaded_file:
    with st.spinner("문서를 분석하고 있습니다..."):
        documents = parse_pdf(uploaded_file)
        st.success(f"{len(documents)}개의 페이지를 분석했습니다!")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("교재에 대해 질문하세요"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            response = ask_question(prompt, documents)
            st.markdown(response)

        st.session_state.messages.append({"role": "assistant", "content": response})
