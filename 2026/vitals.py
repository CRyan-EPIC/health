import random

# Base vital signs for all 21 patients
# Each value: (base_value, unit, variance, abnormal_threshold_low, abnormal_threshold_high)
PATIENT_VITALS = {
    "Julian": {
        "HR":   (98,    "bpm",  3,   60, 100),
        "Temp": (100.2, "F",    0.2, 97.0, 99.5),
        "BP_S": (105,   "",     3,   90, 120),
        "BP_D": (68,    "",     2,   60, 80),
        "SpO2": (98,    "%",    1,   95, 100),
        "Resp": (18,    "/min", 1,   12, 20),
    },
    "Emily": {
        "HR":   (102,   "bpm",  4,   60, 100),
        "Temp": (98.1,  "F",    0.2, 97.0, 99.5),
        "BP_S": (90,    "",     3,   90, 120),
        "BP_D": (58,    "",     2,   60, 80),
        "SpO2": (98,    "%",    1,   95, 100),
        "Resp": (16,    "/min", 1,   12, 20),
    },
    "Sophia": {
        "HR":   (82,    "bpm",  2,   60, 100),
        "Temp": (98.4,  "F",    0.2, 97.0, 99.5),
        "BP_S": (108,   "",     2,   90, 120),
        "BP_D": (70,    "",     2,   60, 80),
        "SpO2": (99,    "%",    0,   95, 100),
        "Resp": (16,    "/min", 1,   12, 20),
    },
    "Camila": {
        "HR":   (80,    "bpm",  2,   60, 100),
        "Temp": (99.0,  "F",    0.2, 97.0, 99.5),
        "BP_S": (106,   "",     2,   90, 120),
        "BP_D": (68,    "",     2,   60, 80),
        "SpO2": (99,    "%",    0,   95, 100),
        "Resp": (16,    "/min", 1,   12, 20),
    },
    "Connor": {
        "HR":   (78,    "bpm",  2,   60, 100),
        "Temp": (98.6,  "F",    0.1, 97.0, 99.5),
        "BP_S": (104,   "",     2,   90, 120),
        "BP_D": (66,    "",     2,   60, 80),
        "SpO2": (99,    "%",    0,   95, 100),
        "Resp": (15,    "/min", 1,   12, 20),
    },
    "Ben": {
        "HR":   (76,    "bpm",  2,   60, 100),
        "Temp": (98.5,  "F",    0.1, 97.0, 99.5),
        "BP_S": (110,   "",     2,   90, 120),
        "BP_D": (70,    "",     2,   60, 80),
        "SpO2": (99,    "%",    0,   95, 100),
        "Resp": (16,    "/min", 1,   12, 20),
    },
    "Aidan": {
        "HR":   (100,   "bpm",  4,   60, 100),
        "Temp": (102.4, "F",    0.3, 97.0, 99.5),
        "BP_S": (100,   "",     3,   90, 120),
        "BP_D": (62,    "",     2,   60, 80),
        "SpO2": (97,    "%",    1,   95, 100),
        "Resp": (20,    "/min", 2,   12, 20),
    },
    "Emma": {
        "HR":   (108,   "bpm",  5,   60, 100),
        "Temp": (98.6,  "F",    0.1, 97.0, 99.5),
        "BP_S": (118,   "",     3,   90, 120),
        "BP_D": (76,    "",     2,   60, 80),
        "SpO2": (99,    "%",    0,   95, 100),
        "Resp": (22,    "/min", 2,   12, 20),
    },
    "Lizzy": {
        "HR":   (90,    "bpm",  3,   60, 100),
        "Temp": (98.4,  "F",    0.1, 97.0, 99.5),
        "BP_S": (110,   "",     2,   90, 120),
        "BP_D": (70,    "",     2,   60, 80),
        "SpO2": (99,    "%",    0,   95, 100),
        "Resp": (16,    "/min", 1,   12, 20),
    },
    "Michaela": {
        "HR":   (88,    "bpm",  3,   60, 100),
        "Temp": (101.8, "F",    0.3, 97.0, 99.5),
        "BP_S": (108,   "",     2,   90, 120),
        "BP_D": (68,    "",     2,   60, 80),
        "SpO2": (98,    "%",    1,   95, 100),
        "Resp": (17,    "/min", 1,   12, 20),
    },
    "Ian": {
        "HR":   (92,    "bpm",  3,   60, 100),
        "Temp": (98.6,  "F",    0.1, 97.0, 99.5),
        "BP_S": (112,   "",     2,   90, 120),
        "BP_D": (72,    "",     2,   60, 80),
        "SpO2": (99,    "%",    0,   95, 100),
        "Resp": (16,    "/min", 1,   12, 20),
    },
    "Samira": {
        "HR":   (104,   "bpm",  4,   60, 100),
        "Temp": (98.8,  "F",    0.2, 97.0, 99.5),
        "BP_S": (114,   "",     3,   90, 120),
        "BP_D": (74,    "",     2,   60, 80),
        "SpO2": (99,    "%",    0,   95, 100),
        "Resp": (18,    "/min", 1,   12, 20),
    },
    "Ethan": {
        "HR":   (110,   "bpm",  5,   60, 100),
        "Temp": (98.6,  "F",    0.1, 97.0, 99.5),
        "BP_S": (100,   "",     3,   90, 120),
        "BP_D": (65,    "",     2,   60, 80),
        "SpO2": (91,    "%",    2,   95, 100),
        "Resp": (28,    "/min", 3,   12, 20),
    },
    "Jackson": {
        "HR":   (82,    "bpm",  2,   60, 100),
        "Temp": (99.8,  "F",    0.2, 97.0, 99.5),
        "BP_S": (108,   "",     2,   90, 120),
        "BP_D": (70,    "",     2,   60, 80),
        "SpO2": (98,    "%",    1,   95, 100),
        "Resp": (17,    "/min", 1,   12, 20),
    },
    "Cynthia": {
        "HR":   (78,    "bpm",  2,   60, 100),
        "Temp": (98.6,  "F",    0.1, 97.0, 99.5),
        "BP_S": (106,   "",     2,   90, 120),
        "BP_D": (68,    "",     2,   60, 80),
        "SpO2": (99,    "%",    0,   95, 100),
        "Resp": (15,    "/min", 1,   12, 20),
    },
    "Olivia": {
        "HR":   (68,    "bpm",  3,   60, 100),
        "Temp": (98.4,  "F",    0.1, 97.0, 99.5),
        "BP_S": (126,   "",     3,   90, 120),
        "BP_D": (82,    "",     2,   60, 80),
        "SpO2": (99,    "%",    0,   95, 100),
        "Resp": (14,    "/min", 1,   12, 20),
    },
    "Leo": {
        "HR":   (64,    "bpm",  2,   60, 100),
        "Temp": (97.8,  "F",    0.2, 97.0, 99.5),
        "BP_S": (100,   "",     2,   90, 120),
        "BP_D": (62,    "",     2,   60, 80),
        "SpO2": (99,    "%",    0,   95, 100),
        "Resp": (14,    "/min", 1,   12, 20),
    },
    "Zoe": {
        "HR":   (80,    "bpm",  2,   60, 100),
        "Temp": (98.6,  "F",    0.1, 97.0, 99.5),
        "BP_S": (110,   "",     2,   90, 120),
        "BP_D": (70,    "",     2,   60, 80),
        "SpO2": (99,    "%",    0,   95, 100),
        "Resp": (16,    "/min", 1,   12, 20),
    },
    "Tyler": {
        "HR":   (96,    "bpm",  3,   60, 100),
        "Temp": (98.8,  "F",    0.2, 97.0, 99.5),
        "BP_S": (120,   "",     3,   90, 120),
        "BP_D": (78,    "",     2,   60, 80),
        "SpO2": (98,    "%",    1,   95, 100),
        "Resp": (16,    "/min", 1,   12, 20),
    },
    "Riley": {
        "HR":   (124,   "bpm",  6,   60, 100),
        "Temp": (99.2,  "F",    0.2, 97.0, 99.5),
        "BP_S": (132,   "",     4,   90, 120),
        "BP_D": (86,    "",     3,   60, 80),
        "SpO2": (99,    "%",    0,   95, 100),
        "Resp": (22,    "/min", 2,   12, 20),
    },
    "Mason": {
        "HR":   (106,   "bpm",  4,   60, 100),
        "Temp": (98.6,  "F",    0.1, 97.0, 99.5),
        "BP_S": (116,   "",     3,   90, 120),
        "BP_D": (74,    "",     2,   60, 80),
        "SpO2": (99,    "%",    0,   95, 100),
        "Resp": (20,    "/min", 2,   12, 20),
    },
}

