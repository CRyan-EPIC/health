import random
import time

# Base vital signs for all 21 patients
# Each value: (base_value, unit, variance, abnormal_threshold_low, abnormal_threshold_high)
# variance is the +/- range for fluctuation
PATIENT_VITALS = {
    "Julian": {
        "HR":   (98,   "bpm",   3,  60, 100),
        "Temp": (100.2, "F",    0.2, 97.0, 99.5),
        "BP_S": (105,  "",      3,   90, 120),
        "BP_D": (68,   "",      2,   60, 80),
        "SpO2": (98,   "%",     1,   95, 100),
        "Resp": (18,   "/min",  1,   12, 20),
    },
    "Emily": {
        "HR":   (102,  "bpm",   4,  60, 100),
        "Temp": (98.1, "F",     0.2, 97.0, 99.5),
        "BP_S": (90,   "",      3,   90, 120),
        "BP_D": (58,   "",      2,   60, 80),
        "SpO2": (98,   "%",     1,   95, 100),
        "Resp": (16,   "/min",  1,   12, 20),
    },
    "Sophia": {
        "HR":   (82,   "bpm",   2,  60, 100),
        "Temp": (98.4, "F",     0.2, 97.0, 99.5),
        "BP_S": (108,  "",      2,   90, 120),
        "BP_D": (70,   "",      2,   60, 80),
        "SpO2": (99,   "%",     0,   95, 100),
        "Resp": (16,   "/min",  1,   12, 20),
    },
    "Camila": {
        "HR":   (80,   "bpm",   2,  60, 100),
        "Temp": (99.0, "F",     0.2, 97.0, 99.5),
        "BP_S": (106,  "",      2,   90, 120),
        "BP_D": (68,   "",      2,   60, 80),
        "SpO2": (99,   "%",     0,   95, 100),
        "Resp": (16,   "/min",  1,   12, 20),
    },
    "Connor": {
        "HR":   (78,   "bpm",   2,  60, 100),
        "Temp": (98.6, "F",     0.1, 97.0, 99.5),
        "BP_S": (104,  "",      2,   90, 120),
        "BP_D": (66,   "",      2,   60, 80),
        "SpO2": (99,   "%",     0,   95, 100),
        "Resp": (15,   "/min",  1,   12, 20),
    },
    "Ben": {
        "HR":   (76,   "bpm",   2,  60, 100),
        "Temp": (98.5, "F",     0.1, 97.0, 99.5),
        "BP_S": (110,  "",      2,   90, 120),
        "BP_D": (70,   "",      2,   60, 80),
        "SpO2": (99,   "%",     0,   95, 100),
        "Resp": (16,   "/min",  1,   12, 20),
    },
    "Aidan": {
        "HR":   (100,  "bpm",   4,  60, 100),
        "Temp": (102.4, "F",    0.3, 97.0, 99.5),
        "BP_S": (100,  "",      3,   90, 120),
        "BP_D": (62,   "",      2,   60, 80),
        "SpO2": (97,   "%",     1,   95, 100),
        "Resp": (20,   "/min",  2,   12, 20),
    },
    "Emma": {
        "HR":   (108,  "bpm",   5,  60, 100),
        "Temp": (98.6, "F",     0.1, 97.0, 99.5),
        "BP_S": (118,  "",      3,   90, 120),
        "BP_D": (76,   "",      2,   60, 80),
        "SpO2": (99,   "%",     0,   95, 100),
        "Resp": (22,   "/min",  2,   12, 20),
    },
    "Lizzy": {
        "HR":   (90,   "bpm",   3,  60, 100),
        "Temp": (98.4, "F",     0.1, 97.0, 99.5),
        "BP_S": (110,  "",      2,   90, 120),
        "BP_D": (70,   "",      2,   60, 80),
        "SpO2": (99,   "%",     0,   95, 100),
        "Resp": (16,   "/min",  1,   12, 20),
    },
    "Michaela": {
        "HR":   (88,   "bpm",   3,  60, 100),
        "Temp": (101.8, "F",    0.3, 97.0, 99.5),
        "BP_S": (108,  "",      2,   90, 120),
        "BP_D": (68,   "",      2,   60, 80),
        "SpO2": (98,   "%",     1,   95, 100),
        "Resp": (17,   "/min",  1,   12, 20),
    },
    "Ian": {
        "HR":   (92,   "bpm",   3,  60, 100),
        "Temp": (98.6, "F",     0.1, 97.0, 99.5),
        "BP_S": (112,  "",      2,   90, 120),
        "BP_D": (72,   "",      2,   60, 80),
        "SpO2": (99,   "%",     0,   95, 100),
        "Resp": (16,   "/min",  1,   12, 20),
    },
    "Samira": {
        "HR":   (104,  "bpm",   4,  60, 100),
        "Temp": (98.8, "F",     0.2, 97.0, 99.5),
        "BP_S": (114,  "",      3,   90, 120),
        "BP_D": (74,   "",      2,   60, 80),
        "SpO2": (99,   "%",     0,   95, 100),
        "Resp": (18,   "/min",  1,   12, 20),
    },
    "Ethan": {
        "HR":   (110,  "bpm",   5,  60, 100),
        "Temp": (98.6, "F",     0.1, 97.0, 99.5),
        "BP_S": (100,  "",      3,   90, 120),
        "BP_D": (65,   "",      2,   60, 80),
        "SpO2": (91,   "%",     2,   95, 100),
        "Resp": (28,   "/min",  3,   12, 20),
    },
    "Jackson": {
        "HR":   (82,   "bpm",   2,  60, 100),
        "Temp": (99.8, "F",     0.2, 97.0, 99.5),
        "BP_S": (108,  "",      2,   90, 120),
        "BP_D": (70,   "",      2,   60, 80),
        "SpO2": (98,   "%",     1,   95, 100),
        "Resp": (17,   "/min",  1,   12, 20),
    },
    "Cynthia": {
        "HR":   (78,   "bpm",   2,  60, 100),
        "Temp": (98.6, "F",     0.1, 97.0, 99.5),
        "BP_S": (106,  "",      2,   90, 120),
        "BP_D": (68,   "",      2,   60, 80),
        "SpO2": (99,   "%",     0,   95, 100),
        "Resp": (15,   "/min",  1,   12, 20),
    },
    "Olivia": {
        "HR":   (68,   "bpm",   3,  60, 100),
        "Temp": (98.4, "F",     0.1, 97.0, 99.5),
        "BP_S": (126,  "",      3,   90, 120),
        "BP_D": (82,   "",      2,   60, 80),
        "SpO2": (99,   "%",     0,   95, 100),
        "Resp": (14,   "/min",  1,   12, 20),
    },
    "Leo": {
        "HR":   (64,   "bpm",   2,  60, 100),
        "Temp": (97.8, "F",     0.2, 97.0, 99.5),
        "BP_S": (100,  "",      2,   90, 120),
        "BP_D": (62,   "",      2,   60, 80),
        "SpO2": (99,   "%",     0,   95, 100),
        "Resp": (14,   "/min",  1,   12, 20),
    },
    "Zoe": {
        "HR":   (80,   "bpm",   2,  60, 100),
        "Temp": (98.6, "F",     0.1, 97.0, 99.5),
        "BP_S": (110,  "",      2,   90, 120),
        "BP_D": (70,   "",      2,   60, 80),
        "SpO2": (99,   "%",     0,   95, 100),
        "Resp": (16,   "/min",  1,   12, 20),
    },
    "Tyler": {
        "HR":   (96,   "bpm",   3,  60, 100),
        "Temp": (98.8, "F",     0.2, 97.0, 99.5),
        "BP_S": (120,  "",      3,   90, 120),
        "BP_D": (78,   "",      2,   60, 80),
        "SpO2": (98,   "%",     1,   95, 100),
        "Resp": (16,   "/min",  1,   12, 20),
    },
    "Riley": {
        "HR":   (124,  "bpm",   6,  60, 100),
        "Temp": (99.2, "F",     0.2, 97.0, 99.5),
        "BP_S": (132,  "",      4,   90, 120),
        "BP_D": (86,   "",      3,   60, 80),
        "SpO2": (99,   "%",     0,   95, 100),
        "Resp": (22,   "/min",  2,   12, 20),
    },
    "Mason": {
        "HR":   (106,  "bpm",   4,  60, 100),
        "Temp": (98.6, "F",     0.1, 97.0, 99.5),
        "BP_S": (116,  "",      3,   90, 120),
        "BP_D": (74,   "",      2,   60, 80),
        "SpO2": (99,   "%",     0,   95, 100),
        "Resp": (20,   "/min",  2,   12, 20),
    },
}

