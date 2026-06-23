from fastapi import FastAPI, HTTPException, UploadFile, File, Request, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.security import APIKeyHeader
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import requests
import tempfile
import os
from datetime import date

from extract_ocr import extract_text as file_to_text
from extractor_v2 import (
    extract_name,
    extract_email,
    extract_phone,
    extract_education,
    detect_pan,
    detect_aadhaar
)
from location_address_v2 import extract_current_location, extract_address

import re
import google.generativeai as genai
import pandas as pd
import json
import io
from fastapi.responses import StreamingResponse

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def calculate_experience(text):
    text_lower = text.lower()
    matches = re.findall(r'(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)(?:\s+of)?\s+experience', text_lower)
    if matches:
        try: return float(matches[0])
        except: pass
    matches = re.findall(r'experience\s*[:\-]?\s*(\d+(?:\.\d+)?)', text_lower)
    if matches:
        try: return float(matches[0])
        except: pass
    return 0

def match_job(text):
    if not GEMINI_API_KEY:
        return {
            "jobTitle": "Not Available",
            "department": "Not Available",
            "matchScore": 0,
            "skills": ["LLM API Key Missing"],
            "skillClusters": {},
            "fitScore": 0,
            "missingSkills": []
        }
    prompt = """You are an AI resume analyzer. Extract the following from the resume text and return ONLY valid JSON:
- jobTitle (most recent or suitable job title)
- department (e.g. Engineering, Sales, HR)
- skills (list of strings)
- skillClusters (dict categorizing skills, e.g. {"Languages": ["Python"], "Frameworks": ["React"]})
- fitScore (number between 0-100 representing resume quality)
- missingSkills (list of obvious skills missing for the jobTitle)
- matchScore (same as fitScore)

Resume Text:
""" + text[:10000]
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        res_text = response.text.strip()
        if res_text.startswith("```json"): res_text = res_text[7:]
        elif res_text.startswith("```"): res_text = res_text[3:]
        if res_text.endswith("```"): res_text = res_text[:-3]
        return json.loads(res_text.strip())
    except Exception as e:
        print(f"Job Match LLM failed: {e}")
        return {}


# ================= CONFIG =================

API_KEY = os.getenv("RESUME_API_KEY", "pk_ai_resume_2026")
MAX_FILE_SIZE_MB = 10
MAX_TEXT_LENGTH = 20000

api_key_header = APIKeyHeader(name="x-api-key", auto_error=False)


# ================= APP INIT =================

app = FastAPI(
    title="AI Resume Parsing API",
    version="5.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # change to frontend domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend static files
_frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
if os.path.isdir(_frontend_dir):
    app.mount("/static", StaticFiles(directory=_frontend_dir), name="static")


# ================= GLOBAL ERROR HANDLER =================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": "Internal Server Error"}
    )


# ================= HEALTH =================

@app.get("/health")
def health():
    return {"status": "running"}


# ================= FRONTEND =================

@app.get("/", include_in_schema=False)
def serve_frontend():
    """Serve the resume parser UI."""
    index_path = os.path.join(os.path.dirname(__file__), "frontend", "index.html")
    if os.path.isfile(index_path):
        return FileResponse(index_path)
    return {"message": "AI Resume Parser API v5.0 — visit /docs"}


# ================= AUTH VALIDATION =================

def validate_api_key(api_key: str):
    if api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")


# ================= REQUEST MODEL =================

class ResumeURLRequest(BaseModel):
    resume: str


# ================= SAFE DOWNLOADER =================

def download_file(url: str):

    try:
        response = requests.get(url, timeout=20)
    except Exception:
        raise HTTPException(status_code=400, detail="Resume download failed")

    if response.status_code != 200:
        raise HTTPException(status_code=400, detail="Resume download failed")

    size_mb = len(response.content) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise HTTPException(status_code=400, detail="File too large")

    suffix = os.path.splitext(url.split("?")[0])[1] or ".pdf"

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(response.content)
        return tmp.name


# ================= CORE PARSER =================

