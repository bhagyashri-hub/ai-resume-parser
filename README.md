# Project Title
# Resume Parser using OCR & FastAPI
Developing an advanced resume extraction system using OCR to convert scanned and PDF documents into machine-readable text.
Built a robust pipeline to transform unstructured resume data into structured JSON format for downstream applications.
Implemented entity extraction (name, address, email, phone, education, ID details) using Regex and SpaCy (NER).
Designed and deployed secure REST APIs using FastAPI for real-time resume processing.
Integrated file upload handling and automated text extraction using custom OCR engine.
Enabled end-to-end workflow: document upload → OCR → data extraction → JSON response.
Applied data validation and error handling for reliable API performance.
Built scalable backend architecture to support multiple resume formats and noisy data.
Designed modular pipeline for scalable data extraction and transformation.

# Features
- OCR-based text extraction from scanned and PDF resumes
- Entity extraction (Name, Email, Phone, Education, Address, ID details)
- REST API development using FastAPI
- Secure API access using API Key Header
- Structured JSON output generation
- Error handling and data validation
- Scalable and modular pipeline design

# Tech Stack
- Python
- FastAPI (API Key Header Security)
- SpaCy (NLP / NER)
- Regex
- OCR Engine
  
# API Flow
Upload Resume → OCR → Data Extraction → JSON Output

# Sample Output
{
  "candidateName": "Chandu S",
  "address": "Sivajij Nagar, Rajampet, Annamayya District",
  "city": "Annamayya District",
  "state": "A.P",
  "country": "India",
  "pinCode": "516115"
}
