import json
import os
import random
import subprocess
from pydub import AudioSegment
from elevenlabs import save
from elevenlabs.client import ElevenLabs
#from pyrubberband import time_stretch
# Define the list of voices, ambiance MP3s, and global ambiance MP3 (provided by you)
voices = {
    #"Julie": "vVypMgcNd4WcVJdE5KAS",
    "Julie": "AcGHtn5NK8C0VkbCsIjm",
   # "Dave": "0aj9guxInFB1t3JOl4J6",
   "Dave": "Ybqj6CIlqb6M85s9Bl4n",
}
pans = {
    "Julie": -0.25,
    "Dave": 0.25,
}

ambiance_mp3s = ["ambiance1.mp3", "ambiance2.mp3", "ambiance3.mp3"]
global_ambiance_mp3 = "global_ambiance.mp3"

# Initialize the ElevenLabs client with your API key
client = ElevenLabs(api_key=os.environ["ELEVENLABS_API_KEY"])


def find_segment_by_utterance(utterance, voice, segments_cache):
    # Iterate over the segments cache and find the segment with the matching utterance
    for segment_file, segment_data in segments_cache.items():
        if segment_data["utterance"] == utterance and segment_data["voice"] == voice:
            return segment_file

    # If no matching segment is found, return None
    return None

def find_largest_segment_number(segments_dir):
    # Get a list of all files in the segments directory
    files = os.listdir(segments_dir)

    # Filter the list to include only MP3 files
    mp3_files = [f for f in files if f.endswith(".mp3")]

    # Extract the numbers from the MP3 filenames
    numbers = [int(f.split(".")[0]) for f in mp3_files if f.split(".")[0].isdigit()]

    # Return the largest number, or None if no MP3 files are found
    return max(numbers) if numbers else None


