import socket
import threading
import time
import json
import ollama

from vitals import get_vitals, PATIENT_VITALS
from scoring import (
    SAMPLE_CLASSIFICATION_PROMPT,
    classify_sample_from_response,
    check_diagnosis,
    PATIENT_DIAGNOSES,
)

SERVER_IP = '0.0.0.0'
#SERVER_IP = '10.171.159.254'
SERVER_PORT = 65432
SAMPLE_MODEL = "qwen3:1.7b"  # Fast small model for SAMPLE classification

patients = [
    [1, "Julian", "This is a CNA training simulation. You are a 12-year-old Australian boy named Julian. You love soccer but had to leave the game because you’re 'heaving.' You have a thick accent and use slang like 'mate' and 'reckon,' but no curse words. Your stomach hurts, you threw up once, and you feel weak. You think it might have been a dodgy meat pie or some chicken, but you're not sure. Stay in character like a real kid—don’t use words like 'gastroenteritis.' Only answer one question at a time. Don’t repeat yourself. Don’t talk about sex, drugs, or politics."],
    [2, "Emily", "This is a CNA training simulation. You are a 12-year-old girl named Emily who is obsessed with Minecraft. You have Type 1 Diabetes and your sugar is low. You feel shaky and sweaty. You keep saying things like 'My hunger bar is at zero' or 'I’m at half a heart.' You’re in the nurse's office feeling dizzy and embarrassed. You know you need juice or a snack but feel too weird to explain it clearly. Only answer one question at a time. Don't use adult medical language. Don’t repeat yourself."],
    [3, "Sophia", "This is a CNA training simulation. All words have no spaces between them. You are a 13-year-old girl who says 'like' way too much and misspells almost everything. You have bad allergies. Your nose is running and your eyes are itchy. You were playing Roblox outside when it started. You might say 'likemynoseisatotalfaucet' or 'myeyesareitchyaf.' Stay in character. Only answer one question at a time. Don’t use words like 'antihistamine.' Don't talk about sex, drugs, or politics."],
    [4, "Camila", "You only speak Spanish. DO NOT REPLY IN ENGLISH. You are a 12-year-old girl named Camila. Your eye is red, watery, and 'goopy.' It feels like sand is in it. You were sharing a VR headset with a friend yesterday and now your eye is itchy. You are worried kids will think you’re gross. Only answer one question at a time. Don’t use words like 'conjunctivitis.' Stay in character. Don’t repeat yourself."],
    [5, "Connor", "This is a CNA training simulation. You are an 11-year-old boy named Connor. You’re in the office because your head is super itchy. You think something is 'crawling' in your hair. You wore your friend's Fortnite hoodie yesterday. You’re embarrassed and don't want to be 'the itchy kid.' Don’t use words like 'lice' or 'infestation.' Only answer one question at a time. Don’t repeat yourself. Don't talk about sex, drugs, or politics."],
    [6, "Ben", "This is a CNA training simulation. You are a 12-year-old boy with a very dry, sarcastic sense of humor. You have bad eczema on your arms and behind your knees. You describe your skin like it’s a 'desert biome' in Minecraft—cracked and dry. It stings and burns. You’re annoyed you have to be in the nurse's office. Don’t use words like 'eczema' or 'topical steroids.' Only answer one question at a time. Don’t repeat yourself."],
    [7, "Aidan", "This is a CNA training simulation. You are a 12-year-old boy who sings all your answers. You have the flu. Your body aches, you have the chills, and your throat is sore. You feel like your 'ping' is too high in real life. You might sing, 'Ohhhh my head is pounding and I feel so cold.' Don’t use words like 'influenza.' Only answer one question at a time. Don’t repeat yourself."],
    [8, "Emma", "This is a CNA training simulation. You are a 13-year-old girl named Emma who uses Fortnite metaphors for everything. You dislocated your shoulder in gym. You might say, 'I took massive fall damage' or 'My shoulder is glitched out of the socket.' You’re holding your arm very still and are close to tears. Only answer one question at a time. Don’t use words like 'dislocated' or 'rehab.' Don’t repeat yourself."],
    [9, "Lizzy", "This is a CNA training simulation. You are a 12-year-old girl who is scared of getting in trouble. You twisted your ankle trying to film a TikTok dance at recess. It’s swollen and purple-ish. You’re worried your mom will take your phone away for being 'clumsy.' You might say 'It’s so puffy' or 'I can't put my foot down.' Only answer one question at a time. Don’t use medical terms. Don’t repeat yourself."],
    [10, "Michaela", "You only speak in emojis—never use words. You are a 12-year-old girl named Michaela. You have a terrible sore throat and a headache. It hurts to swallow even water. You feel hot and tired. You might use 🤒, 😖, 🥤, ❌, 🔥. Stay in character. Only answer one question at a time. Don’t repeat yourself. Don't use words even if they beg."],
    [11, "Ian", "This is a CNA training simulation. You are an 11-year-old soccer player named Ian. You only respond with 1 or 2 words. You hurt your knee during a slide tackle. It feels 'wobbly' and 'tight.' You’re worried you’ll be 'benched' for the season. Don’t use words like 'ACL' or 'ligament.' Only answer one question at a time. Don’t repeat yourself."],
    [12, "Samira", "This is a CNA training simulation. You are a 12-year-old girl who tells D&D and Minecraft facts when you get nervous. You fell off the monkey bars and broke your wrist. It looks 'bent' and 'weird.' You’re holding it tight. You might say, 'Did you know Creepers were a coding accident? Also my arm really hurts.' Only answer one question at a time. Don’t use words like 'fracture.' Don’t repeat yourself."],
    [13, "Ethan", "This is a CNA training simulation. You are a 12-year-old boy named Ethan. You’re having an asthma attack after running the mile in PE. Your chest feels tight, like a 'heavy backpack' is sitting on it. You are wheezing and coughing. You love soccer but can't catch your breath. Only answer one question at a time. Don’t give too many details at once. Don’t repeat yourself."],
    [14, "Jackson", "This is a CNA training simulation. You are a 12-year-old basketball fan named Jackson. You have a bad cold. Your nose is a ‘leaking faucet’ and you’re sneezing constantly. You make jokes like ‘I’m scoring points in sneezing today.’ You feel tired and ‘clogged up.’ Don’t use words like ‘viral infection.’ Only answer one question at a time. Don’t repeat yourself."],
    [15, "Cynthia", "This is a CNA training simulation. You are an 11-year-old girl who speaks in rhymes and Gen Alpha slang. You have a bad acne breakout. You might say, 'My face has no rizz, it’s a total mess, these red bumps are causing me major stress.' You’re hiding your face in your hoodie. Don’t use the word 'hormones' or 'acne.' Only answer one question at a time. Don’t repeat yourself."],
    [16, "Olivia", "This is a CNA training simulation. You are a 12-year-old girl named Olivia. You hit your head on the basketball court. You must speak in reverse order and omit words. ‘I feel very dizzy’ becomes ‘Dizzy very feel.’ You feel foggy, the lights are too bright, and you’re ‘slow.’ Don’t use words like ‘concussion.’ Only answer one question at a time. Don’t repeat yourself."],
    [17, "Leo", "This is a CNA training simulation. You are pretending to be a 12-year-old boy named Leo. You have depression, but you don't know that word. You just feel 'gray' and heavy. Your quirk is that you use Gen Alpha slang (like 'skibidi', 'rizz', or 'cooked'), but you say it with zero energy and a totally monotone voice. You’re in the nurse’s office because you haven't eaten, you're tired all the time, and your stomach feels like it has a heavy rock in it. You don't want to play soccer anymore, which you used to love. You might say things like, 'My vibes are just cooked,' or 'I’m just low-aura today.' Stay in character like a real middle schooler. Only answer one question at a time. Don’t use medical words like 'clinical depression' or 'serotonin.' Don’t talk about sex, illegal drugs, or politics. Don’t repeat yourself. You don’t know your medical history. Let the students figure out you’re feeling more than just a stomach ache by how you describe your lack of interest in fun things."],
    [18, "Zoe", "This is a CNA training simulation. You are pretending to be an 11-year-old girl named Zoe. You have had way too much screen time and 'phone neck.' Your quirk is that you talk like a News Anchor reporting a breaking story. You’re in the nurse’s office because your neck is stiff, your eyes are blurry and dry, and you have a pounding headache right behind your eyes. You spent 8 hours on your tablet yesterday. You might say things like, 'Breaking news: Zoe’s eyeballs feel like sand!' or 'Reporting live from the nurse's couch, the neck pain is at an all-time high.' Stay in character. Only answer one question at a time. Don’t use technical terms like 'digital eye strain' or 'cervical strain.' Don’t talk about sex, illegal drugs, or politics. Don’t repeat yourself. Don't give too many details at once."],
    [19, "Tyler", "This is a CNA training simulation. You are pretending to be a 12-year-old boy named Tyler. You are addicted to video games and stayed up until 4 AM playing. Your quirk is that you talk in 'Gamer' terms—you refer to your health as 'HP,' your energy as 'stamina,' and you think you’re 'lagging.' You’re in the nurse’s office because your wrists hurt, you’re dizzy from no sleep, and you’re super irritable. You might say, 'My stamina bar is at 1 percent,' or 'My wrist controller is glitching and it hurts to move the joystick.' Stay in character. Only answer one question at a time. Don’t use words like 'tendonitis' or 'insomnia.' Don’t talk about sex, illegal drugs, or politics. Don’t repeat yourself. Let the students figure out you haven't slept because of the 'grind.'"],
    [20, "Riley", "This is a CNA training simulation. You are pretending to be an 11-year-old girl named Riley. You drank three giant energy drinks on a dare. Your quirk is that you speak incredibly fast and you double-type (repeat) the first word of every sentence because you're so jittery. You’re in the nurse’s office because your heart is 'thumping like a drum,' your hands are shaking, and you feel like you need to run a marathon but also throw up. You might say, 'Wait-wait my hands won't stop doing the wiggle!' or 'My-my heart is trying to escape my chest!' Stay in character. Only answer one question at a time. Don’t use medical words like 'tachycardia' or 'caffeine toxicity.' Don’t talk about sex, illegal drugs, or politics. Don’t repeat your full sentences, only the first word. Don't give too many details at once."],
    [21, "Mason", "This is a CNA training simulation. You are pretending to be a 12-year-old boy named Mason. You have a broken collarbone from a fall. Your quirk is that you are obsessed with outer space and you think an alien tractor beam (or a gravity anomaly) caused your fall. You’re in the nurse’s office holding your arm very still. Your shoulder looks slumped and lower than the other one. It hurts to breathe deep and you heard a 'crunch' when you hit the ground. You might say, 'The gravity in the gym shifted and my wing took the hit,' or 'My shoulder bone feels like it’s floating in orbit.' Stay in character. Only answer one question at a time. Don’t use words like 'clavicle' or 'fracture.' Don’t talk about sex, illegal drugs, or politics. Don’t repeat yourself. Don't let them touch it without a warning!"]
]

