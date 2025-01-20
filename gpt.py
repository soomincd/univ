import json
import streamlit as st
from openai import OpenAI
import pandas as pd
import io
from base64 import b64decode
import re

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
if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = [
        {"role": "system", "content": "When responding, if the user wants an image to be drawn, write [0] and nothing else. If they want a text conversation without images, write [1] followed by a newline and then your response."}
    ]

# 파일 업로드 컴포넌트
uploaded_files = st.file_uploader("파일 업로드", type=["txt", "pdf", "xlsx", "xls", "png", "pptx", "ppt"], accept_multiple_files=True)

# 파일 처리 로직
if uploaded_files:
    if len(uploaded_files) > 10:
        st.error("최대 10개의 파일을 업로드할 수 있습니다.")
    else:
        file_contents = []
        for uploaded_file in uploaded_files:
            try:
                if uploaded_file.type in ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/vnd.ms-excel"]:
                    # 엑셀 파일 처리
                    df = pd.read_excel(uploaded_file)
                    content = df.to_csv(index=False)
                    file_contents.append(f"[엑셀 파일: {uploaded_file.name}]\n{content}")
                    
                elif uploaded_file.type in ["application/vnd.openxmlformats-officedocument.presentationml.presentation", "application/vnd.ms-powerpoint"]:
                    file_contents.append(f"[PPT 파일: {uploaded_file.name}이 업로드되었습니다.]")
                    
                elif uploaded_file.type == "image/png":
                    file_contents.append(f"[이미지 파일: {uploaded_file.name}이 업로드되었습니다.]")
                    
                elif uploaded_file.type == "text/plain":
                    content = uploaded_file.read().decode('utf-8')
                    file_contents.append(f"[텍스트 파일: {uploaded_file.name}]\n{content}")
                    
                elif uploaded_file.type == "application/pdf":
                    file_contents.append(f"[PDF 파일: {uploaded_file.name}이 업로드되었습니다.]")
                    
            except Exception as e:
                st.error(f"파일 '{uploaded_file.name}' 처리 중 오류가 발생했습니다: {str(e)}")
                continue

        if file_contents:
            # 파일 내용을 conversation history에 추가
            combined_content = "\n\n".join(file_contents)
            st.session_state.conversation_history.append({
                "role": "user", 
                "content": f"다음은 업로드된 파일들의 내용입니다:\n\n{combined_content}"
            })
            st.success("파일 업로드가 완료되었습니다.")

# 사용자 입력
prompt = st.chat_input("메시지 ChatGPT")

if prompt:
    # 사용자 메시지를 화면과 대화 기록에 추가
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.session_state.conversation_history.append({"role": "user", "content": prompt})

    # OpenAI API 요청
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=st.session_state.conversation_history
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
            
            # 이미지 URL을 메시지에 추가
            st.session_state.messages.append({
                "role": "assistant", 
                "content": image_response.data[0].url,
                "type": "image"
            })
            
        elif generated_response.startswith('[1]'):
            # [1] 제거 후 텍스트 응답 추가
            clean_response = generated_response[3:].strip()
            st.session_state.messages.append({
                "role": "assistant",
                "content": clean_response,
                "type": "text"
            })
        
        # 전체 응답을 대화 기록에 저장
        st.session_state.conversation_history.append({
            "role": "assistant",
            "content": generated_response
        })
        
    except Exception as e:
        st.error(f"오류가 발생했습니다: {str(e)}")

# 대화 표시
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message.get("type") == "image":
            st.image(message["content"])
        else:
            st.markdown(message["content"])
            
