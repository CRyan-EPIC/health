import socket
import sys
import time
import getpass
import os
import json
import re
import select
import threading

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from vitals import fluctuate_vitals, PATIENT_VITALS, BEAT_PATTERN, BEAT_LEN

SERVER_IP = '10.171.132.99'
#SERVER_IP = '10.171.159.254'
SERVER_PORT = 65432
SOCKET_TIMEOUT = 30
RECONNECT_DELAY = 3
IDLE_TIMEOUT = 60
MAX_PROMPT_LENGTH = 256

console = Console()

patients = [
    [1, "Julian"],   [2, "Emily"],    [3, "Sophia"],
    [4, "Camila"],   [5, "Connor"],   [6, "Ben"],
    [7, "Aidan"],    [8, "Emma"],     [9, "Lizzy"],
    [10, "Michaela"],[11, "Ian"],     [12, "Samira"],
    [13, "Ethan"],   [14, "Jackson"], [15, "Cynthia"],
    [16, "Olivia"],  [17, "Leo"],     [18, "Zoe"],
    [19, "Tyler"],   [20, "Riley"],   [21, "Mason"],
]

SAMPLE_LABELS = {
    "S": "Signs & Symptoms",
    "A": "Allergies",
    "M": "Medications",
    "P": "Past History",
    "L": "Last Intake",
    "E": "Events Leading Up",
}

# ─── ANSI codes ────────────────────────────────────────────────────

RST  = "\033[0m"
BOLD = "\033[1m"
DIM  = "\033[2m"
RED  = "\033[31m"
GRN  = "\033[32m"
YEL  = "\033[33m"
CYN  = "\033[36m"
WHT  = "\033[37m"
BRED = "\033[1;31m"
BGRN = "\033[1;32m"
BCYN = "\033[1;36m"
BWHT = "\033[1;37m"
DGRN = "\033[2;32m"
DWHT = "\033[2;37m"

# ─── Session state ─────────────────────────────────────────────────

sample_covered = set()
start_time = None
conversation_log = []
last_activity = time.time()


# ─── Vitals Animator ───────────────────────────────────────────────

class VitalsAnimator:
    """Live-updating vitals monitor rendered at fixed screen rows via ANSI."""

    REFRESH_INTERVAL = 0.25       # 250ms between display refreshes
    FLUCTUATE_INTERVAL = 8.0      # seconds between vital number changes

    def __init__(self, patient_name, start_row):
        self.patient_name = patient_name
        self.start_row = start_row
        self.running = False
        self._thread = None
        self._birth = time.time()
        self._vitals = fluctuate_vitals(patient_name)
        self._last_fluctuate = time.time()

    def start(self):
        self.running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self.running = False

    def _loop(self):
        while self.running:
            try:
                self._render()
            except Exception:
                pass
            time.sleep(self.REFRESH_INTERVAL)

    def _render(self):
        now = time.time()
        tw = os.get_terminal_size().columns

        # Fluctuate vitals on schedule
        if now - self._last_fluctuate >= self.FLUCTUATE_INTERVAL:
            self._vitals = fluctuate_vitals(self.patient_name)
            self._last_fluctuate = now

        vitals = self._vitals
        hr_val = vitals.get("HR", (72, "bpm", False))[0]

        # ── ECG waveform ──────────────────────────────
        elapsed = now - self._birth
        beats_per_sec = hr_val / 60.0
        chars_per_sec = beats_per_sec * BEAT_LEN
        offset = int(elapsed * chars_per_sec)

        ecg_width = tw - 20  # leave room for HR number on the right
        ecg_colored = ""
        for i in range(ecg_width):
            ch = BEAT_PATTERN[(offset + i) % BEAT_LEN]
            if ch == "\u2500":
                ecg_colored += f"{DGRN}{ch}"
            else:
                ecg_colored += f"{BGRN}{ch}"
        ecg_colored += RST

        # ── Extract vitals ────────────────────────────
        hr_v, hr_u, hr_ab = vitals.get("HR", (72, "bpm", False))
        t_v, t_u, t_ab = vitals.get("Temp", (98.6, "F", False))
        bp_v, _, bp_ab = vitals.get("BP", ("--/--", "", False))
        o_v, o_u, o_ab = vitals.get("SpO2", (99, "%", False))
        r_v, r_u, r_ab = vitals.get("Resp", (16, "/min", False))

        hrc = BRED if hr_ab else BGRN
        tc  = BRED if t_ab else WHT
        bpc = BRED if bp_ab else WHT
        oc  = BRED if o_ab else BCYN
        rc  = BRED if r_ab else WHT

        # ── Compose 7-line display ────────────────────
        # Line 0: blank spacer
        # Line 1: ECG waveform + large HR number
        # Line 2: blank
        # Line 3: Temp   BP   SpO2   Resp  (labels)
        # Line 4: values
        # Line 5: blank spacer
        # Line 6: thin separator

        hr_display = f"  {BRED}\u2665{RST} {hrc}{hr_v}{RST} {DWHT}bpm{RST}"

        sep = f"{DGRN}" + "\u2500" * tw + f"{RST}"

        lines = [
            "",
            f"  {ecg_colored}{hr_display}",
            "",
            f"    {DWHT}Temp{RST}          {DWHT}BP{RST}            {DWHT}SpO2{RST}          {DWHT}Resp{RST}",
            f"    {tc}{t_v} {t_u}{RST}        {bpc}{bp_v}{RST}          {oc}{o_v}{o_u}{RST}           {rc}{r_v} {r_u}{RST}",
            "",
            sep,
        ]

        # ── Write to screen with cursor save/restore ──
        buf = "\033[s"
        for i, line in enumerate(lines):
            row = self.start_row + i
            buf += f"\033[{row};1H\033[2K{line}"
        buf += "\033[u"
        sys.stdout.write(buf)
        sys.stdout.flush()


