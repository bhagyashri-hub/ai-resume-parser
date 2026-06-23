import re
import spacy
import phonenumbers


# ================= SAFE SPACY LOAD (LOW RAM) =================
try:
    nlp = spacy.load(
        "en_core_web_sm",
        disable=["parser", "tagger", "lemmatizer"]
    )
except:
    nlp = None


# ================= COMMON CLEANERS =================

def clean_text(text):
    text = text.replace("|", " ")
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


# ================= EMAIL =================

def normalize_text_for_email(text):

    # Fix OCR glued domains
    text = re.sub(r'(\.com|\.in|\.org|\.net)([A-Z])', r'\1 \2', text)

    # Replace OCR mistakes
    text = text.replace(" @ ", "@")
    text = text.replace(" . ", ".")
    text = text.replace("(at)", "@")
    text = text.replace("[at]", "@")
    text = text.replace("(dot)", ".")
    text = text.replace("[dot]", ".")

    return text


def extract_email(text):

    text = normalize_text_for_email(text)

    pattern = r'\b[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}\b'

    matches = re.findall(pattern, text, re.IGNORECASE)

    # Remove duplicates + unrealistic long strings
    emails = {
        m.lower()
        for m in matches
        if len(m) < 50
    }

    return list(emails)


# ================= PHONE =================

def extract_phone(text):

    phones = set()

    try:
        for match in phonenumbers.PhoneNumberMatcher(text, "IN"):
            number = phonenumbers.format_number(
                match.number,
                phonenumbers.PhoneNumberFormat.E164
            )
            phones.add(number)
    except:
        pass

    # Fallback regex (OCR sometimes breaks spacing)
    fallback = re.findall(r'\+?\d[\d\s\-]{8,15}\d', text)

    for f in fallback:
        digits = re.sub(r'\D', '', f)
        if 10 <= len(digits) <= 13:
            phones.add("+" + digits if not digits.startswith("+") else digits)

    return list(phones)


# ================= EDUCATION =================

DEGREE_PATTERNS = {
    "PhD": ["phd", "doctor of philosophy"],
    "MBA": ["mba", "master of business administration"],
    "M.Tech": ["m.tech", "mtech", "master of technology"],
    "M.E": ["m.e", "master of engineering"],
    "MCA": ["mca", "master of computer applications"],
    "M.Sc": ["m.sc", "msc", "master of science"],
    "B.Tech": ["b.tech", "btech", "bachelor of technology"],
    "B.E": ["b.e", "be ", "bachelor of engineering"],
    "B.Sc": ["b.sc", "bsc", "bachelor of science"],
    "BCA": ["bca", "bachelor of computer applications"]
}


def extract_education(text):

    text_lower = text.lower()

    found = []

    for degree, patterns in DEGREE_PATTERNS.items():
        for p in patterns:
            if p in text_lower:
                found.append(degree)
                break

    if not found:
        return None

    # Return highest qualification
    priority = list(DEGREE_PATTERNS.keys())
    for degree in priority:
        if degree in found:
            return degree

    return found[0]


# ================= NAME =================

BLACKLIST = [
    "engineering", "college", "university", "institute",
    "technologies", "technology", "solutions", "systems",
    "pvt", "ltd", "limited", "company", "resume",
    "curriculum", "vitae", "profile", "career", "objective",
    "summary", "mail", "email", "address", "contact", "experience",
    "safety", "officer", "ehs", "professional", "iso", "location",
    "phone", "willing", "relocate", "india",
    # 🆕 Added
    "diploma", "degree", "bachelor", "master", "b.tech", "m.tech",
    "maintenance", "operation", "production", "management", "services",
    "well", "also", "dist", "village", "mandal", "nagar", "road",
    "post", "taluk", "taluka", "district", "state", "country",
    "near", "behind", "opposite", "beside",
    "skills", "skill", "qualification", "qualifications", "key"
]

