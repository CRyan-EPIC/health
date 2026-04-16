import socket
import sys
import time
import getpass
import os
import re
import textwrap
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
DCYN = "\033[2;36m"

# ─── Session state ─────────────────────────────────────────────────

sample_covered = set()
start_time = None
conversation_log = []

# Thread-safe stdout writing (animator + streaming share stdout)
_write_lock = threading.Lock()


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
        try:
            self._render()
        except Exception:
            pass
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
        try:
            tw = os.get_terminal_size().columns
        except (ValueError, OSError):
            tw = 80

        # Fluctuate vitals on schedule
        if now - self._last_fluctuate >= self.FLUCTUATE_INTERVAL:
            self._vitals = fluctuate_vitals(self.patient_name)
            self._last_fluctuate = now

        vitals = self._vitals

        # Timer
        elapsed_str = ""
        if start_time:
            secs = int(now - start_time)
            mins, s = divmod(secs, 60)
            elapsed_str = f"{mins}:{s:02d}"

        # Box geometry: " │{content}│" → 1 margin + 1 border + content + 1 border
        inner_w = tw - 3

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

        BC = DCYN  # border color

        # ── Row 0: Top border with title ──
        title = " MedSim AI "
        top_fill = inner_w - len(title) - 2
        if top_fill < 0:
            top_fill = 0
        top = f" {BC}\u250c\u2500{BCYN}{title}{BC}{'\u2500' * top_fill}\u2500\u2510{RST}"

        # ── Row 1: Header (patient + timer) ──
        h_left_vis = f"  Patient: {self.patient_name}"
        h_left = f"  {DWHT}Patient:{RST} {BCYN}{self.patient_name}{RST}"
        if elapsed_str:
            h_right_vis = f"Time: {elapsed_str}  "
            h_right = f"{DWHT}Time:{RST} {BWHT}{elapsed_str}{RST}  "
        else:
            h_right_vis = "  "
            h_right = "  "
        h_pad = inner_w - len(h_left_vis) - len(h_right_vis)
        if h_pad < 0:
            h_pad = 0
        header = f" {BC}\u2502{RST}{h_left}{' ' * h_pad}{h_right}{BC}\u2502{RST}"

        # ── Row 2: ECG waveform + HR ──
        hr_vis = f"  \u2665 {hr_v} bpm  "
        hr_colored = f"  {BRED}\u2665{RST} {hrc}{hr_v}{RST} {DWHT}bpm{RST}  "
        ecg_width = inner_w - len(hr_vis) - 2  # 2 for left margin
        if ecg_width < 10:
            ecg_width = 10

        elapsed_t = now - self._birth
        beats_per_sec = hr_v / 60.0
        chars_per_sec = beats_per_sec * BEAT_LEN
        offset = int(elapsed_t * chars_per_sec)

        ecg_str = ""
        for i in range(ecg_width):
            ch = BEAT_PATTERN[(offset + i) % BEAT_LEN]
            if ch == "\u2500":
                ecg_str += f"{DGRN}{ch}"
            else:
                ecg_str += f"{BGRN}{ch}"
        ecg_str += RST

        ecg_vis_len = 2 + ecg_width + len(hr_vis)
        ecg_rpad = inner_w - ecg_vis_len
        if ecg_rpad < 0:
            ecg_rpad = 0
        ecg_line = f" {BC}\u2502{RST}  {ecg_str}{hr_colored}{' ' * ecg_rpad}{BC}\u2502{RST}"

        # ── Row 3: Vitals ──
        v_str = (
            f"  {DWHT}Temp{RST} {tc}{t_v}\u00b0{t_u}{RST}"
            f"    {DWHT}BP{RST} {bpc}{bp_v}{RST}"
            f"    {DWHT}SpO2{RST} {oc}{o_v}{o_u}{RST}"
            f"    {DWHT}Resp{RST} {rc}{r_v} {r_u}{RST}"
        )
        v_vis = f"  Temp {t_v}\u00b0{t_u}    BP {bp_v}    SpO2 {o_v}{o_u}    Resp {r_v} {r_u}"
        v_rpad = inner_w - len(v_vis)
        if v_rpad < 0:
            v_rpad = 0
        vitals_line = f" {BC}\u2502{RST}{v_str}{' ' * v_rpad}{BC}\u2502{RST}"

        # ── Row 4: Bottom border ──
        bottom = f" {BC}\u2514{'\u2500' * inner_w}\u2518{RST}"

        lines = [top, header, ecg_line, vitals_line, bottom]

        # ── Write to screen with cursor save/restore ──
        buf = "\033[s"
        for i, line in enumerate(lines):
            row = self.start_row + i
            buf += f"\033[{row};1H\033[2K{line}"
        buf += "\033[u"
        with _write_lock:
            sys.stdout.write(buf)
            sys.stdout.flush()


