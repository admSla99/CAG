# Main application file for the CAG Chat System
import streamlit as st
from document_processor import extract_text_from_file
from prompt_utils import load_prompts # Import prompt loading function
import google.generativeai as genai
import os
from dotenv import load_dotenv
from streamlit_local_storage import LocalStorage # Import local storage
import time # For sleep before rerun

# --- Page Config ---
# Set page config only once, preferably at the top
st.set_page_config(page_title="CAG Chat", page_icon="📄")

# --- Initialize Session State ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "document_content" not in st.session_state:
    st.session_state.document_content = None
if "uploaded_file_name" not in st.session_state:
    st.session_state.uploaded_file_name = None
if "processed_file_id" not in st.session_state: # Track processed file ID
    st.session_state.processed_file_id = None
if "document_token_count" not in st.session_state:
    st.session_state.document_token_count = 0
if "api_key_valid" not in st.session_state:
    st.session_state.api_key_valid = False # Default to invalid
if "current_api_key" not in st.session_state:
    st.session_state.current_api_key = None # Store the validated key
if "selected_system_prompt" not in st.session_state:
    # Find the default prompt text to initialize
    prompts = load_prompts()
    default_prompt_text = "You are a helpful assistant analyzing the provided document." # Fallback default
    for p in prompts:
        if p['id'] == 'default-general':
            default_prompt_text = p['text']
            break
    st.session_state.selected_system_prompt = default_prompt_text

# --- API Key Handling (Task 8.2) ---
localS = LocalStorage() # Initialize local storage interface

def validate_and_configure_key(key_to_test):
    """Attempts to configure genai with the key. Returns True if valid, False otherwise."""
    if not key_to_test:
        return False
    try:
        genai.configure(api_key=key_to_test)
        # Optional: Add a lightweight check like listing models if needed
        # genai.list_models()
        return True
    except Exception as e:
        # Optionally log the specific error e
        # print(f"API Key validation failed: {e}") # Console log for debugging
        return False

# Only perform initial check if key hasn't been validated in this session yet
if not st.session_state.api_key_valid:
    # 1. Try loading from Local Storage
    stored_key_data = localS.getItem("gemini_api_key")
    stored_key = stored_key_data.get('api_key') if stored_key_data else None # Safely get key

    if stored_key and validate_and_configure_key(stored_key):
        st.session_state.api_key_valid = True
        st.session_state.current_api_key = stored_key
        # print("API Key loaded and validated from Local Storage.") # Debug print
    else:
        # 2. Try loading from .env as fallback
        load_dotenv()
        env_key = os.getenv("GOOGLE_API_KEY")
        if env_key and validate_and_configure_key(env_key):
            st.session_state.api_key_valid = True
            st.session_state.current_api_key = env_key
            # Optionally save the .env key to local storage for next time?
            # localS.setItem("gemini_api_key", {"api_key": env_key})
            # print("API Key loaded and validated from .env file.") # Debug print
        # else: Key is not valid from either source yet

# --- Model Initialization (Task 8.6 part 1) ---
# Instantiate the model only if the API key is valid
model = None
model_name = "models/gemini-2.5-pro-exp-03-25"
if st.session_state.api_key_valid and st.session_state.current_api_key:
    try:
        # Ensure genai is configured before creating model instance
        # Validation already happened, but re-configuring is safe
        genai.configure(api_key=st.session_state.current_api_key)
        model = genai.GenerativeModel(model_name=model_name)
    except Exception as e:
        st.error(f"🚨 Error initializing Gemini model even after key validation: {e}")
        model = None # Ensure model is None if init fails
        st.session_state.api_key_valid = False # Mark as invalid again if model init fails

# --- Constants ---
CONTEXT_WINDOW_LIMIT = 1_000_000 # Based on Gemini 2.5 Pro documentation

# --- Helper Function for LLM Call (Task 8.6 part 2) ---
def generate_response(user_prompt, document_text, chat_history, system_prompt):
    """
    Generates response using Gemini, sending document text, history, and system prompt.
    Includes token check and history truncation.
    """
    # Check key validity and model initialization before proceeding
    if not st.session_state.api_key_valid or not st.session_state.current_api_key:
        return "Error: API Key not configured or invalid."
    if not model: # Check if model object exists
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
                f"System Prompt:\n---\n{system_prompt}\n---\n\n"
                f"Chat History:\n---\n{formatted_history}\n---\n\n"
                f"Document Content:\n---\n{document_text}\n---\n\n"
                f"User Question: {user_prompt}"
            )

            # --- Count Tokens for the Combined Prompt ---
            with st.spinner(f"Checking prompt size (history={history_limit} msgs)..."):
                 prompt_token_count = model.count_tokens(full_prompt).total_tokens

            if prompt_token_count <= CONTEXT_WINDOW_LIMIT:
                # Prompt fits, generate content
                st.info(f"Prompt size ({prompt_token_count:,} tokens) fits within limit. Generating response...")
                response = model.generate_content(full_prompt)
                # Check for safety ratings or blocked responses if needed
                # if not response.candidates: return "Error: Response blocked or empty."
                # Accessing response text might differ slightly based on API version/structure
                try:
                    return response.text
                except ValueError: # Handle cases where response might be blocked
                    st.error("Response generation failed or was blocked.")
                    return "Error: Response blocked or invalid."

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


# --- Main App Area ---

# --- Conditional UI Display (Task 8.3) ---
if st.session_state.api_key_valid:
    # --- Sidebar (Only shown if key is valid) ---
    with st.sidebar:
        st.header("Configuration")
        # Load prompts for the selectbox
        available_prompts = load_prompts()
        prompt_options = {p['name']: p['text'] for p in available_prompts}
        prompt_names = list(prompt_options.keys())

        # Find index of currently selected prompt name, default to first if not found
        current_prompt_text = st.session_state.selected_system_prompt
        current_prompt_name = next((name for name, text in prompt_options.items() if text == current_prompt_text), prompt_names[0] if prompt_names else None)
        try:
            # Use key for selectbox to prevent state issues on rerun
            current_index = prompt_names.index(current_prompt_name) if current_prompt_name else 0
        except ValueError:
            current_index = 0 # Default to first if name somehow doesn't match list

        selected_prompt_name = st.selectbox(
            "Select System Prompt:",
            options=prompt_names,
            index=current_index,
            key="system_prompt_selector", # Add key for stability
            help="Choose a system prompt to guide the AI. Manage prompts on the 'Manage Prompts' page."
        )

        # Update session state if selection changes
        if selected_prompt_name and prompt_options[selected_prompt_name] != st.session_state.selected_system_prompt:
            st.session_state.selected_system_prompt = prompt_options[selected_prompt_name]
            # st.info(f"System prompt set to: '{selected_prompt_name}'") # Can be a bit noisy

        st.divider()
        st.success("API Key Valid") # Show status in sidebar
        # Add a button to clear the stored API key
        if st.button("Clear Stored API Key"):
             try:
                 localS.deleteItem("gemini_api_key") # Attempt to remove from local storage
             except KeyError:
                 pass # Ignore if key wasn't in local storage anyway
             st.session_state.api_key_valid = False
             st.session_state.current_api_key = None
             model = None # Reset model instance
             st.info("Stored API Key cleared. Reloading...")
             time.sleep(1)
             st.rerun()

    # --- Main Chat Interface ---
    st.title("📄 Chat with your Document (CAG)") # Title inside the valid key block

    uploaded_file = st.file_uploader(
        "Upload your document (.txt, .pdf, .docx)",
        type=["txt", "pdf", "docx"],
        key="file_uploader" # Add key
    )

    # Check if a new file has been uploaded
    if uploaded_file is not None:
        # Check if the file object itself has changed, more reliable than just name
        if "processed_file_id" not in st.session_state or uploaded_file.id != st.session_state.processed_file_id:
            st.session_state.processed_file_id = uploaded_file.id # Store file ID
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
                        except Exception as e:
                            st.error(f"🚨 Error counting tokens: {e}")
                            st.session_state.document_content = None # Prevent chat on error
                            st.session_state.uploaded_file_name = None
                            st.session_state.document_token_count = 0
                    else:
                        # This case should be less likely now due to the outer check, but keep for safety
                        st.error("🚨 Cannot process document: Gemini model not initialized.")
                        st.session_state.document_content = None
                        st.session_state.uploaded_file_name = None
                        st.session_state.document_token_count = 0
                else:
                    # Error message is handled within extract_text_from_file
                    st.session_state.uploaded_file_name = None # Reset on error

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

            # --- LLM Call ---
            if st.session_state.document_content:
                 with st.chat_message("assistant"):
                     with st.spinner("Generating response..."):
                        response = generate_response(
                            user_prompt=prompt,
                            document_text=st.session_state.document_content,
                            chat_history=st.session_state.messages,
                            system_prompt=st.session_state.selected_system_prompt # Pass selected system prompt
                        )
                        st.markdown(response)
                        # Add assistant response to chat history ONLY if it's not an error message
                        if not response.startswith("Error:"):
                             st.session_state.messages.append({"role": "assistant", "content": response})
            else:
                 # This case should ideally not be reached
                 st.error("🚨 Internal error: Document content missing.")

    elif uploaded_file and st.session_state.document_content is None:
         # Case where file was uploaded but processing failed (e.g., too large, token error)
         # Error message should already be displayed above.
         pass # Don't show the "Please upload" message again
    elif not uploaded_file:
         st.info("Please upload a document (.txt, .pdf, .docx) to start chatting.")

else: # --- API Key Input Section (Task 8.4 & 8.5) ---
    st.title("🔑 Enter Gemini API Key")
    st.markdown("""
        This application requires a Google Gemini API key to function.
        You can obtain a key from [Google AI Studio](https://aistudio.google.com/app/apikey).

        Your key will be stored in your browser's local storage for convenience.
        Use the button in the sidebar (once the key is validated) to clear it.
    """)

    api_key_input = st.text_input("Enter your API Key:", type="password", key="api_key_input_ui")

    if st.button("Validate and Save Key", key="validate_api_key_button"):
        if validate_and_configure_key(api_key_input):
            localS.setItem("gemini_api_key", {"api_key": api_key_input}) # Save to local storage
            st.session_state.current_api_key = api_key_input
            st.session_state.api_key_valid = True
            st.success("API Key validated and saved successfully! Reloading app...")
            time.sleep(1) # Short delay before rerun
            st.rerun()
        else:
            st.error("Invalid API Key. Please check your key and try again.")