# 🆕 Phrase-level blacklist — reject if line contains these multi-word patterns
PHRASE_BLACKLIST = [
    "as well as", "such as", "along with", "responsible for",
    "knowledge of", "experience in", "worked as", "working as",
    "s/o", "d/o", "w/o", "son of", "daughter of", "wife of",  # reject full S/O lines
]

def looks_like_name(text):
    text_clean = text.lower().strip()
    text_clean_nodot = text_clean.replace(".", " ").strip()
    words = text_clean_nodot.split()

    if not (2 <= len(words) <= 4):
        return False
    if re.search(r"\d|[@_:/]", text):
        return False
    if any(bad in text_clean_nodot for bad in BLACKLIST):
        return False
    if ":" in text:
        return False

    # 🆕 Reject phrase-blacklisted patterns
    if any(phrase in text_clean for phrase in PHRASE_BLACKLIST):
        return False

    alpha_words = [w for w in words if w.isalpha()]
    if len(alpha_words) < 2:
        return False

    # 🆕 Reject if any single word is a known non-name word (catches "Krishna Dist")
    non_name_words = {
        "dist", "village", "mandal", "nagar", "road", "post", "pin",
        "taluk", "district", "state", "near", "the", "and", "for",
        "with", "from", "well", "also", "maintenance", "operation",
        "diploma", "degree", "sir", "shri", "mr", "mrs", "ms", "dr"
    }
    if any(w in non_name_words for w in words):
        return False

    return True


def extract_so_name(line):
    """
    🆕 FIXED: Extract the candidate's name which appears BEFORE S/O marker.
    The name AFTER S/O is the father's name — do NOT return that.
    
    e.g., "G. SARATH BABU, S/o TAJUDDIN BABA" → return "G. Sarath Babu"
    """
    # Pattern: <candidate name> , S/O <father name>
    pattern_before = r'^([A-Za-z][A-Za-z\s.]{2,35}?),?\s+[SsDdWw][/\.][Oo][\s.]'
    match = re.search(pattern_before, line)
    if match:
        candidate = match.group(1).strip().rstrip(",").strip()
        if looks_like_name(candidate):
            return candidate.title()

    # 🆕 DO NOT extract the name after S/O — that is father's name, not candidate's
    # (Removed the pattern_after block entirely)

    return None


def clean_inline_name(line):
    """Handle lines where name is mixed with email/phone on same line."""
    line = re.sub(r'^(resume|cv|curriculum vitae|profile)\s*(of|for)?\s*', '', line, flags=re.IGNORECASE).strip()
    line = re.sub(r'\s*[Ee][-\s]?[Mm]ail\s*[–:\-]?\s*\S+@\S+', '', line)
    line = re.sub(r'\s*(Ph|Phone|Mobile|Tel|Mo)\s*[-–:\.]*\s*[\d\s/+\-]+', '', line, flags=re.IGNORECASE)
    line = re.sub(r'\s*\S+@\S+', '', line)
    line = line.split('|')[0]
    # 🆕 Also cut at S/O marker — don't include father's info
    line = re.split(r'\s+[SsDdWw][/\.][Oo][\s.]', line)[0]
    line = line.strip().rstrip(",-").strip()
    return line


def email_cross_check_should_skip(candidate_name_flat, full_text):
    """Only skip if name is short AND ambiguously matches email user."""
    email_match = re.search(r'([a-zA-Z0-9._%+-]+)@', full_text)
    if not email_match:
        return False
    email_user = re.sub(r'\d+', '', email_match.group(1)).lower()
    combined_name = candidate_name_flat.lower()
    if combined_name in email_user and len(combined_name) >= 8:
        return False  # Long match = real name, keep it
    if combined_name in email_user and len(combined_name) < 8:
        return True   # Short/ambiguous, skip
    return False


address_keywords = [
    "post", "pincode", "pin", "mobile", "tq", "dist",
    "at ", "no ", "road", "nagar", "street", "village",
    "mandal", "district", "taluk", "taluka", "s/o", "d/o", "w/o"
]


