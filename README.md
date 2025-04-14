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

```mermaid
sequenceDiagram
    participant User
    participant BrowserLocalStorage
    participant StreamlitUI as app.py
    participant SessionState as st.session_state
    participant DocProcessor as document_processor.py
    participant PromptUtils as prompt_utils.py
    participant GeminiAPI as genai

    %% Initialization and API Key Check %%
    StreamlitUI->>+SessionState: Initialize state (api_key_valid=False, etc.)
    SessionState-->>-StreamlitUI: OK
    StreamlitUI->>+BrowserLocalStorage: getItem("gemini_api_key")
    BrowserLocalStorage-->>-StreamlitUI: stored_key_data
    alt stored_key exists
        StreamlitUI->>+GeminiAPI: configure(api_key=stored_key)
        alt Key Valid
            GeminiAPI-->>-StreamlitUI: OK
            StreamlitUI->>+SessionState: api_key_valid=True, current_api_key=stored_key
            SessionState-->>-StreamlitUI: OK
        else Key Invalid
            GeminiAPI-->>-StreamlitUI: Error
            StreamlitUI->>StreamlitUI: Try .env key (load_dotenv, os.getenv)
            alt env_key exists
                 StreamlitUI->>+GeminiAPI: configure(api_key=env_key)
                 alt Key Valid
                      GeminiAPI-->>-StreamlitUI: OK
                      StreamlitUI->>+SessionState: api_key_valid=True, current_api_key=env_key
                      SessionState-->>-StreamlitUI: OK
                 else Key Invalid
                      GeminiAPI-->>-StreamlitUI: Error
                      StreamlitUI->>+SessionState: api_key_valid=False
                      SessionState-->>-StreamlitUI: OK
                 end
            else No .env key
                 StreamlitUI->>+SessionState: api_key_valid=False
                 SessionState-->>-StreamlitUI: OK
            end
        end
    else No stored_key
        StreamlitUI->>StreamlitUI: Try .env key (load_dotenv, os.getenv)
        alt env_key exists
             StreamlitUI->>+GeminiAPI: configure(api_key=env_key)
             alt Key Valid
                  GeminiAPI-->>-StreamlitUI: OK
                  StreamlitUI->>+SessionState: api_key_valid=True, current_api_key=env_key
                  SessionState-->>-StreamlitUI: OK
             else Key Invalid
                  GeminiAPI-->>-StreamlitUI: Error
                  StreamlitUI->>+SessionState: api_key_valid=False
                  SessionState-->>-StreamlitUI: OK
             end
        else No .env key
             StreamlitUI->>+SessionState: api_key_valid=False
             SessionState-->>-StreamlitUI: OK
        end
    end

    alt API Key Not Valid
        StreamlitUI->>User: Display API Key Input Form
        User->>+StreamlitUI: Enter API Key + Click Validate
        StreamlitUI->>+GeminiAPI: configure(api_key=input_key)
        alt Key Valid
            GeminiAPI-->>-StreamlitUI: OK
            StreamlitUI->>+BrowserLocalStorage: setItem("gemini_api_key", input_key)
            BrowserLocalStorage-->>-StreamlitUI: OK
            StreamlitUI->>+SessionState: api_key_valid=True, current_api_key=input_key
            SessionState-->>-StreamlitUI: OK
            StreamlitUI->>StreamlitUI: rerun()
        else Key Invalid
            GeminiAPI-->>-StreamlitUI: Error
            StreamlitUI->>User: Show Invalid Key Error
        end
    else API Key Valid (Show Main App)
        %% Document Upload and Processing %%
        User->>+StreamlitUI: Upload Document (file)
        StreamlitUI->>+DocProcessor: extract_text_from_file(file)
        DocProcessor-->>-StreamlitUI: extracted_text
        alt extracted_text is valid
            StreamlitUI->>+GeminiAPI: count_tokens(extracted_text)
            GeminiAPI-->>-StreamlitUI: token_count
            alt token_count <= LIMIT
                StreamlitUI->>+SessionState: Store document_content, token_count, file_name, file_size
                SessionState-->>-StreamlitUI: OK
                StreamlitUI->>User: Display Success & Token Info
            else token_count > LIMIT
                StreamlitUI->>User: Show Document Too Large Error
                StreamlitUI->>+SessionState: document_content=None, token_count=0
                SessionState-->>-StreamlitUI: OK
            end
        else extraction failed
             StreamlitUI->>User: Show Extraction Error
             StreamlitUI->>+SessionState: document_content=None, token_count=0
             SessionState-->>-StreamlitUI: OK
        end

        %% Chat Interaction %%
        opt Document Processed Successfully
            User->>+StreamlitUI: Select System Prompt (from sidebar)
            StreamlitUI->>+SessionState: Store selected_system_prompt
            SessionState-->>-StreamlitUI: OK

            User->>+StreamlitUI: Enter Chat Prompt (user_query)
            StreamlitUI->>+SessionState: Get document_content, messages (history), selected_system_prompt
            SessionState-->>-StreamlitUI: doc_text, history, system_prompt
            StreamlitUI->>StreamlitUI: generate_response(user_query, doc_text, history, system_prompt)
            loop Check Prompt Size & Truncate History
                StreamlitUI->>StreamlitUI: Construct full_prompt (system + history + doc + query)
                StreamlitUI->>+GeminiAPI: count_tokens(full_prompt)
                GeminiAPI-->>-StreamlitUI: combined_token_count
                alt combined_token_count <= LIMIT
                    StreamlitUI->>+GeminiAPI: generate_content(full_prompt)
                    GeminiAPI-->>-StreamlitUI: response_text
                    StreamlitUI->>User: Display response_text
                    StreamlitUI->>+SessionState: Append user_query to messages
                    SessionState-->>-StreamlitUI: OK
                    StreamlitUI->>+SessionState: Append response_text to messages
                    SessionState-->>-StreamlitUI: OK
                    break
                else combined_token_count > LIMIT and history exists
                    StreamlitUI->>StreamlitUI: Truncate history
                    StreamlitUI->>User: Show Warning (reducing history)
                else combined_token_count > LIMIT and no history left
                    StreamlitUI->>User: Show Error (Prompt too large even w/o history)
                    break
                end
            end
        end
    end
```