import streamlit as st
import os
from dotenv import load_dotenv
import google.generativeai as genai
from PIL import Image
import io

# Load environment variables
load_dotenv()

# Configure Gemini with API Key
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Streamlit app setup
st.set_page_config(page_title="Visual Health Assistant - Chat with Images", layout="wide")

st.title("📷 Visual Health & Nutrition Assistant")
st.markdown("Upload any food, meal, nutrition label, or health image to get detailed calorie breakdowns and chat interactively with **MR. Bittu**.")

# Initialize session state
if "image_chat_history" not in st.session_state:
    st.session_state.image_chat_history = []
if "active_image_name" not in st.session_state:
    st.session_state.active_image_name = None
if "active_image_data" not in st.session_state:
    st.session_state.active_image_data = None

# Base prompt template
nutritionist_prompt = """
Your name is **MR. Bittu**.
You are an expert nutritionist and visual health advisor.
Your task is to analyze the provided image of food items or health-related images (like prescription labels, medical scans, or physical indicators) and provide clear, accurate, and actionable information.

Instructions:
1. If the image depicts Food or Meals:
   - Identify each distinct item.
   - Provide an estimated calorie count for each item.
   - Provide the Total Calorie Count.
   - Mention key macronutrients (proteins, carbs, fats) and practical dietary tips.
2. If the image depicts Health/Medical Items (prescription, report, X-ray, symptom):
   - Summarize what is visible with medical prudence.
   - Provide helpful health implications and always advise consulting a qualified physician.
3. Answer follow-up questions contextually, referring back to the image and prior conversation.
4. Keep explanations concise, clear, and encouraging.
"""

def optimize_image(uploaded_file, max_dimension=1280):
    """Downscale large phone photos to reduce network transfer latency while keeping crisp details."""
    image = Image.open(uploaded_file)
    if image.mode != "RGB":
        image = image.convert("RGB")
    
    width, height = image.size
    if max(width, height) > max_dimension:
        scale = max_dimension / max(width, height)
        image = image.resize((int(width * scale), int(height * scale)), Image.Resampling.LANCZOS)
    
    buf = io.BytesIO()
    image.save(buf, format="JPEG", quality=85, optimize=True)
    return {
        "mime_type": "image/jpeg",
        "data": buf.getvalue()
    }

def stream_gemini_reply(user_query, image_part, history):
    """Stream Gemini response tokens for near-instant responses."""
    try:
        # Use fast, low-latency flash-lite model
        model = genai.GenerativeModel('gemini-3.5-flash-lite')
        
        # Format conversation context (last 6 messages to keep it focused and fast)
        history_str = ""
        for msg in history[-6:]:
            history_str += f"{msg['role'].upper()}: {msg['content']}\n\n"
            
        full_query = f"""{nutritionist_prompt}

---
CONVERSATION HISTORY:
{history_str}
---
CURRENT USER QUESTION:
{user_query}
"""
        response_stream = model.generate_content([full_query, image_part], stream=True)
        for chunk in response_stream:
            if chunk.text:
                yield chunk.text
    except Exception as e:
        yield f"⚠️ Error communicating with Gemini: {str(e)}"

# Layout: 2 Columns (Left: Image & Controls, Right: Chat Interface)
col1, col2 = st.columns([0.4, 0.6], gap="medium")

with col1:
    st.subheader("1. Upload Image")
    uploaded_file = st.file_uploader("Choose a photo (JPG, JPEG, PNG)...", type=["jpg", "jpeg", "png"])
    
    if uploaded_file is not None:
        # Check if a new file is uploaded
        if st.session_state.active_image_name != uploaded_file.name:
            st.session_state.active_image_name = uploaded_file.name
            with st.spinner("Optimizing image for fast upload..."):
                st.session_state.active_image_data = optimize_image(uploaded_file)
            st.session_state.image_chat_history = []
        
        # Display image
        image = Image.open(io.BytesIO(st.session_state.active_image_data["data"]))
        st.image(image, caption=f"Uploaded: {uploaded_file.name}", use_container_width=True)
        
        # Quick action button for full breakdown
        if st.button("⚡ Run Full Calorie & Health Breakdown", use_container_width=True):
            initial_query = "Please provide a complete breakdown of all items in this image, including estimated calories, macronutrients, and health recommendations."
            st.session_state.image_chat_history.append({"role": "user", "content": initial_query})
            st.rerun()

    if st.session_state.image_chat_history:
        if st.button("🗑️ Clear Chat History", use_container_width=True):
            st.session_state.image_chat_history = []
            st.rerun()

with col2:
    st.subheader("2. Interactive Advisory Chat")
    
    # Display message history
    if not st.session_state.image_chat_history:
        if uploaded_file is None:
            st.info("👈 Upload an image on the left to start analyzing and chatting!")
        else:
            st.info("💡 Image uploaded! Click the breakdown button on the left or ask any question below.")
    else:
        chat_container = st.container()
        with chat_container:
            for msg in st.session_state.image_chat_history:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
    
    # If the last message was from the user and needs a response:
    if st.session_state.image_chat_history and st.session_state.image_chat_history[-1]["role"] == "user":
        last_user_query = st.session_state.image_chat_history[-1]["content"]
        with st.chat_message("assistant"):
            reply = st.write_stream(
                stream_gemini_reply(
                    last_user_query,
                    st.session_state.active_image_data,
                    st.session_state.image_chat_history[:-1]
                )
            )
        st.session_state.image_chat_history.append({"role": "assistant", "content": reply})

    # User input chatbox for initial or follow-up questions
    if user_message := st.chat_input("Ask MR. Bittu any question or follow-up about this image..."):
        if st.session_state.active_image_data is None:
            st.warning("Please upload an image first!")
        else:
            st.session_state.image_chat_history.append({"role": "user", "content": user_message})
            st.rerun()