def extract_name(text):
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    cv_header_keywords = ["curriculum", "resume", "vitae"]
    cv_header_index = None

    for i, line in enumerate(lines[:12]):
        raw_lower = line.lower()

        # Skip CV/Resume heading lines unless they contain the candidate name (e.g. "Resume of...")
        if any(word in raw_lower for word in cv_header_keywords):
            cleaned_temp = re.sub(r'^(resume|cv|curriculum vitae|profile)\s*(of|for)?\s*', '', line, flags=re.IGNORECASE).strip()
            if cleaned_temp.lower() == line.lower():
                if cv_header_index is None:
                    cv_header_index = i
                continue

        # 🆕 Skip lines that are clearly address/relation lines
        if any(kw in raw_lower for kw in address_keywords):
            # But still try to extract candidate name if S/O pattern present
            so_name = extract_so_name(line)
            if so_name:
                return so_name
            continue  # Skip the rest of processing for this line

        # S/O check for lines without address keywords
        so_name = extract_so_name(line)
        if so_name:
            return so_name

        # Inline name clean
        cleaned = clean_inline_name(line)
        cleaned_normalized = re.sub(r'[^\w\s.]', '', cleaned).replace(".", " ").strip()
        if looks_like_name(cleaned_normalized):
            if not email_cross_check_should_skip(cleaned_normalized.replace(" ", "").lower(), text):
                return cleaned_normalized.title()

        # Plain line check
        plain = re.sub(r'[^\w\s.]', '', line).replace(".", " ").strip()
        if looks_like_name(plain):
            if not email_cross_check_should_skip(plain.replace(" ", "").lower(), text):
                return plain.title()

    # Extended scan for two-column PDFs (like VINOD PATTAR case)
    for line in lines[3:25]:
        raw_lower = line.lower()
        if any(kw in raw_lower for kw in address_keywords):
            continue
        if any(kw in raw_lower for kw in BLACKLIST):
            continue
        if re.search(r'\d', line):
            continue
        if ":" in line or "@" in line:
            continue
        # 🆕 Skip lines with too many words (likely skill/description sentences)
        word_count = len(line.split())
        if word_count > 5:
            continue

        plain = re.sub(r'[^\w\s.]', '', line).replace(".", " ").strip()
        if looks_like_name(plain):
            return plain.title()

    # Post-header scan
    if cv_header_index is not None:
        for line in lines[cv_header_index + 1: cv_header_index + 6]:
            so_name = extract_so_name(line)
            if so_name:
                return so_name
            cleaned = clean_inline_name(line)
            cleaned_normalized = re.sub(r'[^\w\s.]', '', cleaned).replace(".", " ").strip()
            if looks_like_name(cleaned_normalized):
                return cleaned_normalized.title()

    # Email fallback
    email_match = re.search(r'([a-zA-Z0-9._%+-]+)@', text)
    if email_match:
        user = re.sub(r'\d+', '', email_match.group(1))
        user = user.replace(".", " ").replace("_", " ")
        parts = [p for p in user.split() if p.isalpha()]
        if 1 <= len(parts) <= 3:
            return " ".join(p.capitalize() for p in parts)

    # NLP fallback
    if nlp:
        try:
            doc = nlp(text[:1000])
            for ent in doc.ents:
                if ent.label_ == "PERSON":
                    if looks_like_name(ent.text):
                        return ent.text.title()
        except:
            pass

    return ""

# ================= PAN =================

def detect_pan(text):

    match = re.search(r'\b[A-Z]{5}[0-9]{4}[A-Z]\b', text.upper())

    if not match:
        return None

    pan = match.group()

    # Optional strict format validation
    if pan[0:5].isalpha() and pan[5:9].isdigit():
        return pan

    return None


# ================= AADHAAR =================

def detect_aadhaar(text):

    match = re.search(r'\b\d{4}\s?\d{4}\s?\d{4}\b', text)

    if not match:
        return None

    number = re.sub(r"\s", "", match.group())

    # Basic validation
    if len(number) == 12:
        return number

    return None
