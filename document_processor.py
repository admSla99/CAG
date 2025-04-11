import streamlit as st
from io import StringIO
from pypdf import PdfReader
from docx import Document

def extract_text_from_txt(uploaded_file):
    """Extracts text from an uploaded .txt file."""
    # To read file as string, decode it using utf-8.
    stringio = StringIO(uploaded_file.getvalue().decode("utf-8"))
    return stringio.read()

def extract_text_from_pdf(uploaded_file):
    """Extracts text from an uploaded .pdf file."""
    pdf_reader = PdfReader(uploaded_file)
    text = ""
    for page in pdf_reader.pages:
        page_text = page.extract_text()
        if page_text: # Ensure text was extracted
             text += page_text + "\n" # Add newline between pages
    return text

def extract_text_from_docx(uploaded_file):
    """Extracts text from an uploaded .docx file."""
    document = Document(uploaded_file)
    text = "\n".join([paragraph.text for paragraph in document.paragraphs])
    return text

def extract_text_from_file(uploaded_file):
    """
    Determines the file type and calls the appropriate text extraction function.
    Returns the extracted text as a string, or None if extraction fails.
    """
    if uploaded_file is None:
        return None

    file_type = uploaded_file.type
    file_name = uploaded_file.name # Useful for potential logging or error messages

    try:
        if file_type == "text/plain":
            return extract_text_from_txt(uploaded_file)
        elif file_type == "application/pdf":
            return extract_text_from_pdf(uploaded_file)
        elif file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            return extract_text_from_docx(uploaded_file)
        else:
            st.error(f"Unsupported file type: {file_type} for file '{file_name}'")
            return None
    except Exception as e:
        st.error(f"Error processing file '{file_name}': {e}")
        return None