# ECG-style waveform pattern (one heartbeat cycle)
# Heights: 0=baseline, positive=up, negative=down
ECG_PATTERN = [0, 0, 0, 1, 0, 0, -1, 4, -2, 0, 0, 1, 1, 0, 0, 0]

# Characters for drawing the waveform
WAVE_CHARS = {
    -2: " ",
    -1: " ",
     0: "─",
     1: "╱",
     2: "│",
     3: "╲",
     4: "▲",
}


def get_vitals(patient_name):
    """Return the base vitals definition for a patient."""
    return PATIENT_VITALS.get(patient_name)


def fluctuate_vitals(patient_name):
    """Generate a snapshot of current vitals with realistic fluctuation."""
    base = PATIENT_VITALS.get(patient_name)
    if not base:
        return {}

    snapshot = {}
    for key, (base_val, unit, variance, low_thresh, high_thresh) in base.items():
        if key in ("BP_S", "BP_D"):
            continue  # handled together below
        if isinstance(base_val, float):
            current = round(base_val + random.uniform(-variance, variance), 1)
        else:
            current = base_val + random.randint(-variance, variance)
        is_abnormal = current < low_thresh or current > high_thresh
        snapshot[key] = (current, unit, is_abnormal)

    # Combine BP
    if "BP_S" in base and "BP_D" in base:
        bp_s_base, _, bp_s_var, bp_s_lo, bp_s_hi = base["BP_S"]
        bp_d_base, _, bp_d_var, bp_d_lo, bp_d_hi = base["BP_D"]
        bp_s = bp_s_base + random.randint(-bp_s_var, bp_s_var)
        bp_d = bp_d_base + random.randint(-bp_d_var, bp_d_var)
        is_abnormal = bp_s < bp_s_lo or bp_s > bp_s_hi or bp_d < bp_d_lo or bp_d > bp_d_hi
        snapshot["BP"] = (f"{bp_s}/{bp_d}", "mmHg", is_abnormal)

    return snapshot


