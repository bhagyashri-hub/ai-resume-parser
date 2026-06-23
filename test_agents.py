import os
import pandas as pd
import excel_manager
from agents import AIDocumentReaderAgent, ValidationAgent

# Define temp test excel path
TEST_EXCEL_PATH = "test_resumes_output.xlsx"

def test_excel_manager():
    print("\n--- Testing Excel Manager ---")
    
    # 1. Reset file
    excel_manager.reset_excel_file(TEST_EXCEL_PATH)
    assert not os.path.exists(TEST_EXCEL_PATH), "Failed to delete old test excel"
    print("[OK] Reset test Excel file successfully.")

    # 2. Load empty
    df = excel_manager.load_excel_data(TEST_EXCEL_PATH)
    assert df.empty, "DataFrame should be empty initially"
    assert list(df.columns) == excel_manager.COLUMNS, "Columns do not match schema"
    print("[OK] Initialized empty Excel sheet with correct columns.")

    # 3. Append row
    dummy_candidate = {
        "File Name": "candidate1.pdf",
        "Full Name": "Jane Doe",
        "Phone Number": "+919876543210",
        "Email": "jane.doe@example.com",
        "Skills": "Python, Sql, Pandas",
        "Education": "B.Tech CSE",
        "College Name": "IIT Bombay",
        "Experience": "2 Years",
        "Applied Role": "Software Developer"
    }
    
    saved_row = excel_manager.append_candidate_to_excel(dummy_candidate, TEST_EXCEL_PATH)
    assert saved_row["S.No"] == 1, "S.No should be 1"
    assert saved_row["Full Name"] == "Jane Doe", "Full Name mismatch"
    
    df_after = excel_manager.load_excel_data(TEST_EXCEL_PATH)
    assert len(df_after) == 1, "Should have 1 row in Excel"
    print("[OK] Appended a candidate row successfully.")

    # 4. Update field
    success = excel_manager.update_candidate_field(1, "Applied Role", "Senior Developer", TEST_EXCEL_PATH)
    assert success, "Field update failed"
    df_updated = excel_manager.load_excel_data(TEST_EXCEL_PATH)
    assert df_updated.iloc[0]["Applied Role"] == "Senior Developer", "Field update check failed"
    print("[OK] Updated a candidate field successfully.")

    # 5. Delete candidate
    success_del = excel_manager.delete_candidate(1, TEST_EXCEL_PATH)
    assert success_del, "Deletion failed"
    df_empty_again = excel_manager.load_excel_data(TEST_EXCEL_PATH)
    assert len(df_empty_again) == 0, "Excel should be empty after deletion"
    print("[OK] Deleted a candidate row successfully.")

    # Cleanup
    excel_manager.reset_excel_file(TEST_EXCEL_PATH)

def test_reader_agent():
    print("\n--- Testing Document Reader Agent (Local Extraction) ---")
    
    dummy_resume = "dummy_resume.docx"
    if not os.path.exists(dummy_resume):
        print(f"Skipping local reader test: {dummy_resume} does not exist in workspace")
        return
        
    reader = AIDocumentReaderAgent(api_key="")
    with open(dummy_resume, "rb") as f:
        file_bytes = f.read()
        
    result = reader.process(file_bytes, dummy_resume, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    
    assert result["file_name"] == dummy_resume, "File name mismatch"
    assert not result["is_scanned"], "Word files should not be flagged as scanned"
    assert len(result["extracted_text"]) > 100, "Should extract text content from Word document"
    print(f"[OK] Local Word text extraction success: extracted {len(result['extracted_text'])} chars.")
    print("Sample text extracted:")
    print(result["extracted_text"][:200].replace('\n', ' '))

def test_validation_agent():
    print("\n--- Testing Validation Agent (Fallback and Formatting) ---")
    
    validator = ValidationAgent()
    
    # Test case where Gemini returned incomplete details, forcing fallback on local regex
    raw_text = """
    Resume of G. Sarath Babu
    Mobile: +91 98765 43210
    Email: sarath.babu@gmail.com
    Highest Qualification: Master of Computer Applications (MCA)
    Experience: 3 years of experience as software engineer.
    Skills: Java, React, SQL.
    """
    
    reader_output = {
        "file_name": "sarath_resume.pdf",
        "extracted_text": raw_text
    }
    
    # Mock output where Gemini failed or returned blank fields
    extracted_data = {
        "Full Name": "",  # Blank, should trigger regex fallback
        "Phone Number": "", # Blank, should trigger phonenumbers fallback
        "Email": "sarath.babu(at)gmail.com",  # Malformed, should clean it or trigger fallback
        "Skills": ["Java", "React", "SQL"],  # List, should flatten to comma-separated string
        "Education": "",  # Blank, should trigger priority fallback
        "College Name": "Unknown College",  # Should clean to standard
        "Experience": "",  # Blank, should clean
        "Applied Role": ""  # Blank, should clean
    }
    
    validated = validator.process(extracted_data, reader_output)
    
    # Assertions
    assert validated["Full Name"] in ["G. Sarath Babu", "G Sarath Babu"], f"Name fallback failed: {validated['Full Name']}"
    assert validated["Email"] == "sarath.babu@gmail.com", f"Email cleaning failed: {validated['Email']}"
    assert "9876543210" in validated["Phone Number"].replace(" ", ""), f"Phone fallback failed: {validated['Phone Number']}"
    assert validated["Skills"] == "Java, React, SQL", f"Skills flattening failed: {validated['Skills']}"
    assert validated["Education"] == "MCA", f"Education fallback failed: {validated['Education']}"
    assert validated["Applied Role"] == "General Candidate", f"Applied Role formatting failed: {validated['Applied Role']}"
    print("[OK] Validation Agent fallback and formatting tested successfully.")

if __name__ == "__main__":
    test_excel_manager()
    test_reader_agent()
    test_validation_agent()
    print("\nALL TESTS PASSED!")
