import re
import spacy

# ================= SAFE SPACY LOAD =================
try:
    nlp = spacy.load("en_core_web_sm", disable=["parser", "tagger", "lemmatizer"])
except Exception:
    nlp = None

# ================= CONSTANTS =================

INDIAN_STATES = [
    "andhra pradesh", "arunachal pradesh", "assam", "bihar", "chhattisgarh",
    "goa", "gujarat", "haryana", "himachal pradesh", "jharkhand",
    "karnataka", "kerala", "madhya pradesh", "maharashtra", "manipur",
    "meghalaya", "mizoram", "nagaland", "odisha", "punjab",
    "rajasthan", "sikkim", "tamil nadu", "telangana", "tripura",
    "uttar pradesh", "uttarakhand", "west bengal",
    "andaman and nicobar", "chandigarh", "dadra and nagar haveli",
    "daman and diu", "delhi", "lakshadweep", "puducherry", "ladakh",
    "jammu and kashmir"
]

STATE_ABBREVIATIONS = {
    "ap": "Andhra Pradesh", "ar": "Arunachal Pradesh", "as": "Assam",
    "br": "Bihar", "cg": "Chhattisgarh", "ga": "Goa", "gj": "Gujarat",
    "hr": "Haryana", "hp": "Himachal Pradesh", "jh": "Jharkhand",
    "ka": "Karnataka", "kl": "Kerala", "mp": "Madhya Pradesh",
    "mh": "Maharashtra", "mn": "Manipur", "ml": "Meghalaya",
    "mz": "Mizoram", "nl": "Nagaland", "od": "Odisha", "pb": "Punjab",
    "rj": "Rajasthan", "sk": "Sikkim", "tn": "Tamil Nadu",
    "tg": "Telangana", "tr": "Tripura", "up": "Uttar Pradesh",
    "uk": "Uttarakhand", "wb": "West Bengal", "dl": "Delhi",
    "jk": "Jammu and Kashmir"
}

INDIAN_DISTRICTS = [
    # Tamil Nadu
    "chennai", "coimbatore", "madurai", "tiruchirappalli", "trichy", "salem",
    "tirunelveli", "vellore", "erode", "theni", "dindigul", "thanjavur",
    "cuddalore", "kanchipuram", "villupuram", "namakkal", "karur",
    "tiruppur", "krishnagiri", "dharmapuri", "perambalur", "ariyalur",
    "pudukkottai", "ramanathapuram", "virudhunagar", "tenkasi",
    "chengalpattu", "ranipet", "tirupattur", "kallakurichi",
    # Karnataka
    "bangalore", "bengaluru", "mysuru", "mysore", "hubli", "dharwad",
    "mangalore", "mangaluru", "belagavi", "kalaburagi", "ballari",
    "davanagere", "shivamogga", "tumakuru", "udupi", "hassan",
    # Andhra Pradesh
    "visakhapatnam", "vizag", "vijayawada", "guntur", "nellore",
    "kurnool", "kakinada", "tirupati", "rajahmundry", "kadapa",
    "anantapur", "eluru", "ongole", "srikakulam", "vizianagaram",
    # Telangana
    "hyderabad", "warangal", "nizamabad", "karimnagar", "khammam",
    "ramagundam", "mahbubnagar", "nalgonda", "adilabad",
    # Maharashtra
    "mumbai", "pune", "nagpur", "nashik", "aurangabad", "solapur",
    "amravati", "kolhapur", "akola", "latur", "jalgaon", "chandrapur",
    "thane", "nanded", "sangli", "satara", "ahmednagar",
    # Kerala
    "thiruvananthapuram", "kochi", "ernakulam", "kozhikode", "calicut",
    "thrissur", "kollam", "palakkad", "alappuzha", "kannur",
    "kasaragod", "malappuram", "pathanamthitta", "idukki", "wayanad",
    # Uttar Pradesh
    "lucknow", "kanpur", "agra", "varanasi", "meerut", "allahabad",
    "prayagraj", "ghaziabad", "noida", "bareilly", "aligarh", "gorakhpur",
    # Others
    "kolkata", "howrah", "patna", "ranchi", "bhopal", "indore",
    "jaipur", "jodhpur", "udaipur", "ahmedabad", "surat", "vadodara",
    "rajkot", "chandigarh", "ludhiana", "amritsar", "jalandhar",
    "dehradun", "guwahati", "bhubaneswar", "cuttack", "raipur",
    "jammu", "srinagar", "shimla", "gurugram", "gurgaon", "faridabad"
]

