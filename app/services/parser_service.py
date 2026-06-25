import io
import PyPDF2
import re

# DOCX support
try:
    from docx import Document
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False


# ---------------------------------------------------
# PDF TEXT EXTRACTION
# ---------------------------------------------------

def extract_pdf_text(uploaded_file):

    try:

        uploaded_file.seek(0)

        pdf_reader = PyPDF2.PdfReader(
            io.BytesIO(uploaded_file.read())
        )

        text = ""

        for page in pdf_reader.pages:

            page_text = page.extract_text()

            if page_text:
                text += page_text + "\n"

        return text.strip()

    except Exception as e:

        return f"Could not read PDF: {str(e)}"


# ---------------------------------------------------
# DOCX TEXT EXTRACTION
# ---------------------------------------------------

def extract_docx_text(uploaded_file):

    if not DOCX_AVAILABLE:
        return "python-docx not installed."

    try:

        uploaded_file.seek(0)

        doc = Document(io.BytesIO(uploaded_file.read()))

        text = "\n".join(
            [p.text for p in doc.paragraphs if p.text.strip()]
        )

        return text.strip()

    except Exception as e:

        return f"Could not read DOCX: {str(e)}"


# ---------------------------------------------------
# FILE ROUTER
# ---------------------------------------------------

def extract_file_text(uploaded_file):

    filename = uploaded_file.name.lower()

    if filename.endswith(".pdf"):
        return extract_pdf_text(uploaded_file)

    elif filename.endswith(".docx"):
        return extract_docx_text(uploaded_file)

    else:
        return f"Unsupported file type: {filename}"


# ---------------------------------------------------
# MULTIPLE RESUME EXTRACTION
# ---------------------------------------------------

def extract_multiple_resumes(uploaded_files):

    all_resumes = []
    resume_data = []

    for i, file in enumerate(uploaded_files, 1):

        extracted_text = extract_file_text(file)

        candidate_email = extract_email(
            extracted_text
        )

        candidate_name = (
            file.name
            .replace(".pdf", "")
            .replace(".docx", "")
            .replace("_", " ")
            .replace("-", " ")
        )

        formatted_resume = f"""
        --- Candidate {i}: {candidate_name} ---

        {extracted_text}
        """

        resume_data.append({
            "candidate_name": candidate_name,
            "email": candidate_email,
            "resume_text": extracted_text
        })

        all_resumes.append(formatted_resume)

    return {
        "combined_text": "\n\n".join(all_resumes),
        "resume_data": resume_data
    }

def extract_email(text):

    match = re.search(
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        text
    )

    if match:
        return match.group(0)

    return ""