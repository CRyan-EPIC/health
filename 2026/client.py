import socket
import sys
import time
import getpass
import os
import json
import re
import select

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.columns import Columns
from rich import box

from vitals import format_vitals_ascii, get_vitals

SERVER_IP = '10.171.132.99'
#SERVER_IP = '10.171.159.254'
SERVER_PORT = 65432
SOCKET_TIMEOUT = 30
RECONNECT_DELAY = 3
IDLE_TIMEOUT = 60  # seconds of no input before auto-restart
MAX_PROMPT_LENGTH = 256  # bytes

console = Console()

patients = [
    [1, "Julian"],
    [2, "Emily"],
    [3, "Sophia"],
    [4, "Camila"],
    [5, "Connor"],
    [6, "Ben"],
    [7, "Aidan"],
    [8, "Emma"],
    [9, "Lizzy"],
    [10, "Michaela"],
    [11, "Ian"],
    [12, "Samira"],
    [13, "Ethan"],
    [14, "Jackson"],
    [15, "Cynthia"],
    [16, "Olivia"],
    [17, "Leo"],
    [18, "Zoe"],
    [19, "Tyler"],
    [20, "Riley"],
    [21, "Mason"],
]

# SAMPLE assessment state
SAMPLE_LABELS = {
    "S": "Signs & Symptoms",
    "A": "Allergies",
    "M": "Medications",
    "P": "Past History",
    "L": "Last Intake",
    "E": "Events Leading Up",
}

# Session state
sample_covered = set()
start_time = None
conversation_log = []  # list of (role, text) tuples
ecg_offset = 0  # animation offset for ECG waveform

last_activity = time.time()


# ─── Display helpers ───────────────────────────────────────────────

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def print_banner():
    """Print the MedSim AI welcome banner."""
    banner = Text()
    banner.append("  +  ", style="bold red")
    banner.append("MedSim AI", style="bold cyan")
    banner.append("  +  ", style="bold red")
    banner.append("  CNA Training Simulator", style="dim white")
    console.print(Panel(banner, border_style="cyan", box=box.DOUBLE))


def print_header(patient_name):
    """Print the patient header with timer."""
    elapsed = ""
    if start_time:
        secs = int(time.time() - start_time)
        mins, s = divmod(secs, 60)
        elapsed = f"{mins}:{s:02d}"

    header = Table.grid(padding=(0, 3))
    header.add_column(justify="left", min_width=30)
    header.add_column(justify="right", min_width=20)
    header.add_row(
        Text.assemble(
            ("  +  ", "bold red"),
            ("Patient: ", "dim white"),
            (patient_name, "bold cyan"),
        ),
        Text.assemble(
            ("Time: ", "dim white"),
            (elapsed, "bold white"),
        ),
    )
    console.print(Panel(header, border_style="cyan", title="[bold cyan]MedSim AI[/]", title_align="left", box=box.ROUNDED))


def print_sample_checklist():
    """Print the SAMPLE assessment checklist."""
    table = Table(
        title="[bold white]SAMPLE Assessment[/]",
        box=box.SIMPLE,
        show_header=False,
        title_style="bold white",
        padding=(0, 1),
    )
    table.add_column("Check", width=3)
    table.add_column("Category", min_width=20)

    for letter, label in SAMPLE_LABELS.items():
        if letter in sample_covered:
            check = "[bold green][x][/]"
            style = "green"
        else:
            check = "[dim][ ][/]"
            style = "dim white"
        table.add_row(check, f"[{style}]{letter} - {label}[/]")

    return table


def build_vitals_monitor(patient_name):
    """Build the ASCII vital signs monitor panel with ECG waveform."""
    global ecg_offset
    ecg_offset += 1

    data = format_vitals_ascii(patient_name, ecg_offset)
    if isinstance(data, list):
        return Panel("[dim]No vitals[/]", title="[bold white]Vitals Monitor[/]", border_style="green")

    text = Text()

    # ECG waveform line
    text.append("  ", style="green")
    text.append(data["ecg_top"], style="bold green")
    text.append("\n")
    text.append("  ", style="green")
    text.append(data["ecg_mid"], style="bold green")
    text.append("\n")
    text.append("  ", style="green")
    text.append(data["ecg_bot"], style="bold green")
    text.append("\n\n")

    # Vital sign readings
    vitals_order = [
        ("HR",   "hr",   "bold green"),
        ("Temp", "temp", "bold white"),
        ("BP",   "bp",   "bold white"),
        ("SpO2", "spo2", "bold cyan"),
        ("Resp", "resp", "bold white"),
    ]

    for label, key, normal_style in vitals_order:
        val, unit, is_abnormal = data[key]
        style = "bold red" if is_abnormal else normal_style
        if label == "HR":
            text.append("  ♥ ", style="bold red")
        else:
            text.append("    ", style="dim")
        text.append(f"{label}: ", style="dim white")
        text.append(f"{val} {unit}", style=style)
        if is_abnormal:
            text.append(" !", style="bold red")
        text.append("\n")

    return text