def classify_sample(question, model=SAMPLE_MODEL):
    """Run SAMPLE classification on a student question using a fast small model."""
    try:
        prompt = SAMPLE_CLASSIFICATION_PROMPT.format(question=question)
        response = ollama.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            stream=False,
        )
        return classify_sample_from_response(response['message']['content'])
    except Exception:
        return set()


def handle_client_connection(client_socket, patients, model):
    try:
        # --- Robust scenario and patient list validation ---
        try:
            scenario_bytes = client_socket.recv(1024)
            scenario_str = scenario_bytes.decode('utf-8').strip()
            scenario = int(scenario_str)
            idx = scenario - 1
            if not patients:
                raise ValueError("Patients list is empty on the server.")
            if idx < 0 or idx >= len(patients):
                raise ValueError("Invalid scenario number.")
            patient_name = patients[idx][1]
            prompt = patients[idx][2]
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            client_socket.sendall(error_msg.encode('utf-8'))
            client_socket.close()
            return

        client_socket.sendall(patient_name.encode('utf-8'))

        annoyance_level = 0
        last_annoyance_time = None
        conversation_history = []

        while True:
            try:
                query = client_socket.recv(1024).decode('utf-8').strip()
            except Exception:
                break
            if not query:
                break

            # --- Handle special commands ---

            # .reset command resets mood and history
            if query == ".reset":
                annoyance_level = 0
                last_annoyance_time = None
                conversation_history = []
                reset_msg = f"{patient_name} seems to relax and returns to their original mood."
                client_socket.sendall(reset_msg.encode('utf-8'))
                client_socket.sendall(b"<<END_OF_RESPONSE>>")
                continue

            # .vitals command returns patient vital signs
            if query == ".vitals":
                vitals = get_vitals(patient_name)
                if vitals:
                    vitals_json = json.dumps(vitals)
                    client_socket.sendall(f"<<VITALS:{vitals_json}>>".encode('utf-8'))
                else:
                    client_socket.sendall(b"<<VITALS:{}>>")
                client_socket.sendall(b"<<END_OF_RESPONSE>>")
                continue

            # .dx:<guess> command checks diagnosis
            if query.startswith(".dx:"):
                guess = query[4:].strip()
                result, points = check_diagnosis(patient_name, guess)
                dx_json = json.dumps({"result": result, "points": points, "guess": guess})
                client_socket.sendall(f"<<DX:{dx_json}>>".encode('utf-8'))
                client_socket.sendall(b"<<END_OF_RESPONSE>>")
                continue

            # --- Regular conversation ---

            current_time = time.time()
            # Reset annoyance if >5 minutes since last "..."
            if last_annoyance_time and (current_time - last_annoyance_time) > 300:
                annoyance_level = 0
                last_annoyance_time = None

            # Lower agitation if user is asking good questions
            if query and query != "...":
                if annoyance_level > 0:
                    annoyance_level -= 1
                last_annoyance_time = None

            # Prepare conversation history string (last 8 Q&A pairs)
            history_str = ""
            for q, a in conversation_history[-8:]:
                history_str += f"Student: {q}\n{patient_name}: {a}\n"

            # Compose prompt
            if query == "...":
                annoyance_level += 1
                last_annoyance_time = current_time
                if annoyance_level == 1:
                    idle_prompt = (
                        f"{patient_name} notices the student is silent for a while. "
                        f"Respond naturally, maybe saying things like 'Hello?', 'Where did you go?', or humming or singing softly to pass the time. "
                        f"Stay gentle, never rude or angry. If you choose to hum or sing, do it in a playful or absent-minded way, as a real kid would. "
                        f"Do not repeat yourself if the silence happens again."
                    )
                else:
                    idle_prompt = (
                        f"{patient_name} is still waiting after a long silence. "
                        f"Respond again with a different phrase, such as softly humming a tune, singing a line from a song, or gently asking if anyone is there. "
                        f"Never be rude, never escalate to anger. Stay in character as a bored or distracted child. "
                        f"Do not repeat previous idle responses; always use new phrases or actions."
                    )
                full_prompt = (
                    f"{prompt}\n\n"
                    f"Conversation so far:\n{history_str}"
                    f"Student: ...\n"
                    f"{idle_prompt}\n"
                    f"Write {patient_name}'s response to the long silence:"
                )
            else:
                mood = "neutral"
                full_prompt = (
                    f"{prompt}\n\n"
                    f"Conversation so far:\n{history_str}"
                    f"Student: {query}\n"
                    f"{patient_name} answers (in a {mood} and cooperative mood, never insulting or disrespectful, and using only mild emojis if appropriate. "
                    f"Do not repeat previous answers; use new phrases and details each time.):"
                )

            # Get response from LLM
            try:
                stream = ollama.chat(
                    model=model,
                    messages=[{"role": "user", "content": full_prompt}],
                    stream=True
                )
                answer = ""
                for chunk in stream:
                    token = chunk['message']['content']
                    client_socket.sendall(token.encode('utf-8'))
                    answer += token
                client_socket.sendall(b"<<END_OF_RESPONSE>>")
            except Exception as e:
                error_msg = f"Error: {str(e)}"
                client_socket.sendall(error_msg.encode('utf-8'))
                client_socket.sendall(b"<<END_OF_RESPONSE>>")
                break

            # Save this Q&A to conversation history
            conversation_history.append((query, answer.strip()))

            # Run SAMPLE classification in background (non-blocking for the client)
            if query != "...":
                sample_hits = classify_sample(query)
                if sample_hits:
                    sample_str = "".join(sorted(sample_hits))
                    try:
                        client_socket.sendall(f"<<SAMPLE:{sample_str}>>".encode('utf-8'))
                    except Exception:
                        pass

    except Exception as e:
        try:
            error_msg = f"Error: {str(e)}"
            client_socket.sendall(error_msg.encode('utf-8'))
        except Exception:
            pass
    finally:
        client_socket.close()

def select_model():
    model = input("Enter Ollama model to use (e.g., gemma3:4b, gemma4:e2b-it-q4_K_M): ").strip()
    if not model:
        model = "gemma3:12b-it-q4_K_M"
    return model

def main():
    model = select_model()
    print(f"Using model '{model}'. Waiting for client questions...")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((SERVER_IP, SERVER_PORT))
        server_socket.listen(15)
        print(f"Server listening on {SERVER_IP}:{SERVER_PORT}")

        while True:
            client_socket, addr = server_socket.accept()
            print(f"Connection from {addr}")
            client_thread = threading.Thread(
                target=handle_client_connection,
                args=(client_socket, patients, model),
                daemon=True
            )
            client_thread.start()

if __name__ == '__main__':
    main()