# ─── Screen layout ─────────────────────────────────────────────────
# Row 1:     Header line
# Row 2:     Separator
# Row 3:     (blank)
# Row 4-10:  Vitals monitor (7 lines, animated by VitalsAnimator)
# Row 11:    SAMPLE compact line
# Row 12:    (blank)
# Rows 13+:  Conversation, help, input prompt

VITALS_START_ROW = 4
VITALS_HEIGHT = 7
STATIC_START_ROW = VITALS_START_ROW + VITALS_HEIGHT


def draw_header(patient_name):
    """Draw the 2-line header at rows 1-2."""
    tw = os.get_terminal_size().columns
    elapsed = ""
    if start_time:
        secs = int(time.time() - start_time)
        mins, s = divmod(secs, 60)
        elapsed = f"{mins}:{s:02d}"

    left = f"  {BRED}+{RST}  {BCYN}MedSim AI{RST}  {BRED}+{RST}  {DWHT}Patient:{RST} {BCYN}{patient_name}{RST}"
    right = f"{DWHT}Time:{RST} {BWHT}{elapsed}{RST}"

    sys.stdout.write(f"\033[1;1H\033[2K{left}    {right}\n")
    sys.stdout.write(f"\033[2K{DGRN}" + "\u2500" * tw + f"{RST}\n")
    sys.stdout.flush()


def draw_sample_line():
    """Draw a compact 1-line SAMPLE checklist."""
    parts = []
    for letter in SAMPLE_LABELS:
        if letter in sample_covered:
            parts.append(f"{BGRN}[\u2713]{letter}{RST}")
        else:
            parts.append(f"{DIM}[ ]{letter}{RST}")
    count = len(sample_covered)
    total = len(SAMPLE_LABELS)
    line = f"  {BWHT}SAMPLE:{RST} {'  '.join(parts)}   {DWHT}({count}/{total}){RST}"
    return line