def print_sidebar(patient_name):
    """Print SAMPLE checklist and vitals monitor side by side."""
    sample_table = print_sample_checklist()
    vitals_text = build_vitals_monitor(patient_name)
    vitals_panel = Panel(
        vitals_text,
        title="[bold green]Vitals Monitor[/]",
        border_style="green",
        box=box.ROUNDED,
        width=38,
    )
    console.print(Columns([sample_table, vitals_panel], padding=(0, 2)))


def print_help_bar():
    """Print the command help bar at the bottom."""
    help_text = Text()
    commands = [
        (".reset", "Reset mood"),
    ]
    for i, (cmd, desc) in enumerate(commands):
        if i > 0:
            help_text.append("  |  ", style="dim")
        help_text.append(cmd, style="bold cyan")
        help_text.append(f" {desc}", style="dim white")
    console.print(Panel(help_text, border_style="dim", box=box.ROUNDED))


def print_conversation_tail(patient_name, n=6):
    """Print the last n conversation exchanges."""
    recent = conversation_log[-n:]
    if not recent:
        console.print(Panel(
            "[dim italic]Start by asking the patient a question...[/]",
            title="[bold white]Conversation[/]",
            border_style="dim cyan",
            box=box.ROUNDED,
        ))
        return

    text = Text()
    for role, msg in recent:
        if role == "doctor":
            text.append("Doctor: ", style="bold green")
            text.append(msg + "\n", style="white")
        elif role == "patient":
            text.append(f"{patient_name}: ", style="bold cyan")
            text.append(msg + "\n", style="white")
        elif role == "system":
            text.append(msg + "\n", style="dim yellow")
    console.print(Panel(
        text,
        title="[bold white]Conversation[/]",
        border_style="dim cyan",
        box=box.ROUNDED,
    ))


def redraw_screen(patient_name):
    """Redraw the full TUI screen."""
    clear_screen()
    print_header(patient_name)
    console.print()
    print_sidebar(patient_name)
    console.print()
    print_conversation_tail(patient_name)
    console.print()
    print_help_bar()


# ─── Networking ────────────────────────────────────────────────────

def stream_response(sock):
    """Yield text tokens from the server, handle special tags."""
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

                    # Check for end of response
                    if "<<END_OF_RESPONSE>>" in decoded:
                        idx = decoded.index("<<END_OF_RESPONSE>>")
                        to_yield = decoded[:idx]
                        remainder = decoded[idx + len("<<END_OF_RESPONSE>>"):]

                        if to_yield:
                            yield ("text", to_yield)

                        # Check remainder for special tags
                        parse_special_tags(remainder)
                        return

                    # Check for special tags within the stream
                    tag_start = decoded.find("<<")
                    if tag_start > 0:
                        yield ("text", decoded[:tag_start])
                        buffer = bytearray(decoded[tag_start:].encode('utf-8'))
                    elif tag_start == 0 and ">>" in decoded:
                        tag_end = decoded.index(">>") + 2
                        tag = decoded[:tag_end]
                        parse_special_tags(tag)
                        buffer = bytearray(decoded[tag_end:].encode('utf-8'))
                    elif tag_start == -1 and decoded:
                        yield ("text", decoded)
                        buffer.clear()
                    else:
                        pass
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
    """Parse special server tags like <<SAMPLE:SE>>."""
    global sample_covered

    sample_match = re.search(r'<<SAMPLE:([A-Z]+)>>', text)
    if sample_match:
        for letter in sample_match.group(1):
            if letter in SAMPLE_LABELS:
                sample_covered.add(letter)


def connect_to_server(scenario):
    while True:
        try:
            console.print(f"[dim]Connecting to server...[/]")
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(SOCKET_TIMEOUT)
            sock.connect((SERVER_IP, SERVER_PORT))
            sock.sendall(str(scenario).encode('utf-8'))
            patient_name = sock.recv(1024).decode('utf-8', errors='replace').strip()
            console.print(f"[green]Connected.[/] Patient: [bold cyan]{patient_name}[/]")
            return sock, patient_name
        except Exception as e:
            console.print(f"[red]Connection failed ({e}), retrying in {RECONNECT_DELAY}s...[/]")
            time.sleep(RECONNECT_DELAY)


def reconnect_and_resend(scenario, last_query):
    while True:
        sock, patient_name = connect_to_server(scenario)
        try:
            sock.sendall(last_query.encode('utf-8'))
            return sock, patient_name
        except Exception as e:
            console.print(f"[red]Resend failed: {e}. Retrying...[/]")
            sock.close()
            time.sleep(RECONNECT_DELAY)


# ─── Scenario selection ────────────────────────────────────────────