ADDRESS_HINT_WORDS = [
    "street", "road", "nagar", "colony", "layout", "lane", "block",
    "sector", "phase", "building", "apartment", "flat", "floor", "tower",
    "near", "opposite", "village", "post", "district", "native place",
    "door no", "house no", "gate no", "residence", "permanent address",
    "present address", "current address", "mailing address",
    "correspondence address", "communication address",
    "taluk", "tehsil", "mandal", "plot no", "room no", "survey no",
    "main road", "bypass", "highway", "industrial area", "civil lines",
    "housing board", "society", "compound", "complex", "enclave", "vihar",
    "garden", "park", "avenue", "market", "bazaar", "chowk",
    "p.o.", "po box", "c/o", "s/o", "d/o", "w/o", "care of",
    "ward no", "ward", "gali", "mohalla", "basti",
    "puram", "pet", "palya", "halli", "guda", "peta",
    "opp", "behind", "beside", "next to", "pincode", "pin code",
    "1st cross", "2nd cross", "3rd cross", "extension", "extn","HO/NO"
    ]

NOISE_WORDS = [
    "resume", "curriculum vitae", "objective", "profile",
    "education", "experience", "skills", "certifications",
    "january", "february", "march", "april", "june", "july",
    "august", "september", "october", "november", "december",
    "challenging", "responsible", "position", "organization",
    "contribute", "client", "designation", "linkedin", "github",
    "hobbies", "interests", "marital", "nationality", "religion"
]

STOP_WORDS = [
    "declaration", "education", "academic", "experience", "skills",
    "objective", "strengths", "summary", "projects", "internship",
    "training", "certifications", "achievements", "awards",
    "publications", "references"
]

PERSONAL_FIELDS = [
    "name", "father", "mother", "dob", "date of birth",
    "age", "gender", "nationality", "marital", "blood group",
    "religion", "caste", "languages known", "hobbies"
]

TECH_BLACKLIST = [
    "react", "java", "python", "devops", "django", "flask",
    "aws", "azure", "node", "angular", "vue", "html", "css",
    "sql", "linux", "docker", "kubernetes", "git", "selenium",
    "spring", "mysql", "mongodb", "tensorflow", "pytorch", "php"
]

# Compiled regex patterns
PINCODE_RE      = re.compile(r"\b[1-9]\d{5}\b")
PHONE_RE        = re.compile(r"\b\d{10}\b")
YEAR_RANGE_RE   = re.compile(r"\b(19|20)\d{2}\s*[-–]\s*(19|20)\d{2}\b")
YEAR_END_RE     = re.compile(r"\b(19|20)\d{2}\s*$")
ALL_CAPS_RE     = re.compile(r"^[A-Z][A-Z\s.\-]{4,}$")
ADDR_LABEL_RE   = re.compile(
    r"(?i)[\W]*"
    r"(?:permanent\s+address|current\s+address|residential\s+address|"
    r"correspondence\s+address|present\s+address|address\s+for\s+communication|"
    r"communication\s+address|mailing\s+address|address)"
    r"\s*[:\-]?\s*",
    re.MULTILINE,
)

# ============================================================
#  LINE-LEVEL HELPERS
# ============================================================

