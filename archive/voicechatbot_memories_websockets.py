# -*- coding: utf-8 -*-
"""
Created on Sat May  4 15:03:02 2024

@author: User
"""

## This is a GPT talkbot that runs on GPT-4o-mini, hosted in streamlit

# Importing the OpenAI library and initialising the API key

import streamlit as st
import openai
import requests # required for API calls to Elevenlabs
import json # for saving and loading memory
import speech_recognition as sr  # For recording and recognizing voice input
import asyncio
import websockets
import threading
from pydub import AudioSegment 
from pydub.playback import play 
import socket


from dotenv import load_dotenv
import os

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")


# Creating an instance of the OpenAI client using the provided API key

client = openai.OpenAI(api_key = OPENAI_API_KEY)

################################ MEMORY HANDLING #################################################
# Load memory from JSON file 
MEMORY_FILE = "user_memories.json"

def load_memory():
    try:
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}  # Return an empty dictionary if no file exists
    except json.JSONDecodeError:
        return {}  # Handle corrupted files

# Save Memory to JSON File
def save_memory(memory):
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f)

def update_memory(extracted_data):
    if "age" in extracted_data and extracted_data["age"]:
        # Update age if new information is provided
        st.session_state.memories["age"] = extracted_data["age"]
    
    for field in ["goals", "preferences", "motivations", "conditions"]:
        if field in extracted_data and extracted_data[field]:
            # Add unique entries to the corresponding list
            current_list = set(st.session_state.memories[field])  # Use a set for uniqueness
            new_entries = set(extracted_data[field])  # Extracted data should also be a list
            updated_list = list(current_list.union(new_entries))  # Combine old and new entries
            st.session_state.memories[field] = updated_list
    
    save_memory(st.session_state.memories)  # Save changes to the file