def choose_scenario():
    clear_screen()
    print_banner()
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

    rows = []
    for i in range(0, len(patients), 3):
        row = []
        for j in range(3):
            if i + j < len(patients):
                p = patients[i + j]
                row.extend([str(p[0]), p[1]])
            else:
                row.extend(["", ""])
        rows.append(row)

    for row in rows:
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


def timed_input(prompt_text, timeout):
    """Read a line from stdin with a timeout. Returns the line or None on timeout."""
    console.print(prompt_text, end="")
    sys.stdout.flush()
    ready, _, _ = select.select([sys.stdin], [], [], timeout)
    if ready:
        return sys.stdin.readline().rstrip('\n')
    return None


# ─── Reset session state ──────────────────────────────────────────

def reset_session():
    """Reset all session state for a new patient."""
    global sample_covered, start_time, conversation_log, ecg_offset
    sample_covered = set()
    start_time = time.time()
    conversation_log = []
    ecg_offset = 0


# ─── Main ─────────────────────────────────────────────────────────

def main():
    global last_activity, start_time, session_active

    clear_screen()
    print_banner()
    console.print()
    password = getpass.getpass("Enter password: ")
    if password != "":
        console.print("[bold red]Incorrect password. Exiting.[/]")
        sys.exit(1)

    while True:  # Outer loop for auto-restart
        scenario = choose_scenario()
        reset_session()
        last_activity = time.time()

        sock, patient_name = connect_to_server(scenario)
        redraw_screen(patient_name)

        last_query = None
        empty_input_count = 0
        EMPTY_INPUT_THRESHOLD = 3
        last_prompt_time = 0
        PROMPT_COOLDOWN = 7  # seconds
        should_restart = False

        while True:
            try:
                # Calculate remaining time before idle restart
                elapsed_idle = time.time() - last_activity
                remaining = max(1, IDLE_TIMEOUT - elapsed_idle)

                query = timed_input("\n[bold green]Doctor > [/]", timeout=remaining)

                # Timed out — auto-restart
                if query is None:
                    console.print("\n[dim yellow]Session timed out. Returning to patient selection...[/]")
                    time.sleep(2)
                    should_restart = True
                    break

                query = query.strip()
                last_activity = time.time()

                if len(query.encode('utf-8')) > MAX_PROMPT_LENGTH:
                    console.print(f"[red]Prompt too long! Limit is {MAX_PROMPT_LENGTH} bytes.[/]")
                    continue

                if query == '':
                    empty_input_count += 1
                    if empty_input_count >= EMPTY_INPUT_THRESHOLD:
                        console.print("[dim yellow]Please type a question for the patient.[/]")
                    continue
                else:
                    empty_input_count = 0

                if query.lower() == 'exit':
                    sock.close()
                    console.print("[dim]Goodbye![/]")
                    return

                # ── .switch command (hidden) ──
                if query.lower() == '.switch':
                    sock.close()
                    should_restart = True
                    break

                # ── .reset command ──
                if query.lower() == '.reset':
                    last_query = query
                    sock.sendall(query.encode('utf-8'))
                    response_text = ""
                    for tag_type, content in stream_response(sock):
                        if tag_type == "text":
                            response_text += content
                    conversation_log.append(("system", response_text.strip()))
                    redraw_screen(patient_name)
                    continue

                # ── Rate limiting ──
                current_time = time.time()
                if current_time - last_prompt_time < PROMPT_COOLDOWN:
                    wait_time = PROMPT_COOLDOWN - (current_time - last_prompt_time)
                    console.print(f"[dim yellow]Please wait {wait_time:.1f}s before your next question.[/]")
                    continue
                last_prompt_time = current_time

                # ── Regular question ──
                last_query = query
                conversation_log.append(("doctor", query))

                while True:
                    try:
                        sock.sendall(query.encode('utf-8'))
                        response_text = ""
                        console.print(f"\n[bold cyan]{patient_name}:[/] ", end="")
                        for tag_type, content in stream_response(sock):
                            if tag_type == "text":
                                console.print(content, end="", highlight=False)
                                response_text += content
                        console.print()

                        if response_text.strip():
                            conversation_log.append(("patient", response_text.strip()))

                        # Show updated SAMPLE coverage after each question
                        if sample_covered:
                            covered_str = ", ".join(
                                SAMPLE_LABELS[l] for l in sorted(sample_covered)
                            )
                            console.print(f"[dim green]  SAMPLE: {len(sample_covered)}/6 covered ({covered_str})[/]")

                        break  # Success
                    except (TimeoutError, ConnectionError) as e:
                        console.print(f"\n[red]Lost connection: {e}. Reconnecting...[/]")
                        sock.close()
                        sock, patient_name = reconnect_and_resend(scenario, last_query)
                        console.print("[green]Reconnected.[/]")

                last_activity = time.time()

            except KeyboardInterrupt:
                console.print("\n[dim]Exiting.[/]")
                sock.close()
                return

        # Clean up socket before restarting
        try:
            sock.close()
        except Exception:
            pass

        if not should_restart:
            break


if __name__ == '__main__':
    main()