def draw_static_area(patient_name):
    """Draw everything below the vitals monitor (SAMPLE, conversation, help, prompt)."""
    tw = os.get_terminal_size().columns
    th = os.get_terminal_size().lines
    row = STATIC_START_ROW

    # Row 8: blank
    sys.stdout.write(f"\033[{row};1H\033[2K")
    row += 1

    # Row 9: SAMPLE
    sys.stdout.write(f"\033[{row};1H\033[2K{draw_sample_line()}")
    row += 1

    # Row 10: separator
    sys.stdout.write(f"\033[{row};1H\033[2K{DGRN}" + "\u2500" * tw + f"{RST}")
    row += 1

    # Rows 11+: Conversation
    max_conv_lines = max(4, th - row - 4)  # leave room for help + input
    recent = conversation_log[-(max_conv_lines):]

    for msg_role, msg_text in recent:
        if row >= th - 3:
            break
        if msg_role == "doctor":
            line = f"  {BGRN}Doctor:{RST} {msg_text}"
        elif msg_role == "patient":
            line = f"  {BCYN}{patient_name}:{RST} {msg_text}"
        else:
            line = f"  {DIM}{YEL}{msg_text}{RST}"
        # Truncate to terminal width
        # Strip ANSI for length check
        visible = re.sub(r'\033\[[0-9;]*m', '', line)
        if len(visible) > tw - 1:
            # Rough truncation (may cut mid-ANSI, but safer than overflow)
            line = line[:tw + 60] + RST
        sys.stdout.write(f"\033[{row};1H\033[2K{line}")
        row += 1

    if not recent:
        sys.stdout.write(f"\033[{row};1H\033[2K  {DIM}Start by asking the patient a question...{RST}")
        row += 1

    # Clear any leftover lines from previous longer conversations
    while row < th - 3:
        sys.stdout.write(f"\033[{row};1H\033[2K")
        row += 1

    # Separator
    sys.stdout.write(f"\033[{row};1H\033[2K{DGRN}" + "\u2500" * tw + f"{RST}")
    row += 1

    # Help line
    sys.stdout.write(f"\033[{row};1H\033[2K  {BCYN}.reset{RST} {DWHT}Reset mood{RST}")
    row += 1

    # Blank + prompt position
    sys.stdout.write(f"\033[{row};1H\033[2K")

    sys.stdout.flush()


def redraw_screen(patient_name):
    """Full screen redraw (header + vitals placeholder + static area)."""
    sys.stdout.write("\033[2J\033[H")  # clear screen, cursor home
    draw_header(patient_name)
    # Row 3: blank
    sys.stdout.write("\033[3;1H\033[2K\n")
    # Rows 4-10: leave blank for VitalsAnimator
    for r in range(VITALS_START_ROW, VITALS_START_ROW + VITALS_HEIGHT):
        sys.stdout.write(f"\033[{r};1H\033[2K\n")
    draw_static_area(patient_name)
    sys.stdout.flush()


# ─── Networking ────────────────────────────────────────────────────

def stream_response(sock):
    buffer = bytearray()
    while True:
        try:
            chunk = sock.recv(64)
            if not chunk:
                raise ConnectionError("Server closed connection.")
            buffer.extend(chunk)
            while True:
                try:
                    decoded = buffer.decode('utf-8')
                    if "<<END_OF_RESPONSE>>" in decoded:
                        idx = decoded.index("<<END_OF_RESPONSE>>")
                        to_yield = decoded[:idx]
                        remainder = decoded[idx + len("<<END_OF_RESPONSE>>"):]
                        if to_yield:
                            yield ("text", to_yield)
                        parse_special_tags(remainder)
                        return
                    tag_start = decoded.find("<<")
                    if tag_start > 0:
                        yield ("text", decoded[:tag_start])
                        buffer = bytearray(decoded[tag_start:].encode('utf-8'))
                    elif tag_start == 0 and ">>" in decoded:
                        tag_end = decoded.index(">>") + 2
                        parse_special_tags(decoded[:tag_end])
                        buffer = bytearray(decoded[tag_end:].encode('utf-8'))
                    elif tag_start == -1 and decoded:
                        yield ("text", decoded)
                        buffer.clear()
                    break
                except UnicodeDecodeError as e:
                    valid_up_to = e.start
                    if valid_up_to > 0:
                        part = buffer[:valid_up_to].decode('utf-8', errors='replace')
                        yield ("text", part)
                        buffer = buffer[valid_up_to:]
                    break
        except (socket.timeout, ConnectionResetError):
            raise TimeoutError("Timed out waiting for server response.")
        except Exception as e:
            raise ConnectionError(f"Server closed connection: {str(e)}")


def parse_special_tags(text):
    global sample_covered
    m = re.search(r'<<SAMPLE:([A-Z]+)>>', text)
    if m:
        for letter in m.group(1):
            if letter in SAMPLE_LABELS:
                sample_covered.add(letter)


