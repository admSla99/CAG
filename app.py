# Main application file for the CAG Chat System
import streamlit as st
from document_processor import extract_text_from_file
import google.generativeai as genai
# Caching module removed as it's not supported by the target model
import os
from dotenv import load_dotenv
# Initialize session state variables if they don't exist
if "messages" not in st.session_state:
    st.session_state.messages = []
if "document_content" not in st.session_state:
    st.session_state.document_content = None
if "uploaded_file_name" not in st.session_state:
    st.session_state.uploaded_file_name = None
# Removed document_cache from session state
if "document_token_count" not in st.session_state:
    st.session_state.document_token_count = 0
# --- API Key Configuration ---
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    st.error("🚨 Google API Key not found! Please set the GOOGLE_API_KEY environment variable in your .env file.")
    # You might want to stop the app execution here if the key is critical
    # st.stop()
else:
    try:
        genai.configure(api_key=api_key)
        # Optional: Check if the key is valid by listing models, but this adds an API call
        # models = genai.list_models() # Uncomment to verify key early
        st.sidebar.success("API Key configured successfully!")
    except Exception as e:
        st.error(f"🚨 Error configuring Google AI SDK: {e}")
        # st.stop()
# --- Model Initialization ---
# Instantiate the model once if the API key is valid
model = None
model_name = "models/gemini-2.5-pro-exp-03-25" # Use suggested experimental model
if api_key:
    try:
        model = genai.GenerativeModel(model_name=model_name)
    except Exception as e:
        st.error(f"🚨 Error initializing Gemini model: {e}")
        model = None # Ensure model is None if init fails

# --- Constants ---
CONTEXT_WINDOW_LIMIT = 1_000_000 # Based on Gemini 2.5 Pro documentation

# --- App Title ---
st.title("📄 Chat with your Document (CAG)")

# --- Helper Function for LLM Call ---
# --- Helper Function for LLM Call ---
def generate_response(user_prompt, document_text, chat_history):
    """
    Generates response using Gemini, sending document text and chat history.
    """
    if not api_key: # Should be checked before calling, but double-check
        return "Error: API Key not configured."

    # model_name is now defined globally

    # --- Task 6.4: Pre-API Token Check & History Truncation ---
    if not model: # Check if model is initialized
         return "Error: Model not initialized."
    if not document_text:
         return "Error: No document content available."

    # Try generating prompt with decreasing history length if needed
    history_limit = 8 # Start with max desired history (4 pairs)
    while history_limit >= 0:
        try:
            # --- Format Chat History ---
            recent_history = chat_history[-history_limit:]
            formatted_history = "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" for msg in recent_history])

            # --- Construct Full Prompt ---
            full_prompt = (
                f"Chat History:\n---\n{formatted_history}\n---\n\n"
                f"Document Content:\n---\n{document_text}\n---\n\n"
                f"User Question: {user_prompt}"
            )

            # --- Count Tokens for the Combined Prompt ---
            # Use a spinner here as counting can take a moment for large prompts
            with st.spinner(f"Checking prompt size (history={history_limit} msgs)..."):
                 prompt_token_count = model.count_tokens(full_prompt).total_tokens

            if prompt_token_count <= CONTEXT_WINDOW_LIMIT:
                # Prompt fits, generate content
                st.info(f"Prompt size ({prompt_token_count:,} tokens) fits within limit. Generating response...")
                response = model.generate_content(full_prompt)
                # Check for safety ratings or blocked responses if needed
                # if not response.candidates: return "Error: Response blocked or empty."
                return response.text
            else:
                # Prompt too large, try reducing history
                if history_limit > 0:
                    st.warning(f"Combined prompt ({prompt_token_count:,} tokens) exceeds limit. Reducing chat history (trying {history_limit-2} messages)...")
                    history_limit -= 2 # Reduce by one user/assistant pair
                else:
                    # History is already 0, still too large (document + query issue)
                    st.error(f"🚨 Combined prompt ({prompt_token_count:,} tokens) exceeds limit even with no chat history. Cannot generate response.")
                    return f"Error: Prompt exceeds token limit ({prompt_token_count:,} / {CONTEXT_WINDOW_LIMIT:,}) even without history."

        except Exception as e:
            # Handle potential errors during token counting or generation within the loop
            st.error(f"🚨 Error during prompt construction/check (history={history_limit}): {e}")
            return f"Error during processing (history={history_limit}): {e}"

    # Should not be reached if logic is correct, but as a fallback
    return "Error: Failed to generate response after checking prompt size."
    # Removed incorrect else/except block from previous structure