# Extract Salient Information
def extract_information(user_input):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": """
                 Extract key details about the user in the following JSON format:
                    {
                        "age": <age or null>,
                        "goals": [<list of goals>],
                        "preferences": [<list of preferences>],
                        "motivations": [<list of motivations],
                        "conditions": [<list of conditions>]
                    }
                    If the user does not provide specific details, use null for missing fields.
                    """},
                {"role": "user", "content": user_input}
            ],
            max_tokens=150,
            temperature=0.5
        )
        extracted_data = json.loads(response.choices[0].message.content)
        
        # Ensure lists for goals, preferences, and conditions
        for field in ["goals", "preferences", "motivations", "conditions"]:
            if field not in extracted_data or not isinstance(extracted_data[field], list):
                extracted_data[field] = []
        
        return extracted_data
    except Exception as e:
        st.error(f"Error extracting information: {e}")
        return {
            "age": None,
            "goals": [],
            "preferences": [],
            "motivations": [],
            "conditions": []
        }
    
# Function to display memory
def display_memory():
    st.sidebar.write("### Stored Memories")
    age = st.session_state.memories.get("age")
    memory_output = ""

    if age:
        memory_output += f"**Age:** {age}<br>"

    for field in ["goals", "preferences", "motivations", "conditions"]:
        memory_output += f"**{field.capitalize()}:**<br>"
        if st.session_state.memories[field]:
            for item in st.session_state.memories[field]:
                memory_output += f"- {item}<br>"
        else:
            memory_output += "No entries.<br>"

    # Render the formatted memory output with no gaps
    st.sidebar.markdown(memory_output, unsafe_allow_html=True)
    

###########################################################################################

# Function to record audio from the microphone and save it to a file
def record_audio():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        st.info("Press the button and speak now...")
        recognizer.adjust_for_ambient_noise(source, duration=1)
        try:
            audio = recognizer.listen(source, timeout=10, phrase_time_limit=30)
            text = recognizer.recognize_google(audio)
            st.write(f"✅ Recognized Speech: {text}")
            return text
        except sr.UnknownValueError:
            st.warning("Could not understand audio. Try again.")
            return None
        except sr.WaitTimeoutError:
            st.warning("No speech detected. Check your microphone.")
            return None

###########################################################################################
# Function to transcribe audio using OpenAI Whisper
def transcribe_audio(audio_file_path):
    try:
        with open(audio_file_path, "rb") as audio_file:
            response = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="en" # force transcription in english
            )
            return(response.text)
    except Exception as e:
        st.error(f"An error occurred during transcription: {e}")
        return None

############################################################################################
# Defining a function that sends a prompt to the OpenAI API and retrieves the API's response 

def get_completion(user_input, client, model="gpt-4o-mini"):
    # Retrieve stored memories
    age = st.session_state.memories.get("age")
    goals = ", ".join(st.session_state.memories.get("goals", []))
    preferences = ", ".join(st.session_state.memories.get("preferences", []))
    motivations = ", ".join(st.session_state.memories.get("motivations", []))
    conditions = ", ".join(st.session_state.memories.get("conditions", []))

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
    try:
        response = client.chat.completions.create(
        model = model,
        messages = messages,
        max_tokens = 100,
        temperature = 0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"Error getting response from OpenAI: {e}")
        return None 

############################################################################################
# Function to convert text to speech using ElevenLabs

def text_to_speech(text, voice_id = "mbL34QDB5FptPamlgvX5"):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "Content-Type": "application/json",
        "xi-api-key": ELEVENLABS_API_KEY
    }
    payload = {
        "text": text,
        "voice_settings": {
            "stability": 0.8,
            "similarity_boost": 1.0
        }
    }
    
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        # **Save the audio file and play it**
        with open("response.mp3", "wb") as audio_file:
            audio_file.write(response.content)
        
        # **Play the MP3 file**
        
        audio = AudioSegment.from_file("response.mp3", format = "mp3")
        play(audio)
    else:
        st.error(f"Error in ElevenLabs API call: {response.status_code}, {response.text}")
        return None

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

async def websocket_handler(websocket, path):
    while True:
        try:
            user_input = await websocket.recv()
            st.write(f"🔄 WebSocket received: {user_input}")
            if user_input:
                bot_response = get_completion(user_input)
                if bot_response:
                    st.write(f"✅ AI Response Generated: {bot_response}")
                    await websocket.send(bot_response)
        except Exception as e:
            st.error(f"❌ WebSocket error: {e}")
            await websocket.send(f"Error: {e}")

async def start_server():
    server = await websockets.serve(websocket_handler, "0.0.0.0", 8765)
    await server.wait_closed()

def run_websocket_server():
    if not is_port_in_use(8765):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(start_server())

# Ensure WebSocket server runs only once
if "ws_server_started" not in st.session_state:
    st.session_state.ws_server_started = True
    threading.Thread(target=run_websocket_server, daemon=True).start()

#############################################################################################
# Streamlit app

if "messages" not in st.session_state:
    st.session_state['messages'] = []

if "messages" not in st.session_state.keys():
    st.session_state.messages = [{"role": "bot", "content": "How may I assist you today?"}]
else:
    for message in st.session_state.messages: # loop through each item in the 'messages' list stored within 'st.session_state'
        with st.chat_message(message['role']): # creates a chat bubble
            st.markdown(message['content'])

# Initialize memory in session state
if "memories" not in st.session_state:
    st.session_state.memories = {
        "age": None,  # Single value
        "goals": [],  # List
        "preferences": [],  # List
        "motivations": [],  # List
        "conditions": []  # List
    }
    
    
with st.sidebar:
   st.markdown('<h1 style="font-size: 2em;">🦛 Hippopotamus AI </h1>', unsafe_allow_html=True)
   st.text('Ask me anything about health!') 
   
def send_audio(user_input):
    async def async_send_audio():
        try:
            async with websockets.connect("ws://localhost:8765") as websocket:
                st.write(f"Sending to WebSocket: {user_input}")  # Debugging Output
                await websocket.send(user_input)
                bot_response = await websocket.recv()
                st.write(f"Received from WebSocket: {bot_response}")  # Debugging Output
                st.session_state.messages.append({'role': 'user', 'content': user_input})
                st.session_state.messages.append({'role': 'bot', 'content': bot_response})
                audio_file = text_to_speech(bot_response)
                if audio_file:
                    st.audio(audio_file, format="audio/mp3")
        except Exception as e:
            st.error(f"WebSocket error: {e}")
            
# Button to start recording workflow
if st.sidebar.button("Start Recording"):
    user_input = record_audio()
    if user_input:
        send_audio(user_input)

# Button to display memories             
if st.sidebar.button("Show Memories"):
     display_memory()