def connect_to_server(scenario):
    while True:
        try:
            sys.stdout.write(f"  {DIM}Connecting to server...{RST}\n")
            sys.stdout.flush()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(SOCKET_TIMEOUT)
            sock.connect((SERVER_IP, SERVER_PORT))
            sock.sendall(str(scenario).encode('utf-8'))
            patient_name = sock.recv(1024).decode('utf-8', errors='replace').strip()
            return sock, patient_name
        except Exception as e:
            sys.stdout.write(f"  {BRED}Connection failed ({e}), retrying in {RECONNECT_DELAY}s...{RST}\n")
            sys.stdout.flush()
            time.sleep(RECONNECT_DELAY)


def reconnect_and_resend(scenario, last_query):
    while True:
        sock, patient_name = connect_to_server(scenario)
        try:
            sock.sendall(last_query.encode('utf-8'))
            return sock, patient_name
        except Exception as e:
            sys.stdout.write(f"  {BRED}Resend failed: {e}. Retrying...{RST}\n")
            sys.stdout.flush()
            sock.close()
            time.sleep(RECONNECT_DELAY)


def timed_input(prompt, timeout):
    sys.stdout.write(prompt)
    sys.stdout.flush()
    ready, _, _ = select.select([sys.stdin], [], [], timeout)
    if ready:
        return sys.stdin.readline().rstrip('\n')
    return None


# ─── Scenario selection (Rich for the one-time screen) ─────────────

def choose_scenario():
    os.system('cls' if os.name == 'nt' else 'clear')
    banner = Text()
    banner.append("  +  ", style="bold red")
    banner.append("MedSim AI", style="bold cyan")
    banner.append("  +  ", style="bold red")
    banner.append("  CNA Training Simulator", style="dim white")
    console.print(Panel(banner, border_style="cyan", box=box.DOUBLE))
    console.print()
    console.print("[bold white]  Select a Patient[/]")
    console.print()

    table = Table(box=box.SIMPLE, show_header=True, header_style="bold cyan", padding=(0, 2))
    table.add_column("#", justify="right", style="bold cyan", width=3)
    table.add_column("Patient", min_width=12, style="white")
    table.add_column("#", justify="right", style="bold cyan", width=3)
    table.add_column("Patient", min_width=12, style="white")
    table.add_column("#", justify="right", style="bold cyan", width=3)
    table.add_column("Patient", min_width=12, style="white")

    for i in range(0, len(patients), 3):
        row = []
        for j in range(3):
            if i + j < len(patients):
                p = patients[i + j]
                row.extend([str(p[0]), p[1]])
            else:
                row.extend(["", ""])
        table.add_row(*row)

    console.print(table)
    console.print()

    while True:
        try:
            choice = console.input("[bold cyan]Choose patient (1-21): [/]")
            scenario = int(choice.strip())
            if 1 <= scenario <= 21:
                return scenario
            console.print("[red]Invalid choice. Pick 1-21.[/]")
        except ValueError:
            console.print("[red]Numbers only please.[/]")


# ─── Session management ───────────────────────────────────────────

def reset_session():
    global sample_covered, start_time, conversation_log
    sample_covered = set()
    start_time = time.time()
    conversation_log = []


# ─── Main ─────────────────────────────────────────────────────────