def _is_noise(line: str) -> bool:
    """True if this line is clearly NOT an address (email, phone, dates, etc.)."""
    lo = line.lower()
    return (
        "@" in line
        or bool(PHONE_RE.search(line))
        or bool(YEAR_RANGE_RE.search(line))      # work history: 2019-2022
        or bool(YEAR_END_RE.search(line))         # line ending in a year
        or any(n in lo for n in NOISE_WORDS)
    )


def _is_stop(line: str) -> bool:
    """True if this line signals a resume section heading — stop scanning."""
    lo = line.lower()
    return any(s in lo for s in STOP_WORDS)


def _is_name_line(line: str) -> bool:
    """True if this line looks like a candidate name, not an address."""
    # ALL-CAPS short line (e.g. RAMESH KUMAR)
    if ALL_CAPS_RE.match(line) and len(line.split()) <= 5:
        return True
    # Title-case short line with no digits, commas, or address words
    words = line.split()
    return (
        len(words) <= 5
        and all(w[0].isupper() for w in words if w and w[0].isalpha())
        and not _has_address_signal(line)
        and not any(c.isdigit() for c in line)
        and not any(c in line for c in ("@", "|", ","))
    )


def _has_address_signal(line: str) -> bool:
    """True if this line contains any address indicator."""
    lo = line.lower()
    if PINCODE_RE.search(line):
        return True
    # Use word boundaries for short state names to avoid false hits (e.g. 'up' in 'Gupta')
    for state in INDIAN_STATES:
        pat = (r"\b" + re.escape(state) + r"\b") if len(state) <= 3 else re.escape(state)
        if re.search(pat, lo):
            return True
    for district in INDIAN_DISTRICTS:
        if re.search(r"\b" + re.escape(district) + r"\b", lo):
            return True
    return any(hint in lo for hint in ADDRESS_HINT_WORDS)


def _clean_line(line: str) -> str:
    """Strip address labels, pincode text, leading symbols, and extra spaces."""
    line = ADDR_LABEL_RE.sub("", line)
    line = re.sub(r"(?i)\b(pin\s*code|pincode)\s*[-:]?\s*\d{6}\b", "", line)
    line = re.sub(PINCODE_RE, "", line)
    line = re.sub(r"^[\W_]+", "", line)          # leading ➢ • – * etc.
    return line.strip(" ,.-|;:")

# ============================================================
#  PINCODE
# ============================================================

def extract_pincode(text: str) -> str:
    match = PINCODE_RE.search(text)
    return match.group() if match else ""

# ============================================================
#  STATE
# ============================================================

def extract_state(text: str) -> str:
    lo = text.lower()

    # Full state names (longest first to avoid partial matches)
    for state in sorted(INDIAN_STATES, key=len, reverse=True):
        pat = (r"\b" + re.escape(state) + r"\b") if len(state) <= 3 else re.escape(state)
        if re.search(pat, lo):
            return state.title()

    # 2-letter abbreviation (e.g. TN, KA) — only in first 800 chars
    m = re.search(r"\b([A-Z]{2})\b", text[:800])
    if m and m.group(1).lower() in STATE_ABBREVIATIONS:
        return STATE_ABBREVIATIONS[m.group(1).lower()]

    return ""

# ============================================================
#  CITY
# ============================================================

def extract_city(text: str) -> str:

    # Pattern 1: known district/city list (most reliable — check first)
    lo = text.lower()
    for district in sorted(INDIAN_DISTRICTS, key=len, reverse=True):
        if re.search(r"\b" + re.escape(district) + r"\b", lo):
            return district.title()

    # Pattern 2: "City, State"
    m = re.search(
        r"([A-Za-z][A-Za-z\s]{2,20}),?\s*(?:" + "|".join(re.escape(s) for s in INDIAN_STATES) + r")",
        text, re.IGNORECASE
    )
    if m:
        city = m.group(1).strip().split(",")[-1].strip()
        if city.lower() not in TECH_BLACKLIST and len(city) > 2:
            return city.title()

    # Pattern 3: "City – 600096"
    m = re.search(r"([A-Za-z][A-Za-z\s]{2,25})[–\-]\s*(?=\d{6})", text)
    if m:
        city = m.group(1).strip().split(",")[-1].strip()
        if city.lower() not in TECH_BLACKLIST and city.lower() not in ("pin", "pincode", "pin code"):
            return city.title()

    # Pattern 4: spaCy NER fallback
    if nlp:
        try:
            doc = nlp(text[:1000])
            for ent in doc.ents:
                if ent.label_ in ("GPE", "LOC"):
                    city = ent.text.strip()
                    if (
                        city.lower() not in TECH_BLACKLIST
                        and city.lower() not in ("india", "bharat")
                        and not re.search(r"\d", city)
                        and len(city) > 2
                    ):
                        return city.title()
        except Exception:
            pass

    return ""