def generate_ecg_line(offset, width=30):
    """Generate a single line of ASCII ECG waveform.
    offset: shifts the pattern to animate it over time.
    Returns a string of `width` characters.
    """
    pattern_len = len(ECG_PATTERN)
    line_top = []
    line_mid = []
    line_bot = []

    for i in range(width):
        idx = (i + offset) % pattern_len
        val = ECG_PATTERN[idx]
        if val >= 3:
            line_top.append("╷")
            line_mid.append("│")
            line_bot.append("╵")
        elif val == 2:
            line_top.append("╷")
            line_mid.append("│")
            line_bot.append(" ")
        elif val == 1:
            line_top.append("╷")
            line_mid.append(" ")
            line_bot.append(" ")
        elif val == 0:
            line_top.append(" ")
            line_mid.append("─")
            line_bot.append(" ")
        elif val == -1:
            line_top.append(" ")
            line_mid.append(" ")
            line_bot.append("╵")
        elif val <= -2:
            line_top.append(" ")
            line_mid.append("╵")
            line_bot.append("╵")

    return "".join(line_top), "".join(line_mid), "".join(line_bot)


def format_vitals_ascii(patient_name, ecg_offset=0):
    """Build a complete ASCII vital signs monitor string.
    Returns a list of lines for the monitor display.
    """
    snapshot = fluctuate_vitals(patient_name)
    if not snapshot:
        return ["No vitals available"]

    ecg_top, ecg_mid, ecg_bot = generate_ecg_line(ecg_offset, width=28)

    hr_val, hr_unit, hr_abnormal = snapshot.get("HR", (0, "bpm", False))
    temp_val, temp_unit, temp_abnormal = snapshot.get("Temp", (0, "F", False))
    bp_val, bp_unit, bp_abnormal = snapshot.get("BP", ("--/--", "mmHg", False))
    spo2_val, spo2_unit, spo2_abnormal = snapshot.get("SpO2", (0, "%", False))
    resp_val, resp_unit, resp_abnormal = snapshot.get("Resp", (0, "/min", False))

    return {
        "ecg_top": ecg_top,
        "ecg_mid": ecg_mid,
        "ecg_bot": ecg_bot,
        "hr": (hr_val, hr_unit, hr_abnormal),
        "temp": (temp_val, temp_unit, temp_abnormal),
        "bp": (bp_val, bp_unit, bp_abnormal),
        "spo2": (spo2_val, spo2_unit, spo2_abnormal),
        "resp": (resp_val, resp_unit, resp_abnormal),
    }
