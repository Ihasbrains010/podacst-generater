#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Auto Podcast Generator with Credit Tracking
This script converts formatted text scripts into podcasts with voices and sound effects.
It rotates between multiple ElevenLabs API keys and tracks credit usage.
"""

import os
import json
import time
import logging
import requests
import random
from datetime import datetime
from pydub import AudioSegment
from pydub.effects import normalize
from dotenv import load_dotenv
from tqdm import tqdm
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("podcast_generator.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Constants
ELEVENLABS_API_URL = "https://api.elevenlabs.io/v1/text-to-speech"
VOICES_API_URL = "https://api.elevenlabs.io/v1/voices"
USAGE_API_URL = "https://api.elevenlabs.io/v1/user/subscription"
OUTPUT_DIR = "output"
SFX_DIR = "sfx"
CREDITS_LOG_FILE = "credits_log.json"

# Voice IDs mapping (can be customized)
DEFAULT_VOICE_MAPPING = {
    "Bhaskar": "ErXwobaYiN019PkySvjV",  # Antoni (deep authoritative male)
    "Mishra": "VR6AewLTigWG4xSOukaG",   # Adam (mature male)
    "Default": "21m00Tcm4TlvDq8ikWAM"   # Rachel (default female)
}

class ApiKeyManager:
    """Manages and rotates between multiple ElevenLabs API keys."""
    
    def __init__(self, api_keys=None):
        """Initialize with a list of API keys."""
        if api_keys:
            self.api_keys = api_keys
        else:
            # Try to get API keys from environment variables
            keys_str = os.getenv("ELEVENLABS_API_KEYS")
            if keys_str:
                self.api_keys = [key.strip() for key in keys_str.split(",")]
            else:
                self.api_keys = []
                
        self.current_index = 0
        self.credits_log = self._load_credits_log()
        
        if not self.api_keys:
            logger.error("No API keys found. Please provide at least one API key.")
            raise ValueError("No API keys provided")
        
        logger.info(f"Initialized with {len(self.api_keys)} API keys")
    
    def _load_credits_log(self):
        """Load credits log from file or create a new one."""
        if os.path.exists(CREDITS_LOG_FILE):
            try:
                with open(CREDITS_LOG_FILE, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                logger.warning(f"Error reading {CREDITS_LOG_FILE}, creating new log")
        
        # Initialize with empty data for each key
        return {key[:8] + '...': [] for key in self.api_keys}
    
    def _save_credits_log(self):
        """Save credits log to file."""
        with open(CREDITS_LOG_FILE, 'w') as f:
            json.dump(self.credits_log, f, indent=2)
        
    def get_next_api_key(self):
        """Get the next API key in rotation."""
        api_key = self.api_keys[self.current_index]
        # Update index for next call
        self.current_index = (self.current_index + 1) % len(self.api_keys)
        return api_key
    
    def log_credit_usage(self, api_key, character_count, credits_used):
        """Log credit usage for a specific API key."""
        key_id = api_key[:8] + '...'
        if key_id not in self.credits_log:
            self.credits_log[key_id] = []
        
        self.credits_log[key_id].append({
            "timestamp": datetime.now().isoformat(),
            "character_count": character_count,
            "credits_used": credits_used
        })
        
        self._save_credits_log()
        logger.info(f"Logged {credits_used} credits used for API key {key_id}")
    
    def get_remaining_credits(self, api_key):
        """Get remaining credits for a specific API key."""
        headers = {"xi-api-key": api_key}
        
        try:
            response = requests.get(USAGE_API_URL, headers=headers)
            if response.status_code == 200:
                data = response.json()
                return data.get("character_count", 0), data.get("character_limit", 0)
            else:
                logger.warning(f"Failed to get usage info: {response.status_code}, {response.text}")
                return None, None
        except Exception as e:
            logger.error(f"Error getting remaining credits: {str(e)}")
            return None, None


class ScriptParser:
    """Parse the input script into chunks of dialogue and sound effects."""
    
    def __init__(self, script_path):
        """Initialize with the path to the script file."""
        self.script_path = script_path
        
    def parse(self):
        """Parse the script into a list of chunks (dialogue or SFX)."""
        chunks = []
        current_speaker = "Default"
        
        try:
            with open(self.script_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            buffer = []
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Check for speaker tag
                speaker_match = re.match(r'\[SPEAKER:\s*([^\]]+)\]', line)
                if speaker_match:
                    # If there's text in buffer, add it as a chunk with previous speaker
                    if buffer:
                        chunks.append({
                            "type": "dialogue",
                            "speaker": current_speaker,
                            "text": " ".join(buffer)
                        })
                        buffer = []
                    
                    current_speaker = speaker_match.group(1).strip()
                    continue
                
                # Check for SFX tag
                sfx_match = re.match(r'\[SFX:\s*([^\]]+)\]', line)
                if sfx_match:
                    # If there's text in buffer, add it as a chunk
                    if buffer:
                        chunks.append({
                            "type": "dialogue",
                            "speaker": current_speaker,
                            "text": " ".join(buffer)
                        })
                        buffer = []
                    
                    # Add the SFX as a chunk
                    chunks.append({
                        "type": "sfx",
                        "effect": sfx_match.group(1).strip()
                    })
                    continue
                
                # If it's a regular line, add to buffer
                buffer.append(line)
            
            # Add any remaining text in buffer
            if buffer:
                chunks.append({
                    "type": "dialogue",
                    "speaker": current_speaker,
                    "text": " ".join(buffer)
                })
            
            return chunks
        
        except Exception as e:
            logger.error(f"Error parsing script: {str(e)}")
            raise


class SpeechSynthesizer:
    """Synthesize speech using ElevenLabs API."""
    
    def __init__(self, api_key_manager, voice_mapping=None):
        """Initialize with API key manager and optional voice mapping."""
        self.api_key_manager = api_key_manager
        self.voice_mapping = voice_mapping or DEFAULT_VOICE_MAPPING
    
    def synthesize(self, text, speaker):
        """Synthesize speech for given text and speaker."""
        if not text.strip():
            logger.warning("Empty text provided for synthesis, skipping")
            return None
        
        api_key = self.api_key_manager.get_next_api_key()
        voice_id = self.voice_mapping.get(speaker, self.voice_mapping["Default"])
        
        # Set up the API request
        headers = {
            "xi-api-key": api_key,
            "Content-Type": "application/json"
        }
        
        data = {
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75
            }
        }
        
        endpoint = f"{ELEVENLABS_API_URL}/{voice_id}"
        
        try:
            # Make the API request
            logger.info(f"Synthesizing speech for {speaker}: '{text[:50]}...'")
            response = requests.post(endpoint, json=data, headers=headers)
            
            if response.status_code == 200:
                # Calculate character count and credits used (1 character = 1 credit)
                char_count = len(text)
                credits_used = char_count
                
                # Log credit usage
                self.api_key_manager.log_credit_usage(api_key, char_count, credits_used)
                
                # Create temp file for the audio
                temp_file = f"temp_{int(time.time())}_{random.randint(1000, 9999)}.mp3"
                
                with open(temp_file, 'wb') as f:
                    f.write(response.content)
                
                # Load audio with pydub
                audio = AudioSegment.from_mp3(temp_file)
                
                # Clean up temp file
                os.remove(temp_file)
                
                return audio
            else:
                logger.error(f"API request failed: {response.status_code}, {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error synthesizing speech: {str(e)}")
            return None


class SoundEffectsManager:
    """Manage sound effects for the podcast."""
    
    def __init__(self, sfx_dir=SFX_DIR):
        """Initialize with path to sound effects directory."""
        self.sfx_dir = sfx_dir
        
        # Create SFX directory if it doesn't exist
        if not os.path.exists(self.sfx_dir):
            os.makedirs(self.sfx_dir)
            logger.info(f"Created directory: {self.sfx_dir}")
        
        # Cache to avoid loading the same sound multiple times
        self.sfx_cache = {}
    
    def get_sfx_clip(self, effect_name, duration_ms=3000):
        """Get sound effect clip with specified name and optional duration."""
        # Check cache first
        if effect_name in self.sfx_cache:
            clip = self.sfx_cache[effect_name]
        else:
            # Look for file with matching name in SFX directory
            effect_files = [
                f for f in os.listdir(self.sfx_dir) 
                if f.lower().startswith(effect_name.lower()) and 
                f.lower().endswith(('.mp3', '.wav'))
            ]
            
            if not effect_files:
                logger.warning(f"Sound effect '{effect_name}' not found")
                return None
            
            # Load the sound effect
            effect_path = os.path.join(self.sfx_dir, effect_files[0])
            try:
                clip = AudioSegment.from_file(effect_path)
                self.sfx_cache[effect_name] = clip
            except Exception as e:
                logger.error(f"Error loading sound effect '{effect_name}': {str(e)}")
                return None
        
        # Adjust volume and duration
        clip = clip - 10  # Reduce volume by 10dB for background effects
        
        # If effect is longer than requested duration, trim it
        if duration_ms and len(clip) > duration_ms:
            clip = clip[:duration_ms]
        
        # If effect is shorter than requested duration, loop it
        if duration_ms and len(clip) < duration_ms:
            repetitions = duration_ms // len(clip) + 1
            clip = clip * repetitions
            clip = clip[:duration_ms]
        
        return clip


class PodcastGenerator:
    """Generate podcasts from parsed scripts using speech synthesis and sound effects."""
    
    def __init__(self, api_key_manager, voice_mapping=None):
        """Initialize the podcast generator."""
        self.api_key_manager = api_key_manager
        self.speech_synthesizer = SpeechSynthesizer(api_key_manager, voice_mapping)
        self.sfx_manager = SoundEffectsManager()
        
        # Create output directory if it doesn't exist
        if not os.path.exists(OUTPUT_DIR):
            os.makedirs(OUTPUT_DIR)
            logger.info(f"Created directory: {OUTPUT_DIR}")
    
    def generate(self, script_path, output_file=None):
        """Generate a podcast from the given script."""
        # Parse the script
        parser = ScriptParser(script_path)
        chunks = parser.parse()
        
        if not chunks:
            logger.error("No valid content in script")
            return False
        
        # Generate default output filename if not provided
        if not output_file:
            script_name = os.path.basename(script_path).split('.')[0]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = os.path.join(OUTPUT_DIR, f"{script_name}_{timestamp}.mp3")
        
        # Process each chunk
        podcast = AudioSegment.silent(duration=500)  # Start with 0.5s silence
        
        for i, chunk in enumerate(tqdm(chunks, desc="Generating podcast")):
            if chunk["type"] == "dialogue":
                # Synthesize speech
                audio = self.speech_synthesizer.synthesize(
                    chunk["text"], 
                    chunk["speaker"]
                )
                
                if audio:
                    # Add a small silence before the dialogue
                    podcast += AudioSegment.silent(duration=300)
                    podcast += audio
                
            elif chunk["type"] == "sfx":
                # Get sound effect
                sfx_clip = self.sfx_manager.get_sfx_clip(chunk["effect"])
                
                if sfx_clip:
                    # Overlap with previous audio or add to the end
                    if len(podcast) > 2000:  # If podcast already has content
                        # Get last 2 seconds of current podcast
                        overlay_point = len(podcast) - 2000
                        
                        # Create a new audio segment with original audio
                        new_segment = podcast[:overlay_point]
                        
                        # Create the overlapped section
                        overlap_segment = podcast[overlay_point:]
                        
                        # Ensure sfx_clip is not longer than the section to overlay
                        if len(sfx_clip) > len(overlap_segment):
                            sfx_clip = sfx_clip[:len(overlap_segment)]
                        
                        # Overlay the sound effect
                        overlapped = overlap_segment.overlay(sfx_clip)
                        
                        # Combine segments
                        podcast = new_segment + overlapped
                    else:
                        podcast += sfx_clip
            
            # Add a short silence between chunks
            podcast += AudioSegment.silent(duration=200)
        
        # Normalize audio levels
        podcast = normalize(podcast)
        
        # Export the final podcast
        try:
            podcast.export(output_file, format="mp3")
            logger.info(f"Podcast saved to {output_file}")
            return True
        except Exception as e:
            logger.error(f"Error exporting podcast: {str(e)}")
            return False


def main():
    """Main function to run the podcast generator."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Auto Podcast Generator with Credit Tracking")
    parser.add_argument("-s", "--script", required=True, help="Path to the script file")
    parser.add_argument("-o", "--output", help="Path to save the output file")
    parser.add_argument("-k", "--keys", help="Comma-separated list of ElevenLabs API keys")
    args = parser.parse_args()
    
    try:
        # Initialize API key manager
        api_keys = args.keys.split(",") if args.keys else None
        api_key_manager = ApiKeyManager(api_keys)
        
        # Initialize podcast generator
        podcast_generator = PodcastGenerator(api_key_manager)
        
        # Generate podcast
        success = podcast_generator.generate(args.script, args.output)
        
        if success:
            logger.info("Podcast generation completed successfully!")
        else:
            logger.error("Failed to generate podcast")
            
    except Exception as e:
        logger.error(f"Error in main function: {str(e)}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
