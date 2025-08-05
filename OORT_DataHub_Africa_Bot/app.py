import streamlit as st
import os
import sys
import threading
import time

KB_FILE = "oort_faq.md"

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Import the necessary modules
from src.voice_input import VoiceInput
from src.voice_output import VoiceOutput
from src.kb_loader import KnowledgeBase

# Set page configuration
st.set_page_config(
    page_title="OORT Africa Assistant",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state variables if they don't exist
if 'messages' not in st.session_state:
    st.session_state.messages = []

if 'recording' not in st.session_state:
    st.session_state.recording = False

if 'language' not in st.session_state:
    st.session_state.language = "english"
    
if 'last_voice_input' not in st.session_state:
    st.session_state.last_voice_input = None

# Initialize the knowledge base
@st.cache_resource
def load_knowledge_base():
    return KnowledgeBase()

kb = load_knowledge_base()

# Initialize voice components
@st.cache_resource
def load_voice_components():
    voice_input = VoiceInput()
    voice_output = VoiceOutput()
    return voice_input, voice_output

voice_input, voice_output = load_voice_components()

# Function to handle voice recording
def toggle_recording():
    if st.session_state.recording:
        st.session_state.recording = False
        return
    
    st.session_state.recording = True
    
    # Start recording in a separate thread
    threading.Thread(target=record_audio).start()

def record_audio():
    # Check if voice input is ready
    if not voice_input.is_ready():
        st.error("Voice input is not available. Please check if the speech recognition models are properly installed.")
        st.session_state.recording = False
        st.rerun()  # This is the correct usage of st.rerun()
        return
    
    try:
        with st.spinner("Listening..."):
            # Set a reasonable timeout
            text = voice_input.listen(language=st.session_state.language, timeout=15)
            
            if text:
                st.success(f"Recognized: {text}")
                # Store the recognized text in session state to process it after rerun
                st.session_state.last_voice_input = text
            else:
                st.warning("I didn't hear anything. Please try speaking again.")
    except Exception as e:
        st.error(f"Error during voice recognition: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        # Ensure recording state is reset
        st.session_state.recording = False
        st.rerun()

# Function to process user input and generate response
def process_input(user_input):
    # Check if input is empty or just whitespace
    if not user_input or user_input.isspace():
        return
        
    # Check if this is a duplicate input (to prevent processing the same input multiple times)
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "user" and st.session_state.messages[-1]["content"] == user_input:
        return
    
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    # Get response from knowledge base
    response = kb.query(user_input, language=st.session_state.language)
    
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": response})
    
    # Generate speech for the response
    threading.Thread(target=voice_output.speak, args=(response, st.session_state.language)).start()

# Main UI
def main():
    # Sidebar for settings
    with st.sidebar:
        st.title("OORT DH Africa Assistant")
        # Use local SVG file instead of external placeholder
        st.image("oort_logo.svg", width=150)
        
        # Language selection
        language_options = {
            "English": "english",
            "French": "french",
            "Arabic": "arabic",
            "Swahili": "swahili"
        }
        
        selected_language = st.selectbox(
            "Select Language",
            options=list(language_options.keys()),
            index=list(language_options.keys()).index(next(key for key, value in language_options.items() if value == st.session_state.language))
        )
        
        if language_options[selected_language] != st.session_state.language:
            st.session_state.language = language_options[selected_language]
            st.rerun()
        
        st.divider()
        
        # About section
        st.subheader("About")
        st.write(
            "OORT Africa Assistant is a multilingual voice assistant that provides information "
            "about OORT DataHub Africa program. It works 100% offline without requiring any "
            "cloud services or API keys."
        )
        
        st.divider()
        
        # System status
        st.subheader("System Status")
        
        # Check voice input status
        voice_input_status = voice_input.is_ready()
        voice_input_color = "green" if voice_input_status else "red"
        st.markdown(f"<span style='color:{voice_input_color}'>🎙️ Voice Input: {'Active' if voice_input_status else 'Not Available'}</span>", unsafe_allow_html=True)
        
        # Check voice output status
        voice_output_status = voice_output.is_ready()
        voice_output_color = "green" if voice_output_status else "red"
        st.markdown(f"<span style='color:{voice_output_color}'>🔊 Voice Output: {'Active' if voice_output_status else 'Not Available'}</span>", unsafe_allow_html=True)
        
        # Check knowledge base status
        kb_status = kb.is_ready()
        kb_color = "green" if kb_status else "red"
        st.markdown(f"<span style='color:{kb_color}'>🧠 Knowledge Base: {'Loaded' if kb_status else 'Not Available'}</span>", unsafe_allow_html=True)
        
        # Add debug information if components are not available
        if not (voice_input_status and voice_output_status and kb_status):
            with st.expander("Troubleshooting Information"):
                if not voice_input_status:
                    st.write("Voice Input Issue: Check if Vosk models are properly installed in the models/stt directory.")
                if not voice_output_status:
                    st.write("Voice Output Issue: Check if TTS models are properly installed in the models/tts directory.")
                if not kb_status:
                    st.write("Knowledge Base Issue: Check if the vector database was created properly in the db directory.")
    
    # Main content area
    st.title("OORT Africa Assistant")
    
    # Process voice input if available from previous run
    if st.session_state.last_voice_input:
        voice_text = st.session_state.last_voice_input
        st.session_state.last_voice_input = None  # Clear it to prevent reprocessing
        process_input(voice_text)
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
    
    # Chat input
    user_input = st.chat_input("Ask a question about OORT DataHub Africa...")
    if user_input:
        process_input(user_input)
        st.rerun()
    
    # Voice input button
    col1, col2 = st.columns([1, 5])
    with col1:
        mic_button = st.button(
            "🎤", 
            key="mic_button",
            on_click=toggle_recording,
            disabled=st.session_state.recording
        )
    
    with col2:
        if st.session_state.recording:
            st.write("Listening...")

if __name__ == "__main__":
    main()