# ─── Screen layout ─────────────────────────────────────────────────
# Rows 1-5:  Patient monitor box (animated by VitalsAnimator)
#   Row 1: ┌─ MedSim AI ────────────────────────────────┐
#   Row 2: │  Patient: Name                  Time: 0:00 │
#   Row 3: │  ▁▂▁────▃█▃────▁▂▁────▃█▃───   ♥ 76 bpm   │
#   Row 4: │  Temp 98.5°F  BP 110/70  SpO2 99%  Resp 16 │
#   Row 5: └────────────────────────────────────────────┘
# Row 6+:  Conversation, help, input prompt

VITALS_START_ROW = 1
VITALS_HEIGHT = 5
STATIC_START_ROW = VITALS_START_ROW + VITALS_HEIGHT + 1


def draw_static_area(patient_name):
    """Draw everything below the vitals monitor (conversation, help, prompt)."""
    tw = os.get_terminal_size().columns
    th = os.get_terminal_size().lines
    row = STATIC_START_ROW

    # Conversation — word-wrap long messages across multiple rows
    max_rows = th - row - 3  # leave room for separator + help + prompt
    recent = conversation_log[-max_rows:]  # rough limit; may use fewer

    for msg_role, msg_text in recent:
        if row >= th - 3:
            break
        if msg_role == "doctor":
            prefix = f"  {BGRN}Doctor:{RST} "
            prefix_len = 10  # "  Doctor: "
        elif msg_role == "patient":
            prefix = f"  {BCYN}{patient_name}:{RST} "
            prefix_len = len(f"  {patient_name}: ")
        else:
            prefix = f"  {DIM}{YEL}"
            prefix_len = 2

        avail = max(20, tw - prefix_len - 1)
        wrapped = textwrap.wrap(msg_text, width=avail) or [""]

        # First line with role prefix
        first = f"{prefix}{wrapped[0]}"
        if msg_role == "system":
            first += RST
        sys.stdout.write(f"\033[{row};1H\033[2K{first}")
        row += 1

        # Continuation lines indented to align with first line's text
        indent = " " * prefix_len
        for cont in wrapped[1:]:
            if row >= th - 3:
                break
            sys.stdout.write(f"\033[{row};1H\033[2K{indent}{cont}")
            row += 1

    if not conversation_log:
        sys.stdout.write(f"\033[{row};1H\033[2K  {DIM}Start by asking the patient a question...{RST}")
        row += 1

    # Clear leftover lines from previous longer conversations
    while row < th - 3:
        sys.stdout.write(f"\033[{row};1H\033[2K")
        row += 1

    # Separator
    sys.stdout.write(f"\033[{row};1H\033[2K{DGRN}" + "\u2500" * tw + f"{RST}")
    row += 1

    # Help line
    sys.stdout.write(f"\033[{row};1H\033[2K  {BCYN}.reset{RST} {DWHT}Reset mood{RST}")
    row += 1

    # Prompt position
    sys.stdout.write(f"\033[{row};1H\033[2K")

    sys.stdout.flush()


def redraw_screen(patient_name):
    """Full screen redraw (clear + static area; monitor box drawn by animator)."""
    sys.stdout.write("\033[2J\033[H")  # clear screen, cursor home
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