def parse_core(path, resume_url=""):

    text = file_to_text(path)

    if not text or len(text.strip()) < 20:
        raise HTTPException(status_code=400, detail="Could not extract text")

    safe_text = text[:MAX_TEXT_LENGTH]

    emails = extract_email(safe_text)
    phones = extract_phone(safe_text)

    addr = extract_address(safe_text)

    if not isinstance(addr, dict):
        addr = {
        "address": "",
        "city": "",
        "state": "",
        "country": "India",
        "pincode": ""
    }

    location = extract_current_location(safe_text) or {}

    result = {

        "candidateName": extract_name(safe_text) or "",
        "jobTitle": "",
        "department": "",
        "resume": resume_url,
        "isEmployee": "candidate",
        "certificates": [],

        "address": addr.get("address", ""),
        "city": addr.get("city", ""),
        "state": addr.get("state", ""),
        "country": addr.get("country", "India"),
        "pinCode": addr.get("pincode", ""),

        "yearsOfExperience": calculate_experience(safe_text),
        "educationQualification": extract_education(safe_text) or "",

        "currentWorkLocation": (
            f"{location.get('city','')}, {location.get('state','')}"
            if location else ""
        ),

        "emails": [
            {"emailAddress": e, "isPrimary": i == 0}
            for i, e in enumerate(emails)
        ],

        "mobileNumbers": [
            {"mobileNumber": p, "isPrimary": i == 0}
            for i, p in enumerate(phones)
        ],

        "pan": {
            "_id": "",
            "panNumber": detect_pan(safe_text) or ""
        },

        "aadhar": {
            "_id": "",
            "aadharNumber": detect_aadhaar(safe_text) or ""
        },

        "appliedDate": date.today().isoformat(),
        "_raw_text": safe_text
    }

    return result


# ================= V1 =================

@app.post("/parse-resume")
def parse_resume(data: ResumeURLRequest, api_key: str = Security(api_key_header)):

    validate_api_key(api_key)

    path = download_file(data.resume)

    try:
        result = parse_core(path, data.resume)
        result.pop("_raw_text", None)
        return result
    finally:
        os.remove(path)


@app.post("/parse-resume-upload")
def parse_upload(file: UploadFile = File(...), api_key: str = Security(api_key_header)):

    validate_api_key(api_key)

    allowed = (".pdf", ".docx",".doc", ".jpg", ".jpeg", ".png")

    if not file.filename.lower().endswith(allowed):
        raise HTTPException(status_code=400, detail="Unsupported format")

    content = file.file.read()

    size_mb = len(content) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise HTTPException(status_code=400, detail="File too large")

    suffix = os.path.splitext(file.filename)[1]

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        path = tmp.name

    try:
        result = parse_core(path)
        result.pop("_raw_text", None)
        return result
    finally:
        os.remove(path)


# ================= V2 (AI ENGINE) =================

@app.post("/v2/parse-resume")
def parse_resume_v2(data: ResumeURLRequest, api_key: str = Security(api_key_header)):

    validate_api_key(api_key)

    path = download_file(data.resume)

    try:
        result = parse_core(path, data.resume)

        job_data = match_job(result["_raw_text"]) or {}

        result.update({
            "jobTitle": job_data.get("jobTitle", ""),
            "department": job_data.get("department", ""),
            "matchScore": job_data.get("matchScore", 0),
            "skills": job_data.get("skills", []),
            "skillClusters": job_data.get("skillClusters", {}),
            "fitScore": job_data.get("fitScore", 0),
            "missingSkills": job_data.get("missingSkills", [])
        })

        result.pop("_raw_text", None)
        return result

    finally:
        os.remove(path)


# ================= PERSISTENT EXCEL HELPERS =================

EXCEL_OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "resumes_output.xlsx")

EXCEL_COLUMNS = [
    "S.No", "File Name", "Full Name", "Email", "Phone", "Address",
    "Skills", "Education", "Experience", "Projects", "Certifications", "Parsed At"
]