# ============================================================
#  LABELED ADDRESS DETECTOR
#  (handles "Address: value" anywhere in the document)
# ============================================================

def find_labeled_address(text: str) -> str | None:
    """
    Finds 'Address: ...' style labels anywhere in the text.
    Captures value on same line + up to 2 continuation lines.
    Returns the raw combined string, or None if not found.
    """
    m = re.search(
        r"(?i)(?:permanent\s+address|current\s+address|residential\s+address|"
        r"address\s+for\s+communication|address)\s*[:\-]\s*(.+)",
        text,
    )
    if not m:
        return None

    # Grab matched value + next 2 lines for multi-line addresses
    block = text[m.start():]
    lines = [l.strip() for l in block.split("\n") if l.strip()][:3]
    return " ".join(lines)

# ============================================================
#  SMART ADDRESS DETECTOR  (header-area scan)
# ============================================================

def find_address_near_contact_info(text: str) -> str:
    """
    Scans the top 25 lines of the resume for address-like content
    near the contact info block (name, phone, email area).
    Returns a comma-joined address string, or ''.
    """
    lines = [l.strip() for l in text.split("\n") if l.strip()][:25]

    for i, line in enumerate(lines):
        lower = line.lower()                    

        if _is_stop(line):
            break

        if _is_noise(line) or _is_name_line(line):
            continue

        if not _has_address_signal(line):
            continue

        # Found an address anchor — collect this line + up to 3 continuation lines
        address_parts = []
        for part in lines[i: i + 4]:
            if _is_stop(part) or _is_noise(part):
                break
            cleaned = _clean_line(part)
            if cleaned:
                address_parts.append(cleaned)

        if address_parts:
            return ", ".join(address_parts)

    return ""

# ============================================================
#  MAIN EXTRACT ADDRESS
# ============================================================

