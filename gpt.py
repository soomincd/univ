import json
import streamlit as st
from openai import OpenAI
import pandas as pd
import io
from PIL import Image
import base64

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
    st.session_state.processed_files = set()  # 처리된 파일을 추적하기 위한 세트
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
        success_files = []
        failed_files = []
        new_file_contents = []
        
        for uploaded_file in uploaded_files:
            # 이미 처리된 파일인지 확인
            file_identifier = f"{uploaded_file.name}_{uploaded_file.size}"
            if file_identifier in st.session_state.processed_files:
                continue

            try:
                if uploaded_file.size > 200 * 1024 * 1024:  # 200MB 제한
                    failed_files.append((uploaded_file.name, "파일 크기가 200MB를 초과합니다."))
                    continue

                # 파일 내용을 읽고 Base64로 인코딩
                content = uploaded_file.read()
                encoded_content = base64.b64encode(content).decode('utf-8')
                
                new_file_contents.append({
                    "name": uploaded_file.name,
                    "type": uploaded_file.type,
                    "content": encoded_content
                })
                success_files.append(uploaded_file.name)

                # 처리된 파일 추적
                st.session_state.processed_files.add(file_identifier)

            except Exception as e:
                failed_files.append((uploaded_file.name, str(e)))

        # 새로운 파일이 있는 경우에만 메시지 표시 및 내용 업데이트
        if new_file_contents:
            if failed_files:
                st.error(f"다음 파일의 처리가 실패했습니다: {', '.join(name for name, _ in failed_files)}")
            if success_files:
                st.success(f"파일 업로드가 완료되었습니다: {', '.join(success_files)}")
            
            # 새로운 파일 내용으로 업데이트
            st.session_state.file_contents = new_file_contents

# 사용자 입력
prompt = st.chat_input("메시지 ChatGPT")

if prompt:
    # OpenAI에 보낼 메시지 준비
    messages = list(st.session_state.conversation_history)  # 기존 대화 기록 복사
    
    if st.session_state.file_contents:
        # 파일 데이터를 포함한 메시지 구성
        current_message = {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt}
            ]
        }
        
        # 각 파일을 메시지에 추가
        for file in st.session_state.file_contents:
            current_message["content"].append({
                "type": "file",
                "file": file['content'],  # Base64로 인코딩된 파일 내용
                "name": file['name'],
                "mime_type": file['type']
            })
            
        messages.append(current_message)
    else:
        # 파일이 없는 경우 일반 텍스트 메시지만 추가
        messages.append({
            "role": "user",
            "content": prompt
        })
    
    # API 요청
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages
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
        
        st.session_state.conversation_history.append({
            "role": "assistant",
            "content": generated_response
        })
        
        # 파일 내용 초기화
        st.session_state.file_contents = []
        
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
