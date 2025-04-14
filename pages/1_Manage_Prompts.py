import streamlit as st
from prompt_utils import load_prompts, add_prompt, delete_prompt, DEFAULT_PROMPTS

st.set_page_config(page_title="Manage Prompts", page_icon="⚙️")

st.title("⚙️ Manage System Prompts")

st.write("Here you can create, view, and delete reusable system prompts for the chat.")

# --- Load Prompts ---
prompts = load_prompts()

# --- Display Existing Prompts ---
st.subheader("Existing Prompts")
if not prompts:
    st.info("No custom prompts saved yet. Default prompts are available.")
else:
    # Separate default and custom prompts for clarity
    default_ids = {p['id'] for p in DEFAULT_PROMPTS}
    custom_prompts = [p for p in prompts if p['id'] not in default_ids]
    default_prompts_in_file = [p for p in prompts if p['id'] in default_ids]

    if default_prompts_in_file:
         st.markdown("**Default Prompts:**")
         for prompt in default_prompts_in_file:
              with st.expander(f"{prompt['name']} (Default)"):
                   st.code(prompt['text'], language=None) # Use st.code for better formatting

    if custom_prompts:
         st.markdown("**Custom Prompts:**")
         for prompt in custom_prompts:
              col1, col2 = st.columns([0.8, 0.2])
              with col1:
                   with st.expander(f"{prompt['name']}"):
                        st.code(prompt['text'], language=None)
              with col2:
                   # Use unique key for delete button based on prompt ID
                   if st.button("Delete", key=f"delete_{prompt['id']}", help=f"Delete prompt '{prompt['name']}'"):
                        if delete_prompt(prompt['id']):
                             st.rerun() # Refresh page to show updated list

st.divider()

# --- Add New Prompt ---
st.subheader("Add New Prompt")
with st.form("new_prompt_form", clear_on_submit=True):
    new_prompt_name = st.text_input("Prompt Name (must be unique)")
    new_prompt_text = st.text_area("Prompt Text", height=150)
    submitted = st.form_submit_button("Save New Prompt")
    if submitted:
        if add_prompt(new_prompt_name, new_prompt_text):
            st.rerun() # Refresh page to show the new prompt