# --- App Title --- (Removed duplicate already)

uploaded_file = st.file_uploader(
    "Upload your document (.txt, .pdf, .docx)",
    type=["txt", "pdf", "docx"]
)

# Check if a new file has been uploaded
new_upload = False
if uploaded_file is not None:
    if uploaded_file.name != st.session_state.uploaded_file_name:
        new_upload = True
        st.session_state.uploaded_file_name = uploaded_file.name
        # Clear previous content and chat history on new upload
        st.session_state.document_content = None
        st.session_state.messages = []
        st.session_state.document_token_count = 0 # Reset token count
        st.info(f"Processing '{uploaded_file.name}'...")
        with st.spinner(f"Extracting text from '{uploaded_file.name}'..."):
            extracted_text = extract_text_from_file(uploaded_file)
            if extracted_text is not None:
                # --- Token Counting and Context Window Check ---
                if model: # Only count tokens if model initialized successfully
                    try:
                        with st.spinner("Counting document tokens..."):
                            token_count = model.count_tokens(extracted_text).total_tokens
                        st.session_state.document_token_count = token_count

                        if token_count > CONTEXT_WINDOW_LIMIT:
                            st.error(f"🚨 Document '{uploaded_file.name}' is too large ({token_count:,} tokens). Exceeds the model's limit of {CONTEXT_WINDOW_LIMIT:,} tokens. Cannot process.")
                            st.session_state.document_content = None # Prevent chat
                            st.session_state.uploaded_file_name = None # Allow re-upload
                            st.session_state.document_token_count = 0
                        else:
                            # Document size is acceptable
                            st.session_state.document_content = extracted_text # Store the text
                            st.success(f"Document '{uploaded_file.name}' processed successfully.")
                            # Display token count info (Task 5.4) - will add below
                    except Exception as e:
                        st.error(f"🚨 Error counting tokens: {e}")
                        st.session_state.document_content = None # Prevent chat on error
                        st.session_state.uploaded_file_name = None
                        st.session_state.document_token_count = 0
                else:
                    st.error("🚨 Cannot process document: Gemini model not initialized (check API key and configuration).")
                    st.session_state.document_content = None
                    st.session_state.uploaded_file_name = None
                    st.session_state.document_token_count = 0

            else:
                # Error message is handled within extract_text_from_file
                st.session_state.uploaded_file_name = None # Reset on error
                # Removed document_cache assignment

# Only show chat interface if document content exists
# Display token count info and chat interface if document is loaded and valid
if st.session_state.document_content is not None and st.session_state.document_token_count > 0:
    # --- Display Token Count Info (Task 5.4) ---
    st.info(f"**Document:** {st.session_state.uploaded_file_name}\n**Tokens:** {st.session_state.document_token_count:,} / {CONTEXT_WINDOW_LIMIT:,}")
    # Optional: Progress bar
    progress_value = min(st.session_state.document_token_count / CONTEXT_WINDOW_LIMIT, 1.0)
    st.progress(progress_value)

    # Display existing chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input field
    if prompt := st.chat_input("Ask something about the document..."):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        # Display user message in chat message container
        with st.chat_message("user"):
            st.markdown(prompt)

        # --- LLM Call (Task 3.3) ---
        # Check if API key is available before attempting call
        if not api_key or not model:
            st.error("🚨 Cannot generate response. API Key or Model not configured/initialized.")
        # Removed cache check block
        elif st.session_state.document_content:
             # Placeholder: Handle case where cache failed but content exists (maybe warn user?)
             # For now, just show a placeholder indicating no cache is used.
             # Always use document content now
             with st.chat_message("assistant"):
                 with st.spinner("Generating response..."):
                    # Removed warning about cache
                    response = generate_response(
                        prompt,
                        document_text=st.session_state.document_content,
                        chat_history=st.session_state.messages # Pass history
                    )
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
        else:
             # This case should ideally not be reached if the outer condition holds
             st.error("🚨 Internal error: Document content missing.")

elif not uploaded_file: # Show initial message only if no file is selected
    st.info("Please upload a document (.txt, .pdf, .docx) to start chatting.")