def extract_address(text: str) -> dict:
    """
    Full address extractor. Tries 4 strategies in order:
      1. Top-of-resume header scan (contact info area)
      2. Pipe-separated inline contact line  e.g. "Name | City, State | phone"
      3. Labeled address block  e.g. "Address: ..." or "Permanent Address: ..."
      4. Pincode / state / city fallback
    Returns: { address, city, state, country, pincode }
    """
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    address_parts = []

    # ── STRATEGY 1: top-of-resume header scan (first 20 lines) ──────────────
    for i, line in enumerate(lines[:20]):
        lower = line.lower()

        if _is_stop(line):
            break
        if _is_noise(line) or _is_name_line(line):
            continue
        # Skip pipe contact lines here — handled in strategy 2
        if "|" in line and not PINCODE_RE.search(line):
            if not any(s in lower for s in INDIAN_STATES):
                continue

        if (
            PINCODE_RE.search(line)
            or "india" in lower
            or any(state in lower for state in INDIAN_STATES)
            or any(word in lower for word in ADDRESS_HINT_WORDS)
        ):
            cleaned = _clean_line(line)
            if cleaned and len(cleaned) > 2:
                address_parts.append(cleaned)
                # Collect up to 3 continuation lines
                for cont in lines[i + 1: i + 4]:
                    if _is_stop(cont) or _is_noise(cont):
                        break
                    if any(p in cont.lower() for p in PERSONAL_FIELDS):
                        break
                    cont_clean = _clean_line(cont)
                    if cont_clean and len(cont_clean) > 2:
                        address_parts.append(cont_clean)
                break

    # ── STRATEGY 2: pipe-separated inline contact line ───────────────────────
    # Handles: "ANANYA SINGH | email | 9090909090 | Patna, Bihar"
    if not address_parts:
        for line in lines[:10]:
            if "|" not in line:
                continue
            for segment in line.split("|"):
                seg = segment.strip()
                if not _is_noise(seg) and _has_address_signal(seg) and len(seg) > 3:
                    cleaned = _clean_line(seg)
                    if cleaned:
                        address_parts.append(cleaned)
                    break
            if address_parts:
                break

    # ── STRATEGY 3: labeled address block anywhere in document ───────────────
    # Handles: "Address: ..." / "Permanent Address: ..." / bottom personal details
    if not address_parts:
        for i, line in enumerate(lines):
            if not re.search(r"(?i)\b(permanent\s+address|current\s+address|"
                             r"residential\s+address|address)\b", line):
                continue

            # Value on same line as label
            inline = _clean_line(line)
            if inline and not _is_noise(inline) and len(inline) > 2:
                address_parts.append(inline)

            # Value on following lines (multi-line address)
            for part in lines[i + 1: i + 5]:
                lower_part = part.lower()
                if _is_stop(part):
                    break
                if any(p in lower_part for p in PERSONAL_FIELDS):
                    # Another personal field label — stop UNLESS it's another address type
                    if not re.search(r"(?i)\baddress\b", part):
                        break
                if _is_noise(part):
                    continue
                # Skip lines that are clearly other label fields (contain ":" but no address words)
                if ":" in part and not _has_address_signal(part):
                    continue
                part_clean = _clean_line(part)
                if part_clean and len(part_clean) > 2:
                    address_parts.append(part_clean)
                if len(address_parts) >= 4:
                    break
            break

    # ── STRATEGY 4: spaCy NER on the header block ────────────────────────────
    if not address_parts and nlp:
        try:
            header = text[:1200]
            doc = nlp(header)
            geo_lines = []
            for ent in doc.ents:
                if ent.label_ in ("GPE", "LOC") and ent.text.lower() not in ("india", "bharat"):
                    geo_lines.append(ent.text.strip())
            if geo_lines:
                # Find the actual resume line that contains these entities
                for line in lines[:20]:
                    if _is_noise(line) or _is_name_line(line):
                        continue
                    hits = sum(1 for g in geo_lines if g.lower() in line.lower())
                    if hits >= 1 and _has_address_signal(line):
                        address_parts.append(_clean_line(line))
                        break
        except Exception:
            pass

    # ── STRATEGY 5: pincode line fallback ────────────────────────────────────
    if not address_parts:
        for line in lines:
            if PINCODE_RE.search(line) and not _is_noise(line):
                cleaned = _clean_line(line)
                if cleaned and len(cleaned) > 3:
                    address_parts.append(cleaned)
                    break

    # ── STRATEGY 6: state / district fallback ────────────────────────────────
    if not address_parts:
        for line in lines:
            if _is_noise(line) or _is_name_line(line):
                continue
            lo = line.lower()
            if any(s in lo for s in INDIAN_STATES) or \
               any(re.search(r"\b" + re.escape(d) + r"\b", lo) for d in INDIAN_DISTRICTS):
                address_parts.append(line.strip())
                break

    # ── Build result ──────────────────────────────────────────────────────────
    # Deduplicate while preserving order
    seen, unique_parts = set(), []
    for p in address_parts:
        key = p.lower().strip()
        if key and key not in seen:
            seen.add(key)
            unique_parts.append(p)

    full_address = ", ".join(unique_parts)

    city    = extract_city(full_address)    or extract_city(text[:2000])
    state   = extract_state(full_address)   or extract_state(text[:2000])
    pincode = extract_pincode(text)

    return {
        "address": full_address,
        "city":    city,
        "state":   state,
        "country": "India",
        "pincode": pincode,
    }

