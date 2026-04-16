from difflib import SequenceMatcher

SAMPLE_CATEGORIES = {
    "S": "Signs & Symptoms",
    "A": "Allergies",
    "M": "Medications",
    "P": "Past History",
    "L": "Last Intake",
    "E": "Events Leading Up",
}

# Accepted answers for each patient (lowercase). Multiple aliases per patient.
PATIENT_DIAGNOSES = {
    "Julian": ["food poisoning", "stomach bug", "bad food", "spoiled food", "gastroenteritis"],
    "Emily": ["low blood sugar", "diabetes", "type 1 diabetes", "hypoglycemia", "low sugar", "diabetic"],
    "Sophia": ["allergies", "hay fever", "seasonal allergies", "pollen allergy"],
    "Camila": ["pink eye", "conjunctivitis", "eye infection"],
    "Connor": ["head lice", "lice"],
    "Ben": ["eczema", "dry skin", "dermatitis", "atopic dermatitis"],
    "Aidan": ["flu", "influenza", "the flu"],
    "Emma": ["dislocated shoulder", "shoulder dislocation", "shoulder out of socket", "dislocated arm"],
    "Lizzy": ["sprained ankle", "twisted ankle", "ankle sprain", "rolled ankle"],
    "Michaela": ["strep throat", "strep", "sore throat", "throat infection"],
    "Ian": ["twisted knee", "knee injury", "knee sprain", "torn ligament", "acl"],
    "Samira": ["broken arm", "broken wrist", "fractured arm", "fractured wrist", "wrist fracture"],
    "Ethan": ["asthma", "asthma attack"],
    "Jackson": ["common cold", "cold", "the cold", "head cold"],
    "Cynthia": ["acne", "acne breakout", "pimples", "breakout"],
    "Olivia": ["concussion", "head injury", "head trauma"],
    "Leo": ["depression", "depressed", "mental health", "sadness"],
    "Zoe": ["eye strain", "phone neck", "screen time", "digital eye strain", "neck strain"],
    "Tyler": ["sleep deprivation", "no sleep", "gaming addiction", "insomnia", "lack of sleep"],
    "Riley": ["caffeine overdose", "too much caffeine", "energy drink overdose", "caffeine toxicity", "too many energy drinks"],
    "Mason": ["broken collarbone", "fractured collarbone", "broken clavicle", "collarbone fracture"],
}

# Points
SAMPLE_POINTS_EACH = 10  # 10 per category, 60 max
DIAGNOSIS_CORRECT = 50
DIAGNOSIS_PARTIAL = 25

# Score tiers
SCORE_TIERS = [
    (90, "Expert Nurse"),
    (70, "Senior CNA"),
    (50, "CNA Trainee"),
    (0,  "Keep Practicing!"),
]

# SAMPLE classification prompt for the LLM
SAMPLE_CLASSIFICATION_PROMPT = """You are a nursing assessment classifier. Given a student's question to a patient, determine which SAMPLE assessment categories it covers.

SAMPLE categories:
S = Signs & Symptoms (asking about pain, what hurts, how they feel, symptoms)
A = Allergies (asking about allergies or reactions)
M = Medications (asking about medicines, pills, prescriptions)
P = Past History (asking about past illnesses, if this happened before, medical history)
L = Last Intake (asking about food, drink, when they last ate or drank)
E = Events Leading Up (asking what they were doing, what happened before, how it started)

Student's question: "{question}"

Reply with ONLY the matching letters (e.g., "S" or "SE" or "SL"). If none match, reply "NONE"."""


def classify_sample_from_response(response_text):
    """Parse LLM response into a set of SAMPLE category letters."""
    response_text = response_text.strip().upper()
    valid = set()
    for char in response_text:
        if char in SAMPLE_CATEGORIES:
            valid.add(char)
    return valid


def check_diagnosis(patient_name, student_guess):
    """Check student's diagnosis guess against accepted answers.
    Returns: ('correct', points), ('partial', points), or ('wrong', 0)
    """
    guess = student_guess.strip().lower()
    accepted = PATIENT_DIAGNOSES.get(patient_name, [])

    # Exact or near-exact match
    for answer in accepted:
        ratio = SequenceMatcher(None, guess, answer).ratio()
        if ratio >= 0.75:
            return "correct", DIAGNOSIS_CORRECT

    # Partial match - check if key words overlap
    guess_words = set(guess.split())
    for answer in accepted:
        answer_words = set(answer.split())
        overlap = guess_words & answer_words
        if overlap and len(overlap) >= len(answer_words) * 0.5:
            return "partial", DIAGNOSIS_PARTIAL

    return "wrong", 0


def calculate_score(sample_covered, diagnosis_result):
    """Calculate total score.
    sample_covered: set of SAMPLE letters covered
    diagnosis_result: (result_str, points) from check_diagnosis
    """
    sample_score = len(sample_covered) * SAMPLE_POINTS_EACH
    dx_score = diagnosis_result[1]
    total = sample_score + dx_score
    return {
        "sample_score": sample_score,
        "sample_count": len(sample_covered),
        "sample_total": len(SAMPLE_CATEGORIES),
        "sample_covered": sample_covered,
        "dx_result": diagnosis_result[0],
        "dx_score": dx_score,
        "total": total,
        "max_total": len(SAMPLE_CATEGORIES) * SAMPLE_POINTS_EACH + DIAGNOSIS_CORRECT,
        "tier": get_tier(total),
    }


def get_tier(score):
    """Return the tier name for a given score."""
    for threshold, name in SCORE_TIERS:
        if score >= threshold:
            return name
    return SCORE_TIERS[-1][1]
