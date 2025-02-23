import streamlit as st
import streamlit.components.v1 as components

import openai
import requests
import os
import json
import base64
from dotenv import load_dotenv
import subprocess 


load_dotenv()

# Initialize session state for memories
if "memories" not in st.session_state:
    st.session_state["memories"] = {
        "age": None,
        "goals": [],
        "preferences": [],
        "motivations": [],
        "health conditions": []
    }
 

if "transcript" not in st.session_state:
    st.session_state["transcript"] = []

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
    for field in ["age", "goals", "preferences", "motivations", "health conditions"]:
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
                 Extract key user details in JSON format.
                    {
                        "age": <age or null>,
                        "goals": [<list of goals>],
                        "preferences": [<list of preferences>],
                        "motivations": [<list of motivations>],
                        "health conditions": [<list of health conditions>]
                    }
                """},
                {"role": "user", "content": user_input}
            ],
            max_tokens=150,
            temperature=0.5
        )
        # Append user input to transcript
        st.session_state["transcript"].append(user_input)
        return json.loads(response.choices[0].message.content)
    except:
        return {"age": None, "goals": [], "preferences": [], "motivations": [], "health conditions": []}

# Display Memory in Sidebar
with st.sidebar:
    st.markdown('<h1 style="font-size: 2em;">🦛 Hippopotamus AI </h1>', unsafe_allow_html=True)
    st.text('Ask me anything about health!')
    st.write("### Stored Memories")
    memory_output = ""
    for field in ["age", "goals", "preferences", "motivations", "health conditions"]:
        memory_output += f"**{field.capitalize()}:**<br>"
        items = st.session_state.memories.get(field, [])
        if isinstance(items, list):
            for item in items:
                if item:  # Only display non-empty items
                    memory_output += f"• {item}<br>"
        elif items:  # For non-list items (like age)
            memory_output += f"- {items}<br>"
    st.markdown(memory_output, unsafe_allow_html=True)

    # Add button to download transcript
    transcript_text = "\n".join(st.session_state["transcript"])
    st.download_button(
        label="Download Full Transcript",
        data=transcript_text if transcript_text else "No transcript available yet.",
        file_name="full_transcript.txt",
        mime="text/plain",
        disabled=not bool(st.session_state["transcript"])
    )

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
components.html(audio_recorder_script, height=100)


# Handle Uploaded Audio
uploaded_audio = st.file_uploader("Alternatively, upload pre-recorded audio", type=["webm"])

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
    st.write(f"📝 You: {transcription}")

    # Extract Information and Update Memory
    extracted_info = extract_information(transcription)
    update_memory(extracted_info)

    # Generate Chatbot Response
    def get_completion(user_input):
        # Retrieve stored memories
        age = st.session_state.memories.get("age")
        goals = ", ".join(st.session_state.memories.get("goals", []))
        preferences = ", ".join(st.session_state.memories.get("preferences", []))
        motivations = ", ".join(st.session_state.memories.get("motivations", []))
        conditions = ", ".join(st.session_state.memories.get("health conditions", []))
        
        # Construct memory summary for GPT
        memory_context = "Here is what I remember about the user:\n"
        if age:
            memory_context += f"- Age: {age}\n"
        if goals:
            memory_context += f"- Goals: {goals}\n"
        if preferences:
            memory_context += f"- Preferences: {preferences}\n"
        if motivations:
            memory_context += f"- Motivations: {motivations}\n"
        if conditions:
            memory_context += f"- Health Conditions: {conditions}\n"
        
        # Ensure memory context is empty if there is no stored data
        if memory_context == "Here is what I remember about the user:\n":
            memory_context = "The user has not shared any background information yet."

         # Construct messages for OpenAI API
        messages = [
             {"role": "system", "content": f"You are a friendly, helpful professional health coach. Keep replies short and avoid lists. Use this info to personalize your responses:\n\n{memory_context}"},
             {"role": "user", "content": user_input}
        ]
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=100
        )
        return response.choices[0].message.content

    bot_response = get_completion(transcription)
    st.write(f"🤖 Coach: {bot_response}")

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
            
            audio_html = f"""
            <div id="audio-container" style="padding: 20px; text-align: center; border-radius: 10px; background: #f5f5f5; margin: 10px 0;">
                <div id="audio-status" style="margin-bottom: 15px; font-size: 16px;">
                    Tap the button below to play the audio response
                </div>
                <audio id="audio-player">
                    <source src="data:audio/mp3;base64,{b64_audio}" type="audio/mp3">
                </audio>
                <button id="play-button" 
                        style="padding: 12px 24px; 
                               background-color: #4CAF50; 
                               color: white; 
                               border: none; 
                               border-radius: 5px; 
                               font-size: 16px; 
                               cursor: pointer;">
                    Play Audio 🔊
                </button>
            </div>
    
            <script>
            document.addEventListener('DOMContentLoaded', function() {{
                const audioPlayer = document.getElementById('audio-player');
                const playButton = document.getElementById('play-button');
                const statusDiv = document.getElementById('audio-status');
                let isPlaying = false;
    
                // Initialize audio
                audioPlayer.load();
    
                playButton.addEventListener('click', function() {{
                    if (!isPlaying) {{
                        // Try to play
                        const playPromise = audioPlayer.play();
                        
                        if (playPromise !== undefined) {{
                            playPromise.then(() => {{
                                isPlaying = true;
                                playButton.textContent = 'Pause ⏸️';
                                statusDiv.textContent = 'Playing audio response...';
                                console.log('Audio playback started');
                            }}).catch(error => {{
                                console.error('Playback failed:', error);
                                statusDiv.textContent = 'Playback failed. Please try again.';
                            }});
                        }}
                    }} else {{
                        audioPlayer.pause();
                        isPlaying = false;
                        playButton.textContent = 'Play Audio 🔊';
                        statusDiv.textContent = 'Audio paused. Tap to resume.';
                    }}
                }});
    
                // Handle audio ending
                audioPlayer.addEventListener('ended', function() {{
                    isPlaying = false;
                    playButton.textContent = 'Play Again 🔄';
                    statusDiv.textContent = 'Audio finished. Tap to replay.';
                }});
    
                // Handle audio errors
                audioPlayer.addEventListener('error', function(e) {{
                    console.error('Audio error:', e);
                    statusDiv.textContent = 'Error playing audio. Please try again.';
                    playButton.textContent = 'Retry 🔄';
                }});
            }});
            </script>
            """
            components.html(audio_html, height=150)

