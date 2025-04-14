import json
import os
import uuid
import streamlit as st # For error display potentially

PROMPTS_FILE = "prompts.json"
DEFAULT_PROMPTS = [
    {
        "id": "default-general",
        "name": "Default (General Assistant)",
        "text": "You are a helpful assistant analyzing the provided document. Answer the user's questions based on the document content."
    },
    {
        "id": "default-summary",
        "name": "Default (Summarizer)",
        "text": "You are an expert summarizer. Based on the provided document, summarize the key points in response to the user's request."
    }
]

def load_prompts():
    """Loads prompts from the JSON file, creating it with defaults if it doesn't exist."""
    if not os.path.exists(PROMPTS_FILE):
        save_prompts(DEFAULT_PROMPTS) # Create with defaults
        return DEFAULT_PROMPTS
    try:
        with open(PROMPTS_FILE, 'r', encoding='utf-8') as f:
            prompts = json.load(f)
            # Ensure default prompts are present if file exists but is empty or missing them
            # This is a simple check; more robust merging could be added if needed
            if not any(p['id'] == 'default-general' for p in prompts):
                 prompts.extend(DEFAULT_PROMPTS)
                 save_prompts(prompts)
            return prompts
    except (json.JSONDecodeError, FileNotFoundError) as e:
        st.error(f"Error loading prompts file ({PROMPTS_FILE}): {e}. Using defaults.")
        # Attempt to save defaults if loading failed badly
        try:
            save_prompts(DEFAULT_PROMPTS)
        except Exception as save_e:
             st.error(f"Failed to save default prompts: {save_e}")
        return DEFAULT_PROMPTS
    except Exception as e:
        st.error(f"An unexpected error occurred loading prompts: {e}")
        return DEFAULT_PROMPTS # Fallback to defaults

def save_prompts(prompts_list):
    """Saves the list of prompts to the JSON file."""
    try:
        with open(PROMPTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(prompts_list, f, indent=4)
    except Exception as e:
        st.error(f"Error saving prompts to {PROMPTS_FILE}: {e}")
        # Decide if we should raise the error or just log it

def add_prompt(name, text):
    """Adds a new prompt to the list and saves."""
    if not name or not text:
        st.error("Prompt name and text cannot be empty.")
        return False
    prompts = load_prompts()
    # Check for duplicate names (case-insensitive check)
    if any(p['name'].lower() == name.lower() for p in prompts):
        st.error(f"A prompt with the name '{name}' already exists.")
        return False

    new_prompt = {
        "id": str(uuid.uuid4()), # Generate a unique ID
        "name": name.strip(),
        "text": text.strip()
    }
    prompts.append(new_prompt)
    save_prompts(prompts)
    st.success(f"Prompt '{name}' added successfully.")
    return True

def delete_prompt(prompt_id):
    """Deletes a prompt by its ID and saves."""
    prompts = load_prompts()
    initial_length = len(prompts)
    # Prevent deleting default prompts
    if prompt_id in [p['id'] for p in DEFAULT_PROMPTS]:
         st.error("Cannot delete default prompts.")
         return False

    prompts_to_keep = [p for p in prompts if p['id'] != prompt_id]

    if len(prompts_to_keep) < initial_length:
        save_prompts(prompts_to_keep)
        st.success(f"Prompt deleted successfully.")
        return True
    else:
        st.error(f"Prompt with ID '{prompt_id}' not found.")
        return False