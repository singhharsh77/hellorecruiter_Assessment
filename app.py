import streamlit as st
import os
import time
from router import process_query_stream
try:
    from cache_db import search_cache, save_to_cache, update_feedback
except ImportError:
    search_cache = lambda q: None
    save_to_cache = lambda q, a, m: None
    update_feedback = lambda d, s: None

st.set_page_config(page_title="HelloRecruiter Smart Router", page_icon="🤖", layout="centered")

st.title("🤖 HelloRecruiter Smart Model Router")
st.markdown("""
This tool dynamically routes your question to the most appropriate AI model based on its complexity:
- **EASY**: Handled by Local ML / Gemini Flash Lite
- **MID**: Handled by Local ML / Gemini Flash
- **TOUGH**: Handled by Gemini Pro (with Google Search Agent)
""")

if not os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY") == "your_api_key_here":
    st.warning("⚠️ Please configure your GEMINI_API_KEY in the `.env` file to use this application.")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant" and "metadata" in message:
            meta = message["metadata"]
            time_taken = message.get("time_taken", 0)
            
            # Show metadata and timer
            st.info(f"**🧠 Model Used:** {meta.get('model_name', 'Unknown')} ({meta.get('difficulty', 'Unknown')})\n\n"
                    f"**⚙️ Specs:** {meta.get('model_description', 'N/A')}\n\n"
                    f"**⚡ Compute Level:** {meta.get('compute_level', 'N/A')}\n\n"
                    f"**⏱️ Response Time:** {time_taken:.2f} seconds", icon="ℹ️")
            
            # Feedback UI
            doc_id = message.get("doc_id")
            if doc_id:
                feedback = st.feedback("thumbs", key=f"fb_{doc_id}")
                if feedback is not None:
                    score = 1 if feedback == 1 else -1
                    update_feedback(doc_id, score)

# Input field
if prompt := st.chat_input("Ask a question..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        if not os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY") == "your_api_key_here":
            st.error("API Key missing. Cannot process request.")
        else:
            start_time = time.time()
            try:
                # 1. Check semantic cache first
                cached_result = search_cache(prompt)
                
                if cached_result:
                    # Cache hit
                    st.markdown(cached_result['answer'])
                    end_time = time.time()
                    time_taken = end_time - start_time
                    doc_id = cached_result.get('doc_id')
                    metadata = cached_result
                else:
                    # Cache miss, process via stream
                    stream_generator, metadata = process_query_stream(prompt)
                    
                    # Stream the response natively
                    answer = st.write_stream(stream_generator)
                    end_time = time.time()
                    time_taken = end_time - start_time
                    
                    # Save to self-feeding database
                    metadata["answer"] = answer
                    doc_id = save_to_cache(prompt, answer, metadata)
                
                # Show metadata box for the new message
                st.info(f"**🧠 Model Used:** {metadata.get('model_name', 'Unknown')} ({metadata.get('difficulty', 'Unknown')})\n\n"
                        f"**⚙️ Specs:** {metadata.get('model_description', 'N/A')}\n\n"
                        f"**⚡ Compute Level:** {metadata.get('compute_level', 'N/A')}\n\n"
                        f"**⏱️ Response Time:** {time_taken:.2f} seconds", icon="ℹ️")
                
                # We do NOT show feedback here immediately because it gets shown on the next loop iteration from session_state
                # Wait, actually, st.write_stream renders immediately, so we should append to session state and trigger a rerun to show the feedback widget properly, OR just let the user see it on next message.
                # It's better to just append and rely on Streamlit's natural flow.
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": cached_result['answer'] if cached_result else answer,
                    "metadata": metadata,
                    "time_taken": time_taken,
                    "doc_id": doc_id
                })
                
                # Force rerun to show the feedback widget at the bottom of the loop
                st.rerun()

            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
