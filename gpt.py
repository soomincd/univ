import json
import streamlit as st
from openai import OpenAI
import pandas as pd
import io
from PIL import Image
import pdfplumber

# API 클라이언트 설정
api_key = st.secrets["OPENAI_API_KEY"]
client = OpenAI(api_key=api_key)

# 페이지 설정
st.set_page_config(
    page_title="EdMakers Code page",
    page_icon="favicon.png",
)

# 페이지 설명
st.markdown("""
    <h2 style="color: black; text-align: center;"> Chat GPT </h2>
    <p style="text-align: justify; text-align: center"> 이 페이지는 ChatGPT-4o-mini 버전을 사용하고 있습니다. </p>
""", unsafe_allow_html=True)

# 세션 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []
if "file_contents" not in st.session_state:
    st.session_state.file_contents = []
if "processed_files" not in st.session_state:
    st.session_state.processed_files = set()
if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = [
        {"role": "system", "content": "When responding, if the user wants an image to be drawn, write [0] and nothing else. If they want a text conversation without images, write [1] followed by a newline and then your response."}
    ]

# 파일 아이콘 스타일 정의
st.markdown("""
    <style>
        .file-icon {
            display: inline-flex;
            align-items: center;
            background-color: #f0f2f6;
            padding: 4px 8px;
            border-radius: 4px;
            margin: 2px 0;
        }
        .file-icon i {
            margin-right: 6px;
        }
        .chat-message {
            margin-bottom: 10px;
        }
        .file-list {
            margin-top: 8px;
        }
    </style>
""", unsafe_allow_html=True)

# 파일 업로드 컴포넌트
uploaded_files = st.file_uploader(
    "Drag and drop files here",
    type=["txt", "pdf", "xlsx", "xls", "png", "pptx", "ppt"],
    accept_multiple_files=True,
    help="Limit 200MB per file • TXT, PDF, XLSX, XLS, PNG, PPTX, PPT"
)

# 파일 처리 로직
if uploaded_files:
    if len(uploaded_files) > 10:
        st.error("최대 10개의 파일을 업로드할 수 있습니다.")
    else:
        for uploaded_file in uploaded_files:
            file_identifier = f"{uploaded_file.name}_{uploaded_file.size}"
            if file_identifier not in st.session_state.processed_files:
                try:
                    if uploaded_file.type == "application/pdf":
                        with pdfplumber.open(uploaded_file) as pdf:
                            content = ""
                            for page in pdf.pages:
                                content += page.extract_text() + "\n"
                            
                            # PDF 내용을 conversation_history에 텍스트로 저장
                            st.session_state.conversation_history.append({
                                "role": "system",
                                "content": f"PDF Content from {uploaded_file.name}:\n{content}"
                            })
                            
                            st.session_state.processed_files.add(file_identifier)
                            st.success(f"파일이 처리되었습니다: {uploaded_file.name}")
                            
                except Exception as e:
                    st.error(f"파일 처리 중 오류가 발생했습니다: {str(e)}")
        
        # 파일 컨텐츠 초기화
        st.session_state.file_contents = []
        # UI 초기화
        st.rerun()

# 사용자 입력
prompt = st.chat_input("메시지 ChatGPT")

if prompt:
    # 메시지 표시
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # OpenAI에 보낼 메시지 준비
    full_prompt = f"Question: {prompt}"

    # 히스토리 추가
    if len(st.session_state.conversation_history) > 1:  # 시스템 메시지 제외하고 히스토리가 있다면
        history_content = "\n".join([
            f"Q: {msg['content']}" if msg['role'] == 'user' else 
            f"A: {msg['content'][3:]}" if msg['role'] == 'assistant' and msg['content'].startswith('[1]') else 
            "A: Image was generated" if msg['role'] == 'assistant' else
            f"{msg['content']}"  # PDF 내용 포함
            for msg in st.session_state.conversation_history[1:]
        ])
        full_prompt += f"\n\nHistory:\n{history_content}"
    
    # OpenAI API 요청
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "When responding, if the user wants an image to be drawn, write [0] and nothing else. If they want a text conversation without images, write [1] followed by a newline and then your response."},
                {"role": "user", "content": full_prompt}
            ]
        )
        generated_response = response.choices[0].message.content

        # [0]/[1] 응답 처리
        if generated_response.startswith('[0]'):
            # DALL-E 3로 이미지 생성
            image_response = client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1024x1024",
                quality="standard",
                n=1,
            )
            
            st.session_state.messages.append({
                "role": "assistant", 
                "content": image_response.data[0].url,
                "type": "image"
            })
            
        elif generated_response.startswith('[1]'):
            clean_response = generated_response[3:].strip()
            st.session_state.messages.append({
                "role": "assistant",
                "content": clean_response,
                "type": "text"
            })
        
        st.session_state.conversation_history.append({"role": "user", "content": prompt})
        st.session_state.conversation_history.append({"role": "assistant", "content": generated_response})
        
        # 화면 새로고침
        st.rerun()
        
    except Exception as e:
        st.error(f"오류가 발생했습니다: {str(e)}")

# 대화 표시
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message.get("type") == "image":
            st.image(message["content"])
        else:
            st.markdown(message["content"])
