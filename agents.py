import os
import re
import json
import tempfile
import google.generativeai as genai
import pdfplumber
from docx import Document

import excel_manager
from extractor_v2 import extract_name, extract_email, extract_phone, extract_education

class AIDocumentReaderAgent:
    """Agent 1: Reads files (PDF, Image, DOCX) and extracts raw text or prepares multimodal data."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        if api_key:
            genai.configure(api_key=api_key)

    def extract_text_locally(self, temp_path: str, ext: str) -> str:
        """Extract text locally for text-based formats (PDF, DOCX)."""
        text = ""
        try:
            if ext == ".pdf":
                with pdfplumber.open(temp_path) as pdf:
                    for page in pdf.pages:
                        extracted = page.extract_text()
                        if extracted:
                            text += extracted + "\n"
            elif ext in [".docx", ".doc"]:
                doc = Document(temp_path)
                text = "\n".join([p.text for p in doc.paragraphs])
        except Exception as e:
            print(f"Local text extraction failed: {e}")
        return text.strip()

    def process(self, file_bytes: bytes, file_name: str, mime_type: str) -> dict:
        ext = os.path.splitext(file_name)[1].lower()
        
        # Write bytes to a temporary file for processing
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            tmp.write(file_bytes)
            temp_path = tmp.name

        try:
            raw_text = ""
            is_scanned = False
            
            # If it's a DOCX or PDF, try local extraction first
            if ext in [".pdf", ".docx", ".doc"]:
                raw_text = self.extract_text_locally(temp_path, ext)
                
            # If no text is extracted (or it's an image), we need multimodal Gemini OCR
            if not raw_text or len(raw_text.strip()) < 50 or ext in [".jpg", ".png", ".jpeg"]:
                is_scanned = True
                
            return {
                "file_name": file_name,
                "mime_type": mime_type,
                "ext": ext,
                "is_scanned": is_scanned,
                "extracted_text": raw_text,
                "file_bytes": file_bytes
            }
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


class AIExtractionAgent:
    """Agent 2: Scans document content (text/multimodal) and extracts structured info using Gemini."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        if api_key:
            genai.configure(api_key=api_key)

    def process(self, reader_output: dict) -> dict:
        if not self.api_key:
            raise ValueError("Gemini API Key is missing. Please configure it in the sidebar.")
            
        model = genai.GenerativeModel("gemini-3.5-flash")
        
        prompt = """You are an expert AI Resume Parsing Agent.
Analyze the resume content and extract the candidate information.

Extract these exact fields:
1. Full Name: The candidate's name. (Ensure you do NOT extract their parent's name from 'S/O', 'D/O', or 'W/O' fields).
2. Phone Number: Extract the candidate's primary phone number. Include country code if available.
3. Email: Candidate's email address.
4. Skills: Technical and soft skills found in the resume. Provide a clean, comma-separated string of skills.
5. Education: Candidate's highest qualification/degree (e.g. B.Tech in CSE, MCA, MBA).
6. College Name: The name of the college, university, or institute attended.
7. Experience: Professional experience in years (e.g. '3 Years', '5 Years', or 'Fresher' if no experience is listed).
8. Applied Role: The position they are applying for. Look at the objective, career profile, or recent work experience header. If not explicitly stated, infer the best-fitting role based on skills/experience (e.g. Frontend Developer, Python Engineer, HR Manager). Do not return 'Not found', infer a role.

Return ONLY a valid JSON object matching this structure. Do NOT include markdown blocks, ```json, or other text:
{
  "Full Name": "...",
  "Phone Number": "...",
  "Email": "...",
  "Skills": "...",
  "Education": "...",
  "College Name": "...",
  "Experience": "...",
  "Applied Role": "..."
}
"""
        
        try:
            # Check if we should pass the raw file bytes for multimodal analysis (scanned PDF or Image)
            if reader_output["is_scanned"]:
                # Multimodal request
                content_parts = [
                    {"data": reader_output["file_bytes"], "mime_type": reader_output["mime_type"]},
                    prompt
                ]
                response = model.generate_content(
                    content_parts,
                    generation_config={"response_mime_type": "application/json"}
                )
            else:
                # Text-only request
                text_content = reader_output["extracted_text"]
                # Append a snippet of the text
                full_prompt = f"{prompt}\n\nResume Text:\n{text_content[:20000]}"
                response = model.generate_content(
                    full_prompt,
                    generation_config={"response_mime_type": "application/json"}
                )
                
            result_json = response.text.strip()
            
            # Parse the output
            extracted_data = json.loads(result_json)
            return extracted_data
            
        except Exception as e:
            print(f"Gemini API generation or parsing failed: {e}")
            # Return empty structure for the next agent to validate / fallback
            return {
                "Full Name": "",
                "Phone Number": "",
                "Email": "",
                "Skills": "",
                "Education": "",
                "College Name": "",
                "Experience": "",
                "Applied Role": ""
            }