def rubberband(audio_segment, speed_factor):
    # Save the input audio segment to a temporary file
    input_file = "temp_input.wav"
    audio_segment.export(input_file, format="wav")

    # Generate a temporary output file path
    output_file = "temp_output.wav"

    try:
        subprocess.run([
            "rubberband",
            "--tempo",
            str(speed_factor),
            "-3",
            input_file,
            output_file
        ], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running Rubber Band: {e}")
        return None

    # Load the stretched audio file into a Pydub audio segment
    stretched_audio = AudioSegment.from_wav(output_file)

    # Clean up the temporary files
    os.remove(input_file)
    os.remove(output_file)

    return stretched_audio

# Function to call the ElevenLabs API for text-to-speech
def call_text_to_speech(text, voice, output_file):
    print("Generating audio for:", text)
    audio = client.generate(
        text=text,
        voice=voice,
        model="eleven_multilingual_v2"
    )
    save(audio, output_file)

# Function to add echo to an audio segment
def add_echo(audio, gain_db):
    # this needs more thought
    #echo = audio + AudioSegment.silent(duration=100)
    #echo = echo.overlay(audio, position=100, gain_db=gain_db)
    #echo = audio.overlay(audio, position=100, gain_db=gain_db)
    return audio
# Function to vary the volume randomly and subtly
def vary_volume(audio, min_db, max_db):
    volume_changes = []
    chunk_size = 100  # Adjust the chunk size as needed
    for i in range(0, len(audio), chunk_size):
        volume_change = random.uniform(min_db, max_db)
        volume_changes.append(volume_change)
    
    new_audio = AudioSegment.empty()
    for i, chunk in enumerate(audio[::chunk_size]):
        new_audio += chunk + volume_changes[i]
    
    return new_audio

# Function to handle breathing sounds
def breathing():
    breathing_sounds = os.listdir("sounds/breathing")
    if breathing_sounds:
        return os.path.join("sounds/breathing", random.choice(breathing_sounds))
    return None

# Function to handle break sounds
def handle_break(n):
    break_sounds = os.listdir("sounds/break")
    if break_sounds:
        return os.path.join("sounds/break", random.choice(break_sounds))
    return None

# Function to parse the script into segments
def parse_script(script):
    segments = []
    for line in script.split("\n"):
        if line.strip() == "[break]":
            segments.append({"type": "break"})
        elif ":" in line:
            speaker, text = line.split(":", 1)
            segments.append({"type": "utterance", "speaker": speaker.strip(), "text": text.strip()})
    return segments

# Function to generate speech segments and update the cache
def generate_speech_segments(segments, segments_cache):
    largest_current_segment = find_largest_segment_number("segments")
    print("Largest current segment:", largest_current_segment)
    for i, segment in enumerate(segments):
        n = i + largest_current_segment + 1 if largest_current_segment else i
        if segment["type"] == "utterance":
            speaker = segment["speaker"]
            text = segment["text"]
            if speaker not in voices:
                print("Error: Speaker not found in voices dictionary", speaker)
                continue
            voice = voices[segment["speaker"]]
            output_file = f"segments/{n}.mp3"
            # This is broken. The cache should persist from run to run. 
            # It should look up already-spoken segments and not re-generate them.
            if find_segment_by_utterance(text, voice, segments_cache) is None:
                call_text_to_speech(text, voice, output_file)
                segments_cache[output_file] = {"voice": voice, "utterance": text}

                with open("segments/segments.json", "w") as file:
                    json.dump(segments_cache, file)

# Function to mix the audio segments
def mix_audio_segments(segments, segments_cache):
    mixed_audio = AudioSegment.empty()
    break_count = 0

    # Load the global ambiance audio
    global_ambiance_audio = AudioSegment.from_mp3(global_ambiance_mp3)

    for segment in segments:
        if segment["type"] == "utterance":
            print("Mixing audio for:", segment["text"])
            output_file = find_segment_by_utterance(segment["text"], voices[segment["speaker"]], segments_cache)
            print("Output file:", output_file)
            speech_audio = AudioSegment.from_mp3(output_file)
            #speech_audio = speech_audio.speedup(playback_speed=1.2)  # Adjust the speed here
            # Speedup using pydub with adjustments to minimize clipping
            speed_factor = 1.2  # Adjust the speed factor as needed
            #speech_audio = speech_audio.speedup(playback_speed=speed_factor, chunk_size=50, crossfade=25)

            # Normalize the audio to reduce clipping
            speech_audio = speech_audio.normalize()
            # High-quality speedup using pyrubberband
            # speed_factor = 1.2  # Adjust the speed factor as needed
            # speech_samples = speech_audio.get_array_of_samples()
            # stretched_samples = time_stretch(speech_samples, speech_audio.frame_rate, speed_factor)
            # speech_audio = AudioSegment(
            #     data=stretched_samples.tobytes(),
            #     sample_width=speech_audio.sample_width,
            #     frame_rate=speech_audio.frame_rate,
            #     channels=speech_audio.channels
            # )
            speech_audio = rubberband(speech_audio, 1.1)
            speech_audio = add_echo(speech_audio, gain_db=-3)  # Adjust the echo level here
            speech_audio = vary_volume(speech_audio, min_db=-3, max_db=3)  # Adjust the volume variation here
            speech_audio = speech_audio.pan(pans[segment["speaker"]])
            # per speaker ambiance 
            #ambiance_audio = AudioSegment.from_mp3(random.choice(ambiance_mp3s))
            #ambiance_audio = ambiance_audio[:len(speech_audio)]
            #ambiance_audio = ambiance_audio - 20  # Adjust the ambiance volume here
            #speech_audio = speech_audio.overlay(ambiance_audio)

            # Mix the speech audio with the global ambiance audio
            remaining_duration = len(speech_audio)
            global_ambiance_chunk = AudioSegment.empty()
            while remaining_duration > 0:
                if len(global_ambiance_audio) >= remaining_duration:
                    print("Adding global ambiance chunk1")
                    global_ambiance_chunk += global_ambiance_audio[:remaining_duration]
                    remaining_duration = 0
                else:
                    print("Adding global ambiance chunk2")
                    global_ambiance_chunk += global_ambiance_audio
                    remaining_duration -= len(global_ambiance_audio)
                    global_ambiance_audio = AudioSegment.from_mp3(global_ambiance_mp3)

            global_ambiance_chunk = global_ambiance_chunk  # Adjust the global ambiance volume here
            speech_audio = speech_audio.overlay(global_ambiance_chunk)


            breathing_audio_file = breathing()
            if breathing_audio_file:
                breathing_audio = AudioSegment.from_mp3(breathing_audio_file)
                mixed_audio += breathing_audio

            mixed_audio += speech_audio
        elif segment["type"] == "break":
            break_audio_file = handle_break(break_count)
            if break_audio_file:
                break_audio = AudioSegment.from_mp3(break_audio_file)
                mixed_audio += break_audio
            break_count += 1

    return mixed_audio

# Function to add intro and outro music
def add_intro_outro(mixed_audio):
    intro_audio = AudioSegment.from_mp3("intro.mp3")
    outro_audio = AudioSegment.from_mp3("outro.mp3")

    intro_audio = intro_audio + AudioSegment.silent(duration=500)
    mixed_audio = intro_audio.append(mixed_audio, crossfade=100)
    mixed_audio = mixed_audio + AudioSegment.silent(duration=500)
    mixed_audio = mixed_audio.append(outro_audio, crossfade=1000)

    return mixed_audio

# Main function to generate the podcast
def generate_podcast():
    # Read the script file
    with open("script.txt", "r") as file:
        script = file.read()

    # Parse the script into segments
    segments = parse_script(script)

    # Load the segments cache if it exists
    if os.path.exists("segments/segments.json"):
        with open("segments/segments.json", "r") as file:
            segments_cache = json.load(file)
    else:
        segments_cache = {}

    # Generate speech segments and update the cache
    generate_speech_segments(segments, segments_cache)

    # Mix the audio segments
    mixed_audio = mix_audio_segments(segments, segments_cache)

    # Add intro and outro music
    final_audio = add_intro_outro(mixed_audio)

    # Export the final audio
    final_audio.export("output.mp3", format="mp3")

# Run the podcast generation
generate_podcast()