# ============================================================
#  CURRENT LOCATION  (lightweight — city+state from header)
# ============================================================

def extract_current_location(text: str) -> dict | None:
    """
    Extracts just city + state from the resume header (first 1200 chars).
    Returns None if nothing found.
    """
    header = text[:1200]
    city  = extract_city(header)
    state = extract_state(header)

    if not city and not state:
        return None

    return {
        "city":    city,
        "state":   state,
        "country": "India",
    }

# ============================================================
#  TEST HARNESS  —  python address_extractor.py
# ============================================================

if __name__ == "__main__":

    SAMPLES = {

        "top_after_name": """
RAMESH KUMAR
No. 14, 2nd Cross, Indira Nagar, Bangalore - 560038, Karnataka
ramesh@email.com | 9876543210
OBJECTIVE
Seeking a challenging position...
""",
        "top_with_label": """
Priya Sharma
Address: Flat 202, Sunrise Apartment, Sector 21, Noida, Uttar Pradesh - 201301
Phone: 9988776655
EDUCATION
""",
        "top_multiline": """
Arun Venkatesh
HR Manager | Chennai

Plot 5, Anna Nagar West,
Chennai, Tamil Nadu 600040
arun.v@company.com
EXPERIENCE
""",
        "bottom_personal_details": """
Work Experience
Company A - 2019-2022
...

Personal Details
Name: Kiran Reddy
Date of Birth: 12-05-1997
Gender: Male
Address: H.No 45, Srinagar Colony, Hyderabad, Telangana - 500073
Marital Status: Single
""",
        "symbolic_prefix": """
Sneha Patel
Mobile: 9876543210
Email: sneha@mail.com
Address: B-12, Ashok Vihar, Phase II, Delhi - 110052
""",
        "pincode_only_line": """
Vijay Mohan
vijay@mail.com | 9123456780

Vazhudavur Road, Puducherry 605010
SKILLS
""",
        "state_no_pincode": """
Manoj Gupta
Sector 15, Rohini, New Delhi
EXPERIENCE
""",
        "mixed_inline": """
ANANYA SINGH | ananya@email.com | 9090909090 | Patna, Bihar
SUMMARY
""",
        "permanent_address_bottom": """
Technical Skills: Python, SQL
Personal Details:
Father Name: Mr. Suresh
DOB: 15/08/1995
Permanent Address: 22, Gandhi Street, Coimbatore, Tamil Nadu - 641001
""",
        "two_line_after_label": """
Suresh Babu
Current Address:
Flat No. 3B, Green Valley Apartments
Madhapur, Hyderabad - 500081
Skills:
""",
        "native_place": """
Divya Lakshmi
Native Place: Tirunelveli, Tamil Nadu
Currently residing in Bangalore
divya@mail.com | 8888888888
SKILLS
""",
        "arrow_symbol_address": """
Ravi Shankar
➢ Email: ravi@gmail.com
➢ Phone: 9123456789
➢ Address: Plot 22, New Colony, Guntur, Andhra Pradesh - 522001
EDUCATION
""",
    }

    spacy_status = "spaCy loaded" if nlp else "spaCy NOT available (regex-only mode)"
    print(f"\n[{spacy_status}]")
    print("=" * 65)

    for name, text in SAMPLES.items():
        r = extract_address(text)
        print(f"\n[{name}]")
        print(f"  Address : {r['address']}")
        print(f"  City    : {r['city']}")
        print(f"  State   : {r['state']}")
        print(f"  Pincode : {r['pincode']}")

    print("\n" + "=" * 65)
    print("\n[extract_current_location test]")
    sample = "John Peter | john@mail.com | 9876543210 | Kochi, Kerala"
    loc = extract_current_location(sample)
    print(f"  Input  : {sample}")
    print(f"  Result : {loc}")