# ECG beat pattern using Unicode lower-block characters
# P wave (▁▂▁) + flat + QRS complex (▃█▃) + flat + T wave (▁▂▁) + flat
# One complete PQRST cycle = 24 characters
BEAT_PATTERN = "\u2500\u2500\u2500\u2500\u2581\u2582\u2581\u2500\u2500\u2500\u2500\u2583\u2588\u2583\u2500\u2500\u2500\u2500\u2581\u2582\u2581\u2500\u2500\u2500"
BEAT_LEN = len(BEAT_PATTERN)  # 24


def fluctuate_vitals(patient_name):
    """Generate a snapshot of current vitals with realistic fluctuation.
    Returns dict of {key: (value, unit, is_abnormal)}.
    """
    base = PATIENT_VITALS.get(patient_name)
    if not base:
        return {}

    snapshot = {}
    for key, (base_val, unit, variance, low_thresh, high_thresh) in base.items():
        if key in ("BP_S", "BP_D"):
            continue
        if isinstance(base_val, float):
            current = round(base_val + random.uniform(-variance, variance), 1)
        else:
            current = base_val + random.randint(-variance, variance)
        is_abnormal = current < low_thresh or current > high_thresh
        snapshot[key] = (current, unit, is_abnormal)

    if "BP_S" in base and "BP_D" in base:
        bp_s_base, _, bp_s_var, bp_s_lo, bp_s_hi = base["BP_S"]
        bp_d_base, _, bp_d_var, bp_d_lo, bp_d_hi = base["BP_D"]
        bp_s = bp_s_base + random.randint(-bp_s_var, bp_s_var)
        bp_d = bp_d_base + random.randint(-bp_d_var, bp_d_var)
        is_abnormal = bp_s < bp_s_lo or bp_s > bp_s_hi or bp_d < bp_d_lo or bp_d > bp_d_hi
        snapshot["BP"] = (f"{bp_s}/{bp_d}", "", is_abnormal)

    return snapshot


def get_vitals(patient_name):
    """Return a simple {label: value_string} dict for the server .vitals command."""
    snapshot = fluctuate_vitals(patient_name)
    if not snapshot:
        return None
    result = {}
    for key, (val, unit, is_abnormal) in snapshot.items():
        tag = ""
        if is_abnormal:
            tag = " (abnormal)"
        result[key] = f"{val} {unit}{tag}".strip()
    return result