def main():
    global last_activity, start_time

    os.system('cls' if os.name == 'nt' else 'clear')
    banner = Text()
    banner.append("  +  ", style="bold red")
    banner.append("MedSim AI", style="bold cyan")
    banner.append("  +  ", style="bold red")
    console.print(Panel(banner, border_style="cyan", box=box.DOUBLE))
    console.print()
    password = getpass.getpass("Enter password: ")
    if password != "":
        console.print("[bold red]Incorrect password.[/]")
        sys.exit(1)

    while True:
        scenario = choose_scenario()
        reset_session()
        last_activity = time.time()

        sock, patient_name = connect_to_server(scenario)

        # Draw initial screen and start vitals animation
        redraw_screen(patient_name)
        animator = VitalsAnimator(patient_name, VITALS_START_ROW)
        animator.start()

        last_query = None
        empty_input_count = 0
        EMPTY_INPUT_THRESHOLD = 3
        last_prompt_time = 0
        PROMPT_COOLDOWN = 7
        should_restart = False

        # Move cursor to input row
        th = os.get_terminal_size().lines
        input_row = th
        prompt_str = f"\033[{input_row};1H\033[2K\n  {BGRN}Doctor > {RST}"

        while True:
            try:
                elapsed_idle = time.time() - last_activity
                remaining = max(1, IDLE_TIMEOUT - elapsed_idle)

                query = timed_input(prompt_str, timeout=remaining)

                if query is None:
                    animator.stop()
                    sys.stdout.write(f"\n  {DIM}{YEL}Session timed out. Returning to patient selection...{RST}\n")
                    sys.stdout.flush()
                    time.sleep(2)
                    should_restart = True
                    break

                query = query.strip()
                last_activity = time.time()

                if len(query.encode('utf-8')) > MAX_PROMPT_LENGTH:
                    sys.stdout.write(f"  {BRED}Prompt too long! Max {MAX_PROMPT_LENGTH} bytes.{RST}\n")
                    sys.stdout.flush()
                    continue

                if query == '':
                    empty_input_count += 1
                    if empty_input_count >= EMPTY_INPUT_THRESHOLD:
                        sys.stdout.write(f"  {DIM}{YEL}Please type a question for the patient.{RST}\n")
                        sys.stdout.flush()
                    continue
                else:
                    empty_input_count = 0

                if query.lower() == 'exit':
                    animator.stop()
                    sock.close()
                    sys.stdout.write(f"  {DIM}Goodbye!{RST}\n")
                    sys.stdout.flush()
                    return

                if query.lower() == '.switch':
                    animator.stop()
                    sock.close()
                    should_restart = True
                    break

                if query.lower() == '.reset':
                    sock.sendall(query.encode('utf-8'))
                    response_text = ""
                    for tag_type, content in stream_response(sock):
                        if tag_type == "text":
                            response_text += content
                    conversation_log.append(("system", response_text.strip()))
                    # Pause animator, redraw, resume
                    animator.stop()
                    redraw_screen(patient_name)
                    animator = VitalsAnimator(patient_name, VITALS_START_ROW)
                    animator.start()
                    continue

                # Rate limiting
                current_time = time.time()
                if current_time - last_prompt_time < PROMPT_COOLDOWN:
                    wait_time = PROMPT_COOLDOWN - (current_time - last_prompt_time)
                    sys.stdout.write(f"  {DIM}{YEL}Please wait {wait_time:.1f}s before your next question.{RST}\n")
                    sys.stdout.flush()
                    continue
                last_prompt_time = current_time

                # Regular question
                last_query = query
                conversation_log.append(("doctor", query))

                while True:
                    try:
                        sock.sendall(query.encode('utf-8'))
                        response_text = ""
                        sys.stdout.write(f"\n  {BCYN}{patient_name}:{RST} ")
                        sys.stdout.flush()
                        for tag_type, content in stream_response(sock):
                            if tag_type == "text":
                                sys.stdout.write(content)
                                sys.stdout.flush()
                                response_text += content
                        sys.stdout.write("\n")
                        sys.stdout.flush()

                        if response_text.strip():
                            conversation_log.append(("patient", response_text.strip()))

                        if sample_covered:
                            covered = ", ".join(SAMPLE_LABELS[l] for l in sorted(sample_covered))
                            sys.stdout.write(f"  {DGRN}SAMPLE: {len(sample_covered)}/6 ({covered}){RST}\n")
                            sys.stdout.flush()

                        break
                    except (TimeoutError, ConnectionError) as e:
                        sys.stdout.write(f"\n  {BRED}Lost connection: {e}. Reconnecting...{RST}\n")
                        sys.stdout.flush()
                        sock.close()
                        sock, patient_name = reconnect_and_resend(scenario, last_query)

                # After Q&A, redraw the static area to update conversation + SAMPLE
                last_activity = time.time()
                animator.stop()
                redraw_screen(patient_name)
                animator = VitalsAnimator(patient_name, VITALS_START_ROW)
                animator.start()

            except KeyboardInterrupt:
                animator.stop()
                sock.close()
                sys.stdout.write(f"\n  {DIM}Exiting.{RST}\n")
                sys.stdout.flush()
                return

        try:
            sock.close()
        except Exception:
            pass

        if not should_restart:
            break


if __name__ == '__main__':
    main()
