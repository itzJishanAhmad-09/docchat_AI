import streamlit as st
import requests

API_URL = "https://docchat-ai-backend-ifp9.onrender.com"

st.set_page_config(page_title="DocChat AI", page_icon="📄")
st.title("📄 DocChat AI")
st.markdown("Upload a PDF and chat with it using RAG.")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "document_id" not in st.session_state:
    st.session_state.document_id = None

with st.sidebar:
    st.header("Upload Document")
    uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")

    if uploaded_file is not None:
        if st.button("Process PDF"):
            with st.spinner("Processing and embedding PDF..."):
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
                response = requests.post(f"{API_URL}/upload", files=files)

                if response.status_code == 200:
                    data = response.json()
                    st.session_state.document_id = data["document_id"]
                    st.session_state.messages = []
                    st.success(f"Processed! Document ID: {data['document_id']}")
                else:
                    st.error(f"Error: {response.text}")

if st.session_state.document_id is None:
    st.info("👈 Please upload and process a PDF to start chatting.")
else:
    st.success(f"Chatting with Document ID: {st.session_state.document_id}")

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if "sources" in message:
                with st.expander("View Sources"):
                    for i, source in enumerate(message["sources"]):
                        st.caption(f"**Source {i+1}:** {source[:200]}...")

    if prompt := st.chat_input("Ask a question about your document..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                payload = {"question": prompt, "document_id": st.session_state.document_id}
                response = requests.post(f"{API_URL}/chat", json=payload)

                if response.status_code == 200:
                    data = response.json()
                    st.markdown(data["answer"])

                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": data["answer"],
                        "sources": data["sources"]
                    })
                else:
                    st.error(f"Error: {response.text}")