class ValidationAgent:
    """Agent 3: Validates and cleans extracted fields, falling back to local NLP/regex extractors if needed."""
    
    def process(self, extracted_data: dict, reader_output: dict) -> dict:
        raw_text = reader_output.get("extracted_text", "")
        
        def safe_str(val) -> str:
            if val is None:
                return ""
            if isinstance(val, list):
                val_str = ", ".join([str(v) for v in val if v])
            elif isinstance(val, dict):
                val_str = ", ".join([f"{k}: {v}" for k, v in val.items() if v])
            else:
                val_str = str(val)
            return re.sub(r'\s+', ' ', val_str).strip()
            
        # Clean Full Name
        name = safe_str(extracted_data.get("Full Name"))
        if not name or name.lower() in ["not specified", "unknown", "none", "name not found", ""]:
            # Fallback to local regex/nlp name extractor
            fallback_name = extract_name(raw_text)
            name = fallback_name if fallback_name else "Unknown Candidate"
        name = re.sub(r'\s+', ' ', name).strip()
            
        # Clean Email
        email = safe_str(extracted_data.get("Email"))
        email = re.sub(r'\s+', '', email)
        # Basic validation
        email_regex = r'\b[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}\b'
        if not email or not re.match(email_regex, email):
            # Fallback to local regex
            fallback_emails = extract_email(raw_text)
            email = fallback_emails[0] if fallback_emails else ""
            
        # Clean Phone Number
        phone = safe_str(extracted_data.get("Phone Number"))
        # Remove common text headers like "phone:", "mobile:"
        phone = re.sub(r'^(phone|mobile|tel|contact|call|ph)[:\-\s]*', '', phone, flags=re.IGNORECASE).strip()
        if not phone or len(re.sub(r'\D', '', phone)) < 8:
            # Fallback to local phone matcher
            fallback_phones = extract_phone(raw_text)
            phone = fallback_phones[0] if fallback_phones else ""
            
        # Clean Skills
        skills = safe_str(extracted_data.get("Skills"))
        # Clean redundant spaces
        skills = ", ".join([s.strip() for s in skills.split(",") if s.strip()])
        if not skills or skills.lower() in ["none", "not specified"]:
            skills = "N/A"
            
        # Clean Education
        education = safe_str(extracted_data.get("Education"))
        if not education or education.lower() in ["none", "not specified"]:
            fallback_edu = extract_education(raw_text)
            education = fallback_edu if fallback_edu else "N/A"
            
        # College Name
        college = safe_str(extracted_data.get("College Name"))
        if not college or college.lower() in ["none", "not specified", "unknown"]:
            college = "N/A"
            
        # Experience
        experience = safe_str(extracted_data.get("Experience"))
        if not experience or experience.lower() in ["none", "not specified"]:
            experience = "Fresher"
            
        # Applied Role
        applied_role = safe_str(extracted_data.get("Applied Role"))
        if not applied_role or applied_role.lower() in ["none", "not specified", "unknown"]:
            applied_role = "General Candidate"
            
        return {
            "File Name": reader_output["file_name"],
            "Full Name": name,
            "Phone Number": phone,
            "Email": email,
            "Skills": skills,
            "Education": education,
            "College Name": college,
            "Experience": experience,
            "Applied Role": applied_role
        }


class StorageAgent:
    """Agent 4: Appends the validated candidate record to the master Excel sheet."""
    
    def process(self, validated_data: dict, excel_path: str = None) -> dict:
        try:
            kwargs = {}
            if excel_path:
                kwargs["excel_path"] = excel_path
                
            saved_row = excel_manager.append_candidate_to_excel(validated_data, **kwargs)
            return {
                "success": True,
                "saved_row": saved_row,
                "message": "Candidate successfully saved to master Excel file."
            }
        except Exception as e:
            return {
                "success": False,
                "saved_row": None,
                "message": f"Storage Error: {str(e)}"
            }


def run_agent_pipeline(file_bytes: bytes, file_name: str, mime_type: str, api_key: str, progress_callback=None, excel_path=None) -> dict:
    """
    Executes the entire agentic pipeline step-by-step.
    Calls `progress_callback` at each step to update the client application.
    """
    try:
        # Step 1: AI Document Reader Agent
        if progress_callback:
            progress_callback("reader_start", f"Scanning file '{file_name}'...")
        reader = AIDocumentReaderAgent(api_key)
        reader_output = reader.process(file_bytes, file_name, mime_type)
        if progress_callback:
            mode = "Multimodal Gemini OCR" if reader_output["is_scanned"] else "Text Extractor"
            progress_callback("reader_done", f"Scan complete. Mode: {mode}.")

        # Step 2: AI Information Extraction Agent
        if progress_callback:
            progress_callback("extractor_start", "Extracting key resume fields using Gemini...")
        extractor = AIExtractionAgent(api_key)
        extracted_data = extractor.process(reader_output)
        if progress_callback:
            progress_callback("extractor_done", "Field extraction completed successfully.")

        # Step 3: Validation Agent
        if progress_callback:
            progress_callback("validator_start", "Running validation rules & checking contact data...")
        validator = ValidationAgent()
        validated_data = validator.process(extracted_data, reader_output)
        if progress_callback:
            progress_callback("validator_done", f"Candidate validated: {validated_data.get('Full Name')}")

        # Step 4: Storage Agent
        if progress_callback:
            progress_callback("storage_start", "Saving candidate to local Excel sheet...")
        storage = StorageAgent()
        storage_result = storage.process(validated_data, excel_path)
        
        if progress_callback:
            if storage_result["success"]:
                progress_callback("storage_done", "Row successfully appended to master Excel sheet!")
            else:
                progress_callback("storage_error", f"Failed to save record: {storage_result['message']}")
                
        return {
            "success": storage_result["success"],
            "data": validated_data,
            "message": storage_result["message"]
        }
        
    except Exception as e:
        if progress_callback:
            progress_callback("pipeline_error", f"Pipeline failed: {str(e)}")
        return {
            "success": False,
            "data": None,
            "message": f"Pipeline execution failed: {str(e)}"
        }
