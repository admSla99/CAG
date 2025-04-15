# CAG Chat System with Streamlit and Gemini

This project implements a chat application that allows users to upload documents (.txt, .pdf, .docx) and ask questions about their content. It utilizes a Context-Augmented Generation (CAG) approach by loading the entire document content into the context window of a Google Gemini language model.

## Features

*   **Document Upload:** Supports `.txt`, `.pdf`, and `.docx` file formats.
*   **CAG Approach:** Loads the full text content of the uploaded document into the LLM's context for each query.
*   **LLM Integration:** Uses the `models/gemini-2.5-pro-exp-03-25` model via the `google-generativeai` library.
*   **Token Counting:** Calculates and displays the token count of the uploaded document relative to the model's context limit (1,000,000 tokens).
*   **Context Limit Handling:** Prevents processing documents that exceed the token limit and warns the user.
*   **Conversational History:** Includes recent chat history (up to 4 pairs) in the prompt sent to the LLM for better conversational flow.
*   **Dynamic History Truncation:** Attempts to reduce chat history included in the prompt if the combined size (history + document + query) exceeds the token limit.
*   **Streamlit UI:** Provides a multi-page web interface for chat interaction and prompt management.
*   **Custom System Prompts:** Allows users to define, save, and select custom system prompts to guide the LLM's behavior via a "Prompt Gallery".
*   **API Key Management:** Prompts user for Gemini API key via the UI if not found in browser local storage or `.env`. Stores validated key in browser local storage for persistence (per browser).

## Setup

1.  **Prerequisites:**
    *   Python 3.8+ recommended.
    *   `pip` and `venv` (usually included with Python).

2.  **Clone the Repository (if applicable):**
    ```bash
    git clone <your-repository-url>
    cd <repository-directory>
    ```

3.  **Create and Activate Virtual Environment:**
    ```bash
    # Create the environment
    python -m venv .venv

    # Activate (Windows CMD/PowerShell)
    .\.venv\Scripts\activate

    # Activate (Linux/macOS Bash)
    # source .venv/bin/activate
    ```

4.  **Install Dependencies:**
    ```bash
    # If requirements.txt exists (recommended):
    pip install -r requirements.txt

    # Or install manually:
    pip install streamlit google-generativeai pypdf python-docx python-dotenv streamlit-local-storage
    ```
    *(Note: You can generate `requirements.txt` using `pip freeze > requirements.txt` after manual installation.)*

5.  **Configure API Key:**
    *   **Primary Method (UI):** When you first run the app, if a valid API key isn't found in your browser's local storage or a `.env` file, you will be prompted to enter it directly in the web interface. The app will validate the key and store it in your browser's local storage for future sessions on that browser.
    *   **Alternative (`.env` file):** For development or if you prefer not to use local storage, you can create a file named `.env` in the project root directory and add your key:
        ```dotenv
        GOOGLE_API_KEY="YOUR_ACTUAL_GOOGLE_API_KEY"
        ```
        The app will attempt to load from local storage first, then fall back to this `.env` file if local storage is empty or the stored key is invalid.
    *   You can obtain a Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey).

## Running the Application

1.  Ensure your virtual environment is activated.
2.  Ensure you have a valid Google Gemini API key ready.
3.  Run the Streamlit application from the project root directory:
    ```bash
    streamlit run app.py
    ```
4.  The application should open in your default web browser.
5.  If this is your first time or your stored key is invalid, you'll be prompted to enter your API key. Paste your key and click "Validate and Save Key".
6.  Once the key is validated, the main chat interface will load. You can navigate to the "Manage Prompts" page using the sidebar.

## How it Works

