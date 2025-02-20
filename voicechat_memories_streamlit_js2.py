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
let mediaRecorder;
let audioChunks = [];
let isRecording = false;
let stream;

// Function to handle iOS Safari constraints
function getiOSMediaConstraints() {
    return {
        audio: {
            // iOS Safari specific constraints
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true
        }
    };
}

// Check if running on iOS
function isiOS() {
    return [
        'iPad Simulator',
        'iPhone Simulator',
        'iPod Simulator',
        'iPad',
        'iPhone',
        'iPod'
    ].includes(navigator.platform)
    || (navigator.userAgent.includes("Mac") && "ontouchend" in document);
}

async function startRecording() {
    try {
        if (isRecording) return;
        
        const constraints = isiOS() ? getiOSMediaConstraints() : { audio: true };
        stream = await navigator.mediaDevices.getUserMedia(constraints);
        
        // iOS Safari prefers this mime type
        const mimeType = 'audio/webm;codecs=opus';
        
        mediaRecorder = new MediaRecorder(stream, {
            mimeType: mimeType,
            audioBitsPerSecond: 128000
        });
        
        audioChunks = [];
        mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                audioChunks.push(event.data);
            }
        };
        
        // Start recording with shorter timeslices for more frequent ondataavailable events
        mediaRecorder.start(100);
        isRecording = true;
        
        document.getElementById("recording-status").innerText = "Recording... 🎙️";
    } catch (error) {
        console.error("Error starting recording:", error);
        document.getElementById("recording-status").innerText = "Error starting recording: " + error.message;
    }
}

async function stopRecording() {
    if (!isRecording) return;
    
    try {
        isRecording = false;
        
        // Return a promise that resolves when the recording is fully stopped
        return new Promise((resolve) => {
            mediaRecorder.onstop = async () => {
                try {
                    // Stop all tracks in the stream
                    stream.getTracks().forEach(track => track.stop());
                    
                    const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                    const file = new File([audioBlob], "recorded_audio.webm", { 
                        type: "audio/webm",
                        lastModified: Date.now()
                    });
                    
                    // Handle file upload
                    const uploader = window.parent.document.querySelector("input[type='file']");
                    if (uploader) {
                        const dataTransfer = new DataTransfer();
                        dataTransfer.items.add(file);
                        uploader.files = dataTransfer.files;
                        uploader.dispatchEvent(new Event('change', { bubbles: true }));
                        
                        document.getElementById("recording-status").innerText = "Recording stopped and uploaded ✅";
                    } else {
                        document.getElementById("recording-status").innerText = "Error: Could not find file uploader";
                    }
                    
                    resolve();
                } catch (error) {
                    console.error("Error in stop handler:", error);
                    document.getElementById("recording-status").innerText = "Error processing recording: " + error.message;
                    resolve();
                }
            };
            
            mediaRecorder.stop();
        });
    } catch (error) {
        console.error("Error stopping recording:", error);
        document.getElementById("recording-status").innerText = "Error stopping recording: " + error.message;
    }
}

// Add error handling for getUserMedia
navigator.mediaDevices.getUserMedia({ audio: true })
    .catch(function(err) {
        document.getElementById("recording-status").innerText = 
            "Please ensure microphone permissions are granted. Error: " + err.message;
    });
</script>

<button onclick="startRecording()" style="padding: 10px; margin: 5px; background-color: #4CAF50; color: white; border: none; border-radius: 5px;">
    🎙️ Start Recording
</button>
<button onclick="stopRecording()" style="padding: 10px; margin: 5px; background-color: #f44336; color: white; border: none; border-radius: 5px;">
    🛑 Stop Recording
</button>
<p id="recording-status" style="margin-top: 10px;">Click "Start Recording" to begin.</p>
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
        # Convert audio to base64 for embedding
        with open(tts_audio_file, "rb") as audio_file:
            audio_bytes = audio_file.read()
            b64_audio = base64.b64encode(audio_bytes).decode()
            audio_html = f"""
            <audio id='tts-audio' autoplay>
                <source src='data:audio/mp3;base64,{b64_audio}' type='audio/mp3'>
                Your browser does not support the audio element.
            </audio>
            <script>
                var audio = document.getElementById('tts-audio');
                audio.play();
            </script>
            """
            components.html(audio_html)

# Sidebar for Memory Display
with st.sidebar:
   st.markdown('<h1 style="font-size: 2em;">🦛 Hippopotamus AI </h1>', unsafe_allow_html=True)
   st.text('Ask me anything about health!')
   if st.sidebar.button("Show Memories"):
       display_memory()