def blocking_input(prompt):
    """Write prompt with ANSI positioning, then block until user presses Enter."""
    with _write_lock:
        sys.stdout.write(prompt)
        sys.stdout.flush()
    return sys.stdin.readline().rstrip('\n')


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
    global start_time

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

        sock, patient_name = connect_to_server(scenario)

        # Draw initial screen and start vitals animation
        redraw_screen(patient_name)
        animator = VitalsAnimator(patient_name, VITALS_START_ROW)
        animator.start()

        last_query = None
        last_prompt_time = 0
        PROMPT_COOLDOWN = 7
        should_restart = False

        # Spam detection
        rapid_count = 0
        last_enter_time = 0
        RAPID_WINDOW = 0.8     # seconds between presses to count as "rapid"
        SPAM_LIMIT = 3         # rapid presses before warning

        # Prompt positions at the last terminal row
        th = os.get_terminal_size().lines
        input_row = th
        prompt_str = f"\033[{input_row};1H\033[2K  {BGRN}Doctor > {RST}"

        while True:
            try:
                query = blocking_input(prompt_str)

                # Clear the input line immediately so typed text disappears
                with _write_lock:
                    sys.stdout.write(f"\033[{input_row};1H\033[2K")
                    sys.stdout.flush()

                query = query.strip()

                # Spam detection — warn on rapid repeated Enter presses
                now = time.time()
                if now - last_enter_time < RAPID_WINDOW:
                    rapid_count += 1
                else:
                    rapid_count = 0
                last_enter_time = now

                if rapid_count >= SPAM_LIMIT:
                    with _write_lock:
                        sys.stdout.write(
                            f"\033[{input_row - 1};1H\033[2K"
                            f"  {BRED}Slow down! Wait a moment before pressing Enter.{RST}"
                        )
                        sys.stdout.flush()
                    time.sleep(1.5)
                    rapid_count = 0
                    # Redraw to clear the warning
                    animator.stop()
                    redraw_screen(patient_name)
                    animator.start()
                    continue

                if len(query.encode('utf-8')) > MAX_PROMPT_LENGTH:
                    continue

                if query == '':
                    continue

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
                    animator.stop()
                    redraw_screen(patient_name)
                    animator.start()
                    continue

                # Rate limiting
                current_time = time.time()
                if current_time - last_prompt_time < PROMPT_COOLDOWN:
                    wait_time = PROMPT_COOLDOWN - (current_time - last_prompt_time)
                    with _write_lock:
                        sys.stdout.write(f"\033[{input_row - 1};1H\033[2K  {DIM}{YEL}Please wait {wait_time:.0f}s...{RST}")
                        sys.stdout.flush()
                    continue
                last_prompt_time = current_time

                # Regular question — animator keeps running (lock protects stdout)
                last_query = query
                conversation_log.append(("doctor", query))

                # Show streaming response below the monitor
                resp_row = STATIC_START_ROW
                with _write_lock:
                    sys.stdout.write(f"\033[{resp_row};1H\033[2K  {BCYN}{patient_name}:{RST} ")
                    sys.stdout.flush()

                while True:
                    try:
                        sock.sendall(query.encode('utf-8'))
                        response_text = ""
                        for tag_type, content in stream_response(sock):
                            if tag_type == "text":
                                with _write_lock:
                                    sys.stdout.write(content)
                                    sys.stdout.flush()
                                response_text += content

                        if response_text.strip():
                            conversation_log.append(("patient", response_text.strip()))

                        break
                    except (TimeoutError, ConnectionError) as e:
                        with _write_lock:
                            sys.stdout.write(f"\033[{resp_row + 1};1H\033[2K  {BRED}Reconnecting...{RST}")
                            sys.stdout.flush()
                        sock.close()
                        sock, patient_name = reconnect_and_resend(scenario, last_query)

                # After Q&A, redraw conversation area (animator keeps running)
                animator.stop()
                redraw_screen(patient_name)
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