1.  The user uploads a document via the Streamlit interface.
2.  The application extracts the text content using `document_processor.py`.
3.  The token count for the extracted text is calculated using the Gemini API.
4.  If the token count is within the model's limit (1,000,000 tokens), the content is stored, and the token count is displayed.
5.  The user enters a query in the chat input.
6.  The user selects a system prompt from the sidebar (or uses the default).
7.  The application constructs a prompt containing the selected system prompt, recent chat history, the full document text, and the user's query.
8.  It checks if the *combined* prompt (including the system prompt) exceeds the token limit. If it does, it attempts to reduce the included chat history.
9.  If the prompt fits, it's sent to the `gemini-2.5-pro-exp-03-25` model.
10. The model's response is displayed in the chat interface.

## Application Flow (Sequence Diagram)

sequenceDiagram
    participant User
    participant StreamlitUI as app.py
    participant SessionState as st.session_state
    participant DocProcessor as document_processor.py
    participant GeminiAPI as genai

    %% Initialization & API Key %%
    StreamlitUI->>+SessionState: Initialize state
    SessionState-->>-StreamlitUI: OK
    StreamlitUI->>StreamlitUI: Check for existing valid API Key (storage/env)
    alt Existing Key Valid
        StreamlitUI->>+SessionState: api_key_valid=True
        SessionState-->>-StreamlitUI: OK
    else No Valid Key Found
        StreamlitUI->>User: Display API Key Input Form
        User->>+StreamlitUI: Enter API Key + Click Validate
        StreamlitUI->>+GeminiAPI: Validate Key
        alt Key Valid
            GeminiAPI-->>-StreamlitUI: OK
            StreamlitUI->>StreamlitUI: Store Key (e.g., Local Storage)
            StreamlitUI->>+SessionState: api_key_valid=True
            SessionState-->>-StreamlitUI: OK
            StreamlitUI->>StreamlitUI: Rerun/Refresh UI
        else Key Invalid
            GeminiAPI-->>-StreamlitUI: Error
            StreamlitUI->>User: Show Invalid Key Error
        end
    end

    %% Main Application Flow (Assuming API Key is Valid) %%
    User->>+StreamlitUI: Upload Document (file)
    StreamlitUI->>+DocProcessor: extract_text_from_file(file)
    alt Extraction Successful
        DocProcessor-->>-StreamlitUI: extracted_text
        StreamlitUI->>+GeminiAPI: count_tokens(extracted_text)
        alt token_count <= LIMIT
            GeminiAPI-->>-StreamlitUI: token_count
            StreamlitUI->>+SessionState: Store document_content, token_count
            SessionState-->>-StreamlitUI: OK
            StreamlitUI->>User: Display Success & Token Info
        else token_count > LIMIT
            GeminiAPI-->>-StreamlitUI: token_count # Still need the response even if over limit
            StreamlitUI->>User: Show Document Too Large Error
            StreamlitUI->>+SessionState: Clear document state
            SessionState-->>-StreamlitUI: OK
        end
    else Extraction Failed
         DocProcessor-->>-StreamlitUI: Error # Indicate failure back to caller
         StreamlitUI->>User: Show Extraction Error
         StreamlitUI->>+SessionState: Clear document state # Optional: Clear state on failure too
         SessionState-->>-StreamlitUI: OK
    end

    opt Document Ready
        User->>+StreamlitUI: Select System Prompt
        StreamlitUI->>+SessionState: Store selected_system_prompt
        SessionState-->>-StreamlitUI: OK

        User->>+StreamlitUI: Enter Chat Prompt (user_query)
        StreamlitUI->>+SessionState: Get doc_text, history, system_prompt
        SessionState-->>-StreamlitUI: Data for prompt
        StreamlitUI->>StreamlitUI: Prepare prompt (system + history + doc + query)
        note right of StreamlitUI: May truncate history if prompt exceeds token limit
        StreamlitUI->>+GeminiAPI: generate_content(prepared_prompt)
        GeminiAPI-->>-StreamlitUI: response_text
        StreamlitUI->>User: Display response_text
        StreamlitUI->>+SessionState: Append query & response to history
        SessionState-->>-StreamlitUI: OK
    end
