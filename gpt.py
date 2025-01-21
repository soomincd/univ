import json
import streamlit as st
from openai import OpenAI
import pandas as pd
import io
from PIL import Image

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
if "files_processed" not in st.session_state:
    st.session_state.files_processed = False

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
    help="Limit 200MB per file • TXT, PDF, XLSX, XLS, PNG, PPTX, PPT",
    key="file_uploader"
)

def process_files():
    """파일 처리 함수"""
    if len(uploaded_files) > 10:
        st.error("최대 10개의 파일을 업로드할 수 있습니다.")
        return False

    success_files = []
    failed_files = []
    file_contents = []
    
    for uploaded_file in uploaded_files:
        try:
            if uploaded_file.size > 200 * 1024 * 1024:  # 200MB 제한
                failed_files.append((uploaded_file.name, "파일 크기가 200MB를 초과합니다."))
                continue

            if uploaded_file.type in ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/vnd.ms-excel"]:
                df = pd.read_excel(uploaded_file, engine='openpyxl')
                content = df.to_csv(index=False)
                file_contents.append({
                    "name": uploaded_file.name,
                    "type": "excel",
                    "content": content
                })
                success_files.append(uploaded_file.name)
                
            elif uploaded_file.type == "image/png":
                image = Image.open(uploaded_file)
                file_contents.append({
                    "name": uploaded_file.name,
                    "type": "image",
                    "content": "이미지 파일이 처리되었습니다."
                })
                success_files.append(uploaded_file.name)
                
            elif uploaded_file.type == "text/plain":
                content = uploaded_file.read().decode('utf-8')
                file_contents.append({
                    "name": uploaded_file.name,
                    "type": "text",
                    "content": content
                })
                success_files.append(uploaded_file.name)
                
            else:
                success_files.append(uploaded_file.name)
                file_contents.append({
                    "name": uploaded_file.name,
                    "type": "other",
                    "content": f"{uploaded_file.type} 파일이 업로드되었습니다."
                })

        except Exception as e:
            failed_files.append((uploaded_file.name, str(e)))

    if file_contents:
        st.session_state.file_contents = file_contents
        
    # 결과 메시지 표시
    if failed_files:
        st.error(f"다음 파일의 처리가 실패했습니다: {', '.join(name for name, _ in failed_files)}")
    if success_files:
        st.success("파일 업로드가 완료되었습니다.")
        return True
    return False

# 파일 처리
if uploaded_files and not st.session_state.files_processed:
    if process_files():
        st.session_state.files_processed = True
        st.rerun()

# 파일이 처리되었고 새로운 업로드가 없는 경우 초기화
if not uploaded_files and st.session_state.files_processed:
    st.session_state.files_processed = False

# 사용자 입력
prompt = st.chat_input("메시지 ChatGPT")

if prompt:
    # 메시지와 파일 정보를 함께 표시
    file_info = ""
    if st.session_state.file_contents:
        files_list = [f"📎 {file['name']}" for file in st.session_state.file_contents]
        file_info = "\n".join(files_list)
        display_message = f"{prompt}\n\n{file_info}"
    else:
        display_message = prompt

    st.session_state.messages.append({"role": "user", "content": display_message})
    
    # OpenAI에 보낼 메시지 준비
    if st.session_state.file_contents:
        combined_content = "\n\n".join([
            f"[파일: {file['name']}]\n{file['content']}"
            for file in st.session_state.file_contents
        ])
        full_prompt = f"{prompt}\n\n첨부된 파일 내용:\n{combined_content}"
    else:
        full_prompt = prompt

    st.session_state.conversation_history.append({"role": "user", "content": full_prompt})
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=st.session_state.conversation_history
        )
        generated_response = response.choices[0].message.content

        if generated_response.startswith('[0]'):
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
        
    except Exception as e:
        st.error(f"오류가 발생했습니다: {str(e)}")

# 대화 표시
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message.get("type") == "image":
            st.image(message["content"])
        else:
            st.markdown(message["content"])
