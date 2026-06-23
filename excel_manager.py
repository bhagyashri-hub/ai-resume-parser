import os
import pandas as pd
from datetime import datetime

EXCEL_PATH = os.path.join(os.path.dirname(__file__), "resumes_output.xlsx")

COLUMNS = [
    "S.No", 
    "File Name", 
    "Full Name", 
    "Phone Number", 
    "Email", 
    "Skills", 
    "Education", 
    "College Name", 
    "Experience", 
    "Applied Role", 
    "Parsed At"
]

def load_excel_data(excel_path=EXCEL_PATH) -> pd.DataFrame:
    """Load existing master Excel file or return an empty DataFrame with core columns."""
    if os.path.exists(excel_path):
        try:
            df = pd.read_excel(excel_path, engine="openpyxl")
            # Ensure all required columns exist
            for col in COLUMNS:
                if col not in df.columns:
                    df[col] = ""
            # Reorder columns to match standard
            df = df[COLUMNS]
            # Fill NaN values with empty string
            df = df.fillna("")
            return df
        except Exception as e:
            print(f"Error reading excel: {e}")
            
    # Create empty DataFrame with standard columns
    return pd.DataFrame(columns=COLUMNS)

def save_excel_data(df: pd.DataFrame, excel_path=EXCEL_PATH):
    """Save the DataFrame to the master Excel file on disk."""
    try:
        # Re-index/normalize S.No just in case
        df["S.No"] = range(1, len(df) + 1)
        df.to_excel(excel_path, index=False, engine="openpyxl")
        return True
    except Exception as e:
        print(f"Error saving excel: {e}")
        return False

def append_candidate_to_excel(candidate_data: dict, excel_path=EXCEL_PATH) -> dict:
    """
    Append a new candidate row to the Excel file.
    Updates or creates S.No and Parsed At fields.
    """
    df = load_excel_data(excel_path)
    
    s_no = len(df) + 1
    parsed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    new_row = {
        "S.No": s_no,
        "File Name": candidate_data.get("File Name", "Unknown"),
        "Full Name": candidate_data.get("Full Name", ""),
        "Phone Number": candidate_data.get("Phone Number", ""),
        "Email": candidate_data.get("Email", ""),
        "Skills": candidate_data.get("Skills", ""),
        "Education": candidate_data.get("Education", ""),
        "College Name": candidate_data.get("College Name", ""),
        "Experience": candidate_data.get("Experience", ""),
        "Applied Role": candidate_data.get("Applied Role", ""),
        "Parsed At": parsed_at
    }
    
    # Clean the row dictionary keys to make sure they match COLUMNS exactly
    cleaned_row = {col: new_row.get(col, "") for col in COLUMNS}
    
    # Append the row
    new_df = pd.concat([df, pd.DataFrame([cleaned_row])], ignore_index=True)
    if not save_excel_data(new_df, excel_path):
        raise PermissionError("Could not write to Excel file. Please check if it is open in Microsoft Excel or another program, and close it before retrying.")
    
    return cleaned_row

def delete_candidate(s_no: int, excel_path=EXCEL_PATH) -> bool:
    """Delete a candidate from the spreadsheet by S.No and reindex S.No."""
    df = load_excel_data(excel_path)
    try:
        s_no = int(s_no)
        df = df[df["S.No"] != s_no]
        save_excel_data(df, excel_path)
        return True
    except Exception as e:
        print(f"Error deleting row: {e}")
        return False

def reset_excel_file(excel_path=EXCEL_PATH) -> bool:
    """Reset the Excel file by deleting it or clearing all rows."""
    if os.path.exists(excel_path):
        try:
            os.remove(excel_path)
            return True
        except Exception as e:
            print(f"Error deleting file: {e}")
            return False
    return True

def update_candidate_field(s_no: int, field: str, value: str, excel_path=EXCEL_PATH) -> bool:
    """Update a specific field of a candidate by their S.No."""
    if field not in COLUMNS or field == "S.No":
        return False
    
    df = load_excel_data(excel_path)
    try:
        s_no = int(s_no)
        idx = df[df["S.No"] == s_no].index
        if not idx.empty:
            df.loc[idx, field] = value
            save_excel_data(df, excel_path)
            return True
    except Exception as e:
        print(f"Error updating candidate: {e}")
    return False
