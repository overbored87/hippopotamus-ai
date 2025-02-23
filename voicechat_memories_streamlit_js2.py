import streamlit as st
import streamlit.components.v1 as components

import openai
import requests
import os
import json
import base64
from dotenv import load_dotenv
from pydub import AudioSegment 
import subprocess 


load_dotenv()

# Initialize session state for memories
if "memories" not in st.session_state:
    st.session_state["memories"] = {
        "age": None,
        "goals": [],
        "preferences": [],
        "motivations": [],
        "conditions": []
    }

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

# OpenAI Client
client = openai.OpenAI(api_key=OPENAI_API_KEY)

# Memory Storage
MEMORY_FILE = "user_memories.json"

def load_memory():
    try:
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_memory(memory):
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f)

def update_memory(extracted_data):
    for field in ["age", "goals", "preferences", "motivations", "conditions"]:
        if field in extracted_data and extracted_data[field]:
            if field == "age":
                st.session_state.memories[field] = extracted_data[field]
            else:
                st.session_state.memories[field] = list(set(st.session_state.memories.get(field, []) + extracted_data[field]))
    
    save_memory(st.session_state.memories)

def extract_information(user_input):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": """
                 Extract key user details in JSON format:
                    {
                        "age": <age or null>,
                        "goals": [<list of goals>],
                        "preferences": [<list of preferences>],
                        "motivations": [<list of motivations>],
                        "conditions": [<list of conditions>]
                    }
                """},
                {"role": "user", "content": user_input}
            ],
            max_tokens=150,
            temperature=0.5
        )
        return json.loads(response.choices[0].message.content)
    except:
        return {"age": None, "goals": [], "preferences": [], "motivations": [], "conditions": []}

# Display Memory in Sidebar
def display_memory():
    st.sidebar.write("### Stored Memories")
    memory_output = ""
    for field in ["age", "goals", "preferences", "motivations", "conditions"]:
        memory_output += f"**{field.capitalize()}:**<br>"
        items = st.session_state.memories.get(field, [])
        if isinstance(items, list):
            for item in items:
                memory_output += f"- {item}<br>"
        elif items:
            memory_output += f"- {items}<br>"
    st.sidebar.markdown(memory_output, unsafe_allow_html=True)

# Improved JavaScript for Recording and Auto-Uploading Audio
audio_recorder_script = """
<script>
let mediaRecorder = null;
let audioChunks = [];
let recordingStream = null;

async function requestMicrophonePermission() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        document.getElementById('status').textContent = 'Microphone access granted';
        stream.getTracks().forEach(track => track.stop());
        return true;
    } catch (err) {
        document.getElementById('status').textContent = 'Error: ' + err.message;
        return false;
    }
}

async function startRecording() {
    try {
        // Clear previous recordings
        audioChunks = [];
        
        // Get audio stream
        recordingStream = await navigator.mediaDevices.getUserMedia({
            audio: {
                echoCancellation: true,
                noiseSuppression: true
            }
        });

        // Create recorder
        mediaRecorder = new MediaRecorder(recordingStream);

        // Handle data
        mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                audioChunks.push(event.data);
            }
        };

        // Start recording
        mediaRecorder.start();
        
        // Update UI
        document.getElementById('startBtn').disabled = true;
        document.getElementById('stopBtn').disabled = false;
        document.getElementById('status').textContent = 'Recording...';
        
    } catch (err) {
        document.getElementById('status').textContent = 'Start Error: ' + err.message;
    }
}

function stopRecording() {
    if (!mediaRecorder) {
        document.getElementById('status').textContent = 'No recording in progress';
        return;
    }

    mediaRecorder.onstop = async () => {
        try {
            // Stop all tracks
            if (recordingStream) {
                recordingStream.getTracks().forEach(track => track.stop());
            }

            // Create blob
            const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
            const audioFile = new File([audioBlob], 'recording.webm', {
                type: 'audio/webm'
            });

            // Find Streamlit's file uploader
            const uploader = window.parent.document.querySelector('input[type="file"]');
            if (uploader) {
                const dt = new DataTransfer();
                dt.items.add(audioFile);
                uploader.files = dt.files;
                uploader.dispatchEvent(new Event('change', { bubbles: true }));
                document.getElementById('status').textContent = 'Recording uploaded';
            } else {
                document.getElementById('status').textContent = 'Error: Could not find uploader';
            }
        } catch (err) {
            document.getElementById('status').textContent = 'Stop Error: ' + err.message;
        }
    };

    mediaRecorder.stop();
    document.getElementById('startBtn').disabled = false;
    document.getElementById('stopBtn').disabled = true;
}