def flatten_field(val):
    """Flatten list/dict values into a readable string."""
    if isinstance(val, list):
        items = []
        for item in val:
            if isinstance(item, dict):
                items.append(", ".join([f"{v}" for v in item.values() if v]))
            else:
                items.append(str(item))
        return "\n".join(items)
    elif isinstance(val, dict):
        return ", ".join([f"{v}" for v in val.values() if v])
    return str(val) if val else ""

def load_excel_df():
    """Load existing master Excel file or create a fresh empty one."""
    if os.path.exists(EXCEL_OUTPUT_PATH):
        try:
            return pd.read_excel(EXCEL_OUTPUT_PATH, engine="openpyxl")
        except Exception:
            pass
    return pd.DataFrame(columns=EXCEL_COLUMNS)

def save_excel_df(df: pd.DataFrame):
    """Save DataFrame to the master Excel file on disk."""
    df.to_excel(EXCEL_OUTPUT_PATH, index=False, engine="openpyxl")

def gemini_parse(safe_text: str) -> dict:
    """Call Gemini LLM to extract structured resume fields."""
    if not GEMINI_API_KEY:
        return {}
    prompt = f"""You are an intelligent resume parser.
Extract structured information from the resume text and return ONLY valid JSON.

Fields to extract:
- full_name
- email
- phone
- address
- skills (list of strings)
- education (list of dicts with keys: degree, institution, year)
- experience (list of dicts with keys: company, role, duration)
- projects (list of strings or dicts)
- certifications (list of strings)

Rules:
- Return clean JSON ONLY (no explanation, no markdown, no code fences).
- If a field is missing, use null or empty list.

Resume Text:
{safe_text}
"""
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        res_text = response.text.strip()
        if res_text.startswith("```json"):
            res_text = res_text[7:]
        elif res_text.startswith("```"):
            res_text = res_text[3:]
        if res_text.endswith("```"):
            res_text = res_text[:-3]
        return json.loads(res_text.strip())
    except Exception as e:
        print(f"Gemini parse failed: {e}")
        return {}


# ================= V3 — APPEND RESUME TO MASTER EXCEL =================

