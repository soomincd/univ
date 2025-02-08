import json
import streamlit as st
from openai import OpenAI
import pandas as pd
import io
from PIL import Image
import base64
import PyPDF2
import PyPDF2

# API 클라이언트 설정
api_key = st.secrets["OPENAI_API_KEY"]
client = OpenAI(api_key=api_key)

def encode_image_to_base64(image):
    """이미지를 base64로 인코딩"""
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

def extract_text_from_pdf(pdf_file):
    """PDF에서 텍스트 추출"""
    try:
        # PDF 파일을 읽기 모드로 열기
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        
        # 모든 페이지의 텍스트 추출
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
            
        return {
            "text": text,
            "images": []  # PyPDF2는 이미지 추출을 지원하지 않습니다
        }
    except Exception as e:
        st.error(f"PDF 처리 중 오류 발생: {str(e)}")
        return None

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
    st.session_state.conversation_history = []
    # 기본 시스템 메시지 설정
    st.session_state.system_message = {
        "role": "system",
        "content": "You are a helpful assistant that can analyze both text and images. When responding to queries, provide clear and detailed observations."
    }

# 파일 업로드 처리
uploaded_files = st.file_uploader(
    "Drag and drop files here",
    type=["txt", "pdf", "xlsx", "xls", "png", "jpg", "jpeg"],
    accept_multiple_files=True,
    help="Limit 200MB per file • TXT, PDF, XLSX, XLS, PNG, JPG, JPEG"
)

if uploaded_files:
    for uploaded_file in uploaded_files:
        try:
            if uploaded_file.type in ["image/png", "image/jpeg"]:
                # 이미지 처리
                image = Image.open(uploaded_file)
                encoded_image = encode_image_to_base64(image)
                st.session_state.file_contents.append({
                    "name": uploaded_file.name,
                    "type": "image",
                    "content": encoded_image
                })
                st.image(image, caption=uploaded_file.name)
                
            elif uploaded_file.type == "application/pdf":
                # PDF 처리
                pdf_content = extract_text_from_pdf(uploaded_file)
                if pdf_content:
                    st.session_state.file_contents.append({
                        "name": uploaded_file.name,
                        "type": "pdf",
                        "content": pdf_content["text"],
                        "images": pdf_content["images"]
                    })
                    st.success(f"PDF 파일 '{uploaded_file.name}' 처리 완료")
                    
            elif uploaded_file.type in ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/vnd.ms-excel"]:
                # Excel 처리
                df = pd.read_excel(uploaded_file)
                content = df.to_csv(index=False)
                st.session_state.file_contents.append({
                    "name": uploaded_file.name,
                    "type": "excel",
                    "content": content
                })
                st.success(f"Excel 파일 '{uploaded_file.name}' 처리 완료")
                
            elif uploaded_file.type == "text/plain":
                # 텍스트 파일 처리
                content = uploaded_file.read().decode('utf-8')
                st.session_state.file_contents.append({
                    "name": uploaded_file.name,
                    "type": "text",
                    "content": content
                })
                st.success(f"텍스트 파일 '{uploaded_file.name}' 처리 완료")
                
        except Exception as e:
            st.error(f"파일 '{uploaded_file.name}' 처리 중 오류 발생: {str(e)}")

# 챗봇 입력 및 응답
prompt = st.chat_input("메시지 ChatGPT")

if prompt:
    # 사용자 메시지 표시
    st.chat_message("user").write(prompt)
    
    # GPT에 전송할 메시지 준비
    messages = st.session_state.conversation_history.copy()
    
    # 파일 내용 추가
    if st.session_state.file_contents:
        for file in st.session_state.file_contents:
            if file["type"] == "image":
                messages.append({
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"Analyzing image: {file['name']}"},
                        {"type": "image_url", "image_url": f"data:image/png;base64,{file['content']}"}
                    ]
                })
            elif file["type"] == "pdf":
                messages.append({
                    "role": "user",
                    "content": f"PDF content from {file['name']}:\n{file['content']}"
                })
                # PDF에서 추출된 이미지가 있다면 추가
                for i, img in enumerate(file.get("images", [])):
                    messages.append({
                        "role": "user",
                        "content": [
                            {"type": "text", "text": f"Image {i+1} from PDF {file['name']}:"},
                            {"type": "image_url", "image_url": f"data:image/png;base64,{img}"}
                        ]
                    })
            else:
                messages.append({
                    "role": "user",
                    "content": f"Content from {file['name']}:\n{file['content']}"
                })
    
    messages.append({"role": "user", "content": prompt})
    
    try:
        # GPT API 호출
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[st.session_state.system_message] + st.session_state.conversation_history + messages,
            max_tokens=4096
        )
        
        # 응답 표시
        response_content = response.choices[0].message.content
        st.chat_message("assistant").write(response_content)
        
        # 대화 기록 업데이트
        st.session_state.conversation_history.extend([
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": response_content}
        ])
        
        # 파일 내용 초기화
        st.session_state.file_contents = []
        
    except Exception as e:
        st.error(f"GPT 응답 처리 중 오류 발생: {str(e)}")