// Request permission on page load
window.onload = requestMicrophonePermission;
</script>

<div style="padding: 20px; text-align: center;">
    <button id="startBtn" 
            onclick="startRecording()" 
            style="padding: 10px 20px; margin: 5px; background-color: #4CAF50; color: white; border: none; border-radius: 5px;">
        Start Recording
    </button>
    <button id="stopBtn" 
            onclick="stopRecording()" 
            style="padding: 10px 20px; margin: 5px; background-color: #f44336; color: white; border: none; border-radius: 5px;"
            disabled>
        Stop Recording
    </button>
    <p id="status" style="margin-top: 10px;">Waiting for microphone permission...</p>
</div>
"""

# Inject the improved JavaScript into Streamlit
components.html(audio_recorder_script, height=200)


# Handle Uploaded Audio
uploaded_audio = st.file_uploader("Upload Recorded Audio", type=["webm"])

if uploaded_audio:
    with open("user_input.webm", "wb") as f:
        f.write(uploaded_audio.read())
    st.success("Audio uploaded successfully. Processing...")
    
    
    # Convert WebM to WAV
    # Convert WebM to WAV using FFmpeg
    def convert_webm_to_wav_ffmpeg(webm_path, wav_path):
       try:
           command = ["ffmpeg", "-y", "-i", webm_path, wav_path]
           subprocess.run(command, check=True)
       except subprocess.CalledProcessError as e:
           st.error(f"FFmpeg conversion failed: {e}")

    convert_webm_to_wav_ffmpeg("user_input.webm", "user_input.wav")

    # Transcribe Audio with Whisper
    def transcribe_audio(audio_path):
        with open(audio_path, "rb") as audio_file:
            response = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="en",
                response_format="text"  # Force text output
            )
        return response

    transcription = transcribe_audio("user_input.wav")
    st.write(f"📝 User: {transcription}")

    # Extract Information and Update Memory
    extracted_info = extract_information(transcription)
    update_memory(extracted_info)

    # Generate Chatbot Response
    def get_completion(user_input):
        messages = [
            {"role": "system", "content": "You are a friendly AI assistant. Keep replies short."},
            {"role": "user", "content": user_input}
        ]
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=100
        )
        return response.choices[0].message.content

    bot_response = get_completion(transcription)
    st.write(f"🤖 Chatbot: {bot_response}")

    # Convert Text-to-Speech (TTS) using ElevenLabs
    def text_to_speech(text, voice_id="mbL34QDB5FptPamlgvX5"):
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {
        "Content-Type": "application/json",
        "xi-api-key": ELEVENLABS_API_KEY
        }
        payload = {
            "text": text,
            "voice_settings": {"stability": 0.8, "similarity_boost": 1.0}
        }

        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            with open("response.mp3", "wb") as audio_file:
                audio_file.write(response.content)
            return "response.mp3"
        else:
            st.error(f"Error in TTS API call: {response.status_code}, {response.text}")
            return None

    tts_audio_file = text_to_speech(bot_response)
    if tts_audio_file:
        with open(tts_audio_file, "rb") as audio_file:
            audio_bytes = audio_file.read()
            b64_audio = base64.b64encode(audio_bytes).decode()
        
            # Updated audio player with iOS compatibility
            audio_html = f"""
            <div id="audio-container">
                <div id="audio-status" style="text-align: center; padding: 10px;">
                    Tap anywhere to enable audio responses
                </div>
                <audio id="audio-player" style="display: none">
                    <source src="data:audio/mp3;base64,{b64_audio}" type="audio/mp3">
                </audio>
            </div>
            <script>
            let audioEnabled = false;

            document.addEventListener('touchstart', function() {{
                if (!audioEnabled) {{
                    audioEnabled = true;
                    document.getElementById('audio-status').textContent = 'Audio responses enabled!';
                    document.getElementById('audio-status').style.color = '#4CAF50';
                    
                    // Try to play the audio immediately
                    const playPromise = player.play();
                    if (playPromise !== undefined) {{
                        playPromise.then(() => {{
                            console.log('Audio playback started');
                        }}).catch(error => {{
                            console.error("Playback failed:", error);
                            document.getElementById('audio-status').textContent = 'Tap to play audio manually';
                        }});
                    }}
                }}
            }}, {{ once: true }});
            </script>
        """
        components.html(audio_html, height=80)

# Sidebar for Memory Display
with st.sidebar:
   st.markdown('<h1 style="font-size: 2em;">🦛 Hippopotamus AI </h1>', unsafe_allow_html=True)
   st.text('Ask me anything about health!')
   if st.sidebar.button("Show Memories"):
       display_memory()