@app.post("/append-resume-to-excel")
def append_resume_to_excel(file: UploadFile = File(...), api_key: str = Security(api_key_header)):
    """
    Parse one resume and APPEND its data as a new row to the persistent master Excel file.
    Returns the extracted row as JSON for frontend preview.
    """
    validate_api_key(api_key)

    allowed = (".pdf", ".docx", ".doc", ".jpg", ".jpeg", ".png")
    if not file.filename.lower().endswith(allowed):
        raise HTTPException(status_code=400, detail="Unsupported file format")

    content = file.file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise HTTPException(status_code=400, detail="File too large (max 10 MB)")

    suffix = os.path.splitext(file.filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        path = tmp.name

    try:
        # Step 1: Extract raw text via OCR
        text = file_to_text(path)
        if not text or len(text.strip()) < 20:
            raise HTTPException(status_code=400, detail="Could not extract text from resume")

        safe_text = text[:MAX_TEXT_LENGTH]

        # Step 2: AI parse
        ai_data = gemini_parse(safe_text)

        # Step 3: Build flat row
        df_existing = load_excel_df()
        s_no = len(df_existing) + 1

        row = {
            "S.No": s_no,
            "File Name": file.filename,
            "Full Name": ai_data.get("full_name") or extract_name(safe_text) or "",
            "Email": ai_data.get("email") or ", ".join(extract_email(safe_text)),
            "Phone": ai_data.get("phone") or ", ".join(extract_phone(safe_text)),
            "Address": ai_data.get("address") or "",
            "Skills": flatten_field(ai_data.get("skills", "")),
            "Education": flatten_field(ai_data.get("education", "")) or extract_education(safe_text) or "",
            "Experience": flatten_field(ai_data.get("experience", "")),
            "Projects": flatten_field(ai_data.get("projects", "")),
            "Certifications": flatten_field(ai_data.get("certifications", "")),
            "Parsed At": date.today().isoformat(),
        }

        # Step 4: Append row and save Excel to disk
        new_df = pd.concat([df_existing, pd.DataFrame([row])], ignore_index=True)
        save_excel_df(new_df)

        return {
            "success": True,
            "row_number": s_no,
            "total_rows": len(new_df),
            "row": row
        }

    finally:
        os.remove(path)


# ================= DOWNLOAD MASTER EXCEL =================

@app.get("/download-excel")
def download_excel(api_key: str = Security(api_key_header)):
    """Download the master Excel file containing all parsed resumes."""
    validate_api_key(api_key)
    if not os.path.exists(EXCEL_OUTPUT_PATH):
        raise HTTPException(status_code=404, detail="No data yet. Please parse some resumes first.")
    return FileResponse(
        EXCEL_OUTPUT_PATH,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="resumes_data.xlsx",
        headers={"Content-Disposition": "attachment; filename=resumes_data.xlsx"}
    )


# ================= GET CURRENT EXCEL ROWS (for UI preview) =================

@app.get("/excel-rows")
def get_excel_rows(api_key: str = Security(api_key_header)):
    """Return all rows from the master Excel file as JSON (for UI table preview)."""
    validate_api_key(api_key)
    df = load_excel_df()
    # Replace NaN with empty string so JSON serialization doesn't fail
    df = df.fillna("")
    return {"total": len(df), "rows": df.to_dict(orient="records")}


# ================= PARSE RESUME → INSTANT EXCEL DOWNLOAD =================

@app.post("/parse-resume-excel")
def parse_resume_excel(file: UploadFile = File(...), api_key: str = Security(api_key_header)):
    """
    Parse a single resume and return an Excel file as a direct download.
    This is the endpoint used by the frontend UI.
    """
    validate_api_key(api_key)

    allowed = (".pdf", ".docx", ".doc", ".jpg", ".jpeg", ".png")
    if not file.filename.lower().endswith(allowed):
        raise HTTPException(status_code=400, detail="Unsupported file format")

    content = file.file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise HTTPException(status_code=400, detail="File too large (max 10 MB)")

    suffix = os.path.splitext(file.filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        path = tmp.name

    try:
        # Step 1: Extract raw text via OCR
        text = file_to_text(path)
        if not text or len(text.strip()) < 20:
            raise HTTPException(status_code=400, detail="Could not extract text from resume")

        safe_text = text[:MAX_TEXT_LENGTH]

        # Step 2: AI parse with Gemini
        ai_data = gemini_parse(safe_text)

        # Step 3: Fallback to regex extractors if AI fields are missing
        row = {
            "S.No": 1,
            "File Name": file.filename,
            "Full Name": ai_data.get("full_name") or extract_name(safe_text) or "",
            "Email": ai_data.get("email") or ", ".join(extract_email(safe_text)),
            "Phone": ai_data.get("phone") or ", ".join(extract_phone(safe_text)),
            "Address": ai_data.get("address") or "",
            "Skills": flatten_field(ai_data.get("skills", "")),
            "Education": flatten_field(ai_data.get("education", "")) or extract_education(safe_text) or "",
            "Experience": flatten_field(ai_data.get("experience", "")),
            "Projects": flatten_field(ai_data.get("projects", "")),
            "Certifications": flatten_field(ai_data.get("certifications", "")),
            "Parsed At": date.today().isoformat(),
        }

        # Step 4: Build Excel in memory and stream it back
        df = pd.DataFrame([row], columns=EXCEL_COLUMNS)
        output = io.BytesIO()
        df.to_excel(output, index=False, engine="openpyxl")
        output.seek(0)

        filename = f"parsed_{os.path.splitext(file.filename)[0]}.xlsx"
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    finally:
        os.remove(path)


# ================= RESET MASTER EXCEL =================

@app.delete("/reset-excel")
def reset_excel(api_key: str = Security(api_key_header)):
    """Delete the master Excel file and start fresh."""
    validate_api_key(api_key)
    if os.path.exists(EXCEL_OUTPUT_PATH):
        os.remove(EXCEL_OUTPUT_PATH)
    return {"success": True, "message": "Excel file reset. Ready for new data."}
