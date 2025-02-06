import json
import streamlit as st
from openai import OpenAI
import pandas as pd
import io
from base64 import b64encode
import re

# API 클라이언트 설정
if "OPENAI_API_KEY" not in st.session_state:
    st.session_state.OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY", None)

if not st.session_state.OPENAI_API_KEY:
    st.session_state.OPENAI_API_KEY = st.text_input("OpenAI API 키를 입력하세요:", type="password")
    if not st.session_state.OPENAI_API_KEY:
        st.stop()

client = OpenAI(api_key=st.session_state.OPENAI_API_KEY)

# 페이지 설정
st.set_page_config(
    page_title="EdMakers Code page",
    page_icon="favicon.png",
)

# CSS 스타일 추가
st.markdown("""
    <style>
        .container {
            position: relative;
            padding-top: 1rem;
        }
        .header-container {
            text-align: center;
            margin-bottom: 1rem;
            position: relative;
        }
        .back-link {
            position: absolute;
            left: 1rem;
            top: 50%;
            transform: translateY(-50%);
            color: #666 !important;
            text-decoration: none !important;
            font-size: 0.9rem;
            display: inline-flex;
            align-items: center;
            gap: 5px;
            z-index: 1;
        }
        .back-link:hover {
            color: #333 !important;
        }
        .title {
            margin: 0 auto;
            color: black;
            display: inline-block;
        }
        .stApp {
            margin-top: -6rem;
        }
        .uploadedFile {
            display: flex;
            align-items: center;
            background-color: #f0f2f6;
            padding: 4px 8px;
            border-radius: 4px;
            margin: 2px 0;
        }
    </style>
""", unsafe_allow_html=True)

# Font Awesome 추가
st.markdown("""
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
""", unsafe_allow_html=True)

# 헤더 컨테이너 (제목과 뒤로가기 버튼)
st.markdown("""
    <div class="container">
        <div class="header-container">
            <a href="http://edmakersmp.dothome.co.kr/kcuemain.php" class="back-link">
                <i class="fas fa-arrow-left"></i> 목록으로
            </a>
            <h2 class="title">Chat GPT</h2>
        </div>
    </div>
""", unsafe_allow_html=True)

st.markdown("""
    <p style="text-align: center"> 이 페이지는 ChatGPT-4o버전을 사용하고 있습니다. </p>
""", unsafe_allow_html=True)

# 세션 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []
if "file_contents" not in st.session_state:
    st.session_state.file_contents = []
if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = [
        {"role": "system", "content": "When responding, if the user wants an image to be drawn, write [0] and nothing else. If they want a text conversation without images, write [1] followed by a newline and then your response."}
    ]
if "pending_file_contents" not in st.session_state:
    st.session_state.pending_file_contents = []
if "show_file_uploader" not in st.session_state:
    st.session_state.show_file_uploader = True

# 파일 업로드 컴포넌트
if st.session_state.show_file_uploader:
    uploaded_files = st.file_uploader(
        "Drag and drop files here",
        type=["txt", "xlsx", "xls", "png", "pptx", "ppt"],
        accept_multiple_files=True
    )

    # 파일 내용 처리 및 임시 저장
    if uploaded_files:
        if len(uploaded_files) > 10:
            st.error("최대 10개의 파일을 업로드할 수 있습니다.")
        else:
            st.session_state.pending_file_contents = []
            for uploaded_file in uploaded_files:
                try:
                    if uploaded_file.type in ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/vnd.ms-excel"]:
                        df = pd.read_excel(uploaded_file)
                        content = df.to_csv(index=False)
                        st.session_state.pending_file_contents.append(f"[엑셀 내용]\n{content}")
                    elif uploaded_file.type in ["application/vnd.openxmlformats-officedocument.presentationml.presentation", "application/vnd.ms-powerpoint"]:
                        st.session_state.pending_file_contents.append("PPT 파일이 업로드되었습니다.")
                    elif uploaded_file.type == "image/png":
                        # 이미지를 base64로 인코딩
                        bytes_data = uploaded_file.getvalue()
                        base64_image = b64encode(bytes_data).decode()
                        st.session_state.pending_file_contents.append(f"[이미지 내용]\ndata:image/png;base64,{base64_image}")
                        # 이미지 미리보기 표시
                        st.image(bytes_data, caption="업로드된 이미지")
                    elif uploaded_file.type == "text/plain":
                        content = uploaded_file.read().decode('utf-8')
                        st.session_state.pending_file_contents.append(f"[텍스트 내용]\n{content}")
                except Exception as e:
                    st.error(f"파일 처리 중 오류가 발생했습니다: {str(e)}")
            
            st.success("파일이 준비되었습니다. 메시지를 입력하거나 엔터를 눌러주세요.")

# 사용자 입력
prompt = st.chat_input("메시지 ChatGPT")

if prompt is not None:  # 엔터만 눌러도 처리되도록 수정
    # 파일 내용이 있다면 대화 기록에 추가
    if st.session_state.pending_file_contents:
        for content in st.session_state.pending_file_contents:
            st.session_state.conversation_history.append({"role": "user", "content": content})
        st.session_state.pending_file_contents = []  # 처리 후 초기화
        st.session_state.show_file_uploader = False  # 파일 업로더 숨기기
        st.rerun()  # UI 새로고침

    # 사용자 메시지 추가
    if prompt:  # 실제 메시지가 있는 경우만 표시
        st.session_state.messages.append({"role": "user", "content": prompt})
    st.session_state.conversation_history.append({"role": "user", "content": prompt if prompt else "파일을 분석해주세요."})

    # OpenAI API 요청
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=st.session_state.conversation_history
        )
        generated_response = response.choices[0].message.content

        # [0]/[1] 체크 및 처리
        if generated_response.startswith('[0]'):
            # DALL-E 3로 이미지 생성
            image_response = client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1024x1024",
                quality="standard",
                n=1,
            )
            
            # 이미지 URL을 메시지에 추가
            st.session_state.messages.append({
                "role": "assistant", 
                "content": image_response.data[0].url,
                "type": "image"
            })
            
        elif generated_response.startswith('[1]'):
            # [1] 제거 후 텍스트 응답 추가
            clean_response = generated_response[3:].strip()  # [1]\n 제거
            st.session_state.messages.append({
                "role": "assistant",
                "content": clean_response,
                "type": "text"
            })
            
        # conversation_history에는 원본 응답 저장
        st.session_state.conversation_history.append({
            "role": "assistant",
            "content": generated_response
        })
        
        # 응답 후 파일 업로더 다시 표시
        st.session_state.show_file_uploader = True
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
