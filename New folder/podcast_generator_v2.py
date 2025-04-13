#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Advanced Auto Podcast Generator with ElevenLabs SFX & Full Customization
This script converts formatted text scripts into podcasts with voices and sound effects,
all generated through ElevenLabs API with credit tracking and rotation.
"""

import os
import json
import time
import random
import logging
import argparse
import requests
import configparser
from datetime import datetime
from pydub import AudioSegment
from pydub.effects import normalize, speedup
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
ELEVENLABS_SPEECH_API_URL = "https://api.elevenlabs.io/v1/text-to-speech"
ELEVENLABS_SFX_API_URL = "https://api.elevenlabs.io/v1/speech-to-speech"
VOICES_API_URL = "https://api.elevenlabs.io/v1/voices"
USAGE_API_URL = "https://api.elevenlabs.io/v1/user/subscription"
OUTPUT_DIR = "output"
CREDITS_LOG_FILE = "credits_log.json"
CONFIG_FILE = "podcast_config.ini"

# Default configuration
DEFAULT_CONFIG = {
    "General": {
        "output_dir": "output",
        "credits_log_file": "credits_log.json",
        "temp_dir": "temp"
    },
    "Audio": {
        "format": "mp3",
        "bit_rate": "192k",
        "normalize_audio": "True",
        "silence_between_chunks": "200",
        "intro_silence": "500"
    },
    "VoiceSynthesis": {
        "model": "eleven_monolingual_v1",
        "stability": "0.5",
        "similarity_boost": "0.75",
        "style": "0.0",
        "use_speaker_boost": "True"
    },
    "SoundEffects": {
        "default_duration": "3000",
        "volume_reduction": "10",
        "sfx_overlap": "True",
        "sfx_model": "eleven_multilingual_v2"
    },
    "Speakers": {
        "default": "21m00Tcm4TlvDq8ikWAM",  # Rachel
        "bhaskar": "ErXwobaYiN019PkySvjV",  # Antoni
        "mishra": "VR6AewLTigWG4xSOukaG"    # Adam
    },
    "SoundEffectsPrompts": {
        "thunder": "Loud rumbling thunder during a storm",
        "heartbeat": "Deep rhythmic heartbeat sounds",
        "ghat": "Ambient sounds from the Ganges river bank with distant temple bells",
        "water": "Flowing water sound with gentle splashes",
        "temple_bells": "Sacred Indian temple bells ringing",
        "whispers": "Ghostly whispers in a dark room",
        "footsteps": "Heavy footsteps on wooden floor",
        "wind": "Howling wind through narrow streets",
        "crowd": "Busy Indian market crowd noises",
        "door": "Old wooden door creaking open"
    },
    "APIRotation": {
        "retry_failed_calls": "True",
        "max_retries": "3",
        "retry_delay": "2"
    }
}


class ConfigManager:
    """Manages configuration for the podcast generator."""
    
    def __init__(self, config_file=CONFIG_FILE):
        """Initialize with optional path to config file."""
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        
        # Start with default config
        self._set_default_config()
        
        # Load from file if exists
        if os.path.exists(config_file):
            try:
                self.config.read(config_file)
                logger.info(f"Loaded configuration from {config_file}")
            except Exception as e:
                logger.error(f"Error reading config file: {str(e)}")
        else:
            # Create config file with defaults
            self.save_config()
            logger.info(f"Created new config file at {config_file}")
    
    def _set_default_config(self):
        """Set the default configuration."""
        for section, options in DEFAULT_CONFIG.items():
            if not self.config.has_section(section):
                self.config.add_section(section)
            
            for option, value in options.items():
                self.config.set(section, option, value)
    
    def save_config(self):
        """Save configuration to file."""
        try:
            with open(self.config_file, 'w') as f:
                self.config.write(f)
            logger.info(f"Saved configuration to {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving config: {str(e)}")
            return False
    
    def get(self, section, option, fallback=None):
        """Get configuration value."""
        return self.config.get(section, option, fallback=fallback)
    
    def getint(self, section, option, fallback=None):
        """Get configuration value as integer."""
        return self.config.getint(section, option, fallback=fallback)
    
    def getfloat(self, section, option, fallback=None):
        """Get configuration value as float."""
        return self.config.getfloat(section, option, fallback=fallback)
    
    def getboolean(self, section, option, fallback=None):
        """Get configuration value as boolean."""
        return self.config.getboolean(section, option, fallback=fallback)
    
    def set(self, section, option, value):
        """Set configuration value."""
        if not self.config.has_section(section):
            self.config.add_section(section)
        
        self.config.set(section, option, str(value))
    
    def update_from_args(self, args):
        """Update configuration from command line arguments."""
        # Convert args namespace to dictionary
        args_dict = vars(args)
        
        # Map argument names to config sections and options
        arg_mapping = {
            "output_dir": ("General", "output_dir"),
            "format": ("Audio", "format"),
            "normalize": ("Audio", "normalize_audio"),
            "model": ("VoiceSynthesis", "model"),
            "stability": ("VoiceSynthesis", "stability"),
            "similarity_boost": ("VoiceSynthesis", "similarity_boost"),
            # Add more mappings as needed
        }
        
        # Update config with command line arguments
        for arg_name, (section, option) in arg_mapping.items():
            if arg_name in args_dict and args_dict[arg_name] is not None:
                self.set(section, option, str(args_dict[arg_name]))
        
        # Handle custom speaker mappings
        if hasattr(args, "speaker_mapping") and args.speaker_mapping:
            for mapping in args.speaker_mapping:
                try:
                    speaker, voice_id = mapping.split(":")
                    self.set("Speakers", speaker.lower(), voice_id)
                except ValueError:
                    logger.warning(f"Invalid speaker mapping format: {mapping}")
        
        # Handle custom SFX prompts
        if hasattr(args, "sfx_prompt") and args.sfx_prompt:
            for prompt in args.sfx_prompt:
                try:
                    sfx_name, prompt_text = prompt.split(":", 1)
                    self.set("SoundEffectsPrompts", sfx_name.lower(), prompt_text)
                except ValueError:
                    logger.warning(f"Invalid SFX prompt format: {prompt}")
    
    def get_all_speakers(self):
        """Get all configured speakers and their voice IDs."""
        return {k: v for k, v in self.config.items("Speakers")}
    
    def get_all_sfx_prompts(self):
        """Get all configured sound effect prompts."""
        return {k: v for k, v in self.config.items("SoundEffectsPrompts")}


class ApiKeyManager:
    """Manages and rotates between multiple ElevenLabs API keys."""
    
    def __init__(self, api_keys=None, config=None):
        """Initialize with a list of API keys and optional config."""
        self.config = config or ConfigManager()
        
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
        self.credits_log_file = self.config.get("General", "credits_log_file", 
                                               fallback=CREDITS_LOG_FILE)
        self.credits_log = self._load_credits_log()
        self.retry_failed_calls = self.config.getboolean("APIRotation", "retry_failed_calls", 
                                                        fallback=True)
        self.max_retries = self.config.getint("APIRotation", "max_retries", fallback=3)
        self.retry_delay = self.config.getint("APIRotation", "retry_delay", fallback=2)
        
        if not self.api_keys:
            logger.error("No API keys found. Please provide at least one API key.")
            raise ValueError("No API keys provided")
        
        logger.info(f"Initialized with {len(self.api_keys)} API keys")
    
    def _load_credits_log(self):
        """Load credits log from file or create a new one."""
        if os.path.exists(self.credits_log_file):
            try:
                with open(self.credits_log_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                logger.warning(f"Error reading {self.credits_log_file}, creating new log")
        
        # Initialize with empty data for each key
        return {
            key[:8] + '...': {
                "total_credits_used": 0,
                "calls": []
            } for key in self.api_keys
        }
    
    def _save_credits_log(self):
        """Save credits log to file."""
        with open(self.credits_log_file, 'w') as f:
            json.dump(self.credits_log, f, indent=2)
        
    def get_next_api_key(self):
        """Get the next API key in rotation."""
        api_key = self.api_keys[self.current_index]
        # Update index for next call
        self.current_index = (self.current_index + 1) % len(self.api_keys)
        return api_key
    
    def log_credit_usage(self, api_key, character_count, credits_used, operation_type="speech"):
        """Log credit usage for a specific API key."""
        key_id = api_key[:8] + '...'
        if key_id not in self.credits_log:
            self.credits_log[key_id] = {
                "total_credits_used": 0,
                "calls": []
            }
        
        # Update total credits used
        self.credits_log[key_id]["total_credits_used"] += credits_used
        
        # Add call details
        self.credits_log[key_id]["calls"].append({
            "timestamp": datetime.now().isoformat(),
            "operation_type": operation_type,
            "character_count": character_count,
            "credits_used": credits_used
        })
        
        self._save_credits_log()
        logger.info(f"Logged {credits_used} credits for {operation_type} operation using API key {key_id}")
    
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
    
    def make_api_call(self, url, headers, data=None, json_data=None, files=None, method="POST"):
        """Make API call with retry logic and key rotation."""
        current_attempt = 0
        while current_attempt < self.max_retries:
            try:
                # Get current API key
                if "xi-api-key" not in headers:
                    api_key = self.get_next_api_key()
                    headers["xi-api-key"] = api_key
                
                # Make the request
                if method.upper() == "GET":
                    response = requests.get(url, headers=headers, params=data)
                else:  # POST
                    response = requests.post(
                        url, headers=headers, data=data, json=json_data, files=files
                    )
                
                # If successful, return response
                if response.status_code == 200:
                    return response, headers["xi-api-key"]
                
                # If rate limited or credit issue, try a different key
                if response.status_code in [429, 401]:
                    logger.warning(f"API key issue (status {response.status_code}), rotating key")
                    api_key = self.get_next_api_key()
                    headers["xi-api-key"] = api_key
                    current_attempt += 1
                    time.sleep(self.retry_delay)
                    continue
                
                # Other error
                logger.error(f"API call failed: {response.status_code}, {response.text}")
                if not self.retry_failed_calls:
                    return None, headers["xi-api-key"]
                
                current_attempt += 1
                time.sleep(self.retry_delay)
                
            except Exception as e:
                logger.error(f"Error making API call: {str(e)}")
                if not self.retry_failed_calls:
                    return None, headers.get("xi-api-key")
                
                current_attempt += 1
                time.sleep(self.retry_delay)
        
        logger.error(f"Failed to make API call after {self.max_retries} attempts")
        return None, headers.get("xi-api-key")


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
    
    def __init__(self, api_key_manager, config=None):
        """Initialize with API key manager and optional configuration."""
        self.api_key_manager = api_key_manager
        self.config = config or ConfigManager()
        self.voice_mapping = self.config.get_all_speakers()
        
        # Set up temp directory
        self.temp_dir = self.config.get("General", "temp_dir", fallback="temp")
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)
    
    def synthesize(self, text, speaker):
        """Synthesize speech for given text and speaker."""
        if not text.strip():
            logger.warning("Empty text provided for speech synthesis, skipping")
            return None
        
        # Get speaker voice ID
        speaker_key = speaker.lower()
        voice_id = self.voice_mapping.get(
            speaker_key, 
            self.voice_mapping.get("default", "21m00Tcm4TlvDq8ikWAM")  # Default to Rachel
        )
        
        # Set up API request parameters
        url = f"{ELEVENLABS_SPEECH_API_URL}/{voice_id}"
        headers = {
            "Content-Type": "application/json",
            # API key will be added by the api_key_manager
        }
        
        data = {
            "text": text,
            "model_id": self.config.get("VoiceSynthesis", "model"),
            "voice_settings": {
                "stability": self.config.getfloat("VoiceSynthesis", "stability"),
                "similarity_boost": self.config.getfloat("VoiceSynthesis", "similarity_boost"),
                "style": self.config.getfloat("VoiceSynthesis", "style", fallback=0.0),
                "use_speaker_boost": self.config.getboolean("VoiceSynthesis", "use_speaker_boost", fallback=True)
            }
        }
        
        try:
            # Make the API request with rotation and retry
            response, api_key = self.api_key_manager.make_api_call(
                url=url,
                headers=headers,
                json_data=data
            )
            
            if response:
                # Calculate character count and credits used (1 character = 1 credit)
                char_count = len(text)
                credits_used = char_count
                
                # Log credit usage
                self.api_key_manager.log_credit_usage(
                    api_key, char_count, credits_used, "speech_synthesis"
                )
                
                # Create temp file for the audio
                temp_file = os.path.join(
                    self.temp_dir,
                    f"speech_{int(time.time())}_{random.randint(1000, 9999)}.mp3"
                )
                
                with open(temp_file, 'wb') as f:
                    f.write(response.content)
                
                # Load audio with pydub
                audio = AudioSegment.from_mp3(temp_file)
                
                # Clean up temp file
                os.remove(temp_file)
                
                logger.info(f"Successfully synthesized speech for '{speaker}': {len(text)} chars")
                return audio
            else:
                logger.error(f"Failed to synthesize speech for '{speaker}'")
                return None
                
        except Exception as e:
            logger.error(f"Error synthesizing speech: {str(e)}")
            return None


class SoundEffectsGenerator:
    """Generate sound effects using ElevenLabs API."""
    
    def __init__(self, api_key_manager, config=None):
        """Initialize with API key manager and optional configuration."""
        self.api_key_manager = api_key_manager
        self.config = config or ConfigManager()
        self.sfx_prompts = self.config.get_all_sfx_prompts()
        
        # SFX generation parameters
        self.default_duration = self.config.getint("SoundEffects", "default_duration", fallback=3000)
        self.volume_reduction = self.config.getint("SoundEffects", "volume_reduction", fallback=10)
        self.sfx_overlap = self.config.getboolean("SoundEffects", "sfx_overlap", fallback=True)
        self.sfx_model = self.config.get("SoundEffects", "sfx_model", fallback="eleven_multilingual_v2")
        
        # Set up cache and temp directory
        self.sfx_cache = {}
        self.temp_dir = self.config.get("General", "temp_dir", fallback="temp")
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)
    
    def generate_sfx(self, effect_name, duration_ms=None):
        """Generate sound effect using ElevenLabs API."""
        if duration_ms is None:
            duration_ms = self.default_duration
            
        # Check cache first
        cache_key = f"{effect_name}_{duration_ms}"
        if cache_key in self.sfx_cache:
            logger.info(f"Using cached sound effect: {effect_name}")
            return self.sfx_cache[cache_key]
        
        # Get prompt for the effect
        effect_key = effect_name.lower()
        if effect_key not in self.sfx_prompts:
            logger.warning(f"No prompt found for sound effect: {effect_name}")
            return None
        
        prompt = self.sfx_prompts[effect_key]
        logger.info(f"Generating sound effect '{effect_name}' with prompt: {prompt}")
        
        # Use the text-to-speech API with specific settings optimized for SFX
        url = f"{ELEVENLABS_SPEECH_API_URL}/21m00Tcm4TlvDq8ikWAM"  # Using Rachel voice for SFX
        headers = {
            "Content-Type": "application/json",
            # API key will be added by api_key_manager
        }
        
        # Add specific instructions to make it clear we want sound effects
        enhanced_prompt = f"[SOUND EFFECT ONLY, NO SPEECH]: {prompt}"
        
        data = {
            "text": enhanced_prompt,
            "model_id": self.sfx_model,
            "voice_settings": {
                "stability": 0.1,  # Very low stability for more variety in sound effects
                "similarity_boost": 0.35,  # Lower similarity for more creative sounds
                "style": 1.0,  # Max style for more expressive SFX
                "use_speaker_boost": False  # Disable speaker boost for SFX
            }
        }
        
        try:
            # Make the API request with rotation and retry
            response, api_key = self.api_key_manager.make_api_call(
                url=url,
                headers=headers,
                json_data=data
            )
            
            if response:
                # Calculate credit usage
                char_count = len(enhanced_prompt)
                credits_used = char_count
                
                # Log credit usage
                self.api_key_manager.log_credit_usage(
                    api_key, char_count, credits_used, "sfx_generation"
                )
                
                # Create temp file for the audio
                temp_file = os.path.join(
                    self.temp_dir,
                    f"sfx_{int(time.time())}_{random.randint(1000, 9999)}.mp3"
                )
                
                with open(temp_file, 'wb') as f:
                    f.write(response.content)
                
                # Load and process the sound effect
                sfx = AudioSegment.from_mp3(temp_file)
                
                # Apply volume reduction
                sfx = sfx - self.volume_reduction
                
                # Clean up temp file
                os.remove(temp_file)
                
                # Adjust duration if needed
                if len(sfx) > duration_ms:
                    sfx = sfx[:duration_ms]
                elif len(sfx) < duration_ms:
                    # For short effects, loop them for natural repetition
                    repetitions = duration_ms // len(sfx) + 1
                    sfx = sfx * repetitions
                    sfx = sfx[:duration_ms]
                
                # Add to cache
                self.sfx_cache[cache_key] = sfx
                
                logger.info(f"Successfully generated sound effect: {effect_name}")
                return sfx
            else:
                logger.error(f"Failed to generate sound effect: {effect_name}")
                return None
        
        except Exception as e:
            logger.error(f"Error generating sound effect: {str(e)}")
            return None


class PodcastGenerator:
    """Generate podcasts from parsed scripts using speech synthesis and sound effects."""
    
    def __init__(self, api_key_manager, config=None):
        """Initialize the podcast generator."""
        self.config = config or ConfigManager()
        self.api_key_manager = api_key_manager
        self.speech_synthesizer = SpeechSynthesizer(api_key_manager, self.config)
        self.sfx_generator = SoundEffectsGenerator(api_key_manager, self.config)
        
        # Audio settings
        self.silence_between_chunks = self.config.getint("Audio", "silence_between_chunks", fallback=200)
        self.intro_silence = self.config.getint("Audio", "intro_silence", fallback=500)
        self.normalize_audio = self.config.getboolean("Audio", "normalize_audio", fallback=True)
        self.audio_format = self.config.get("Audio", "format", fallback="mp3")
        self.bit_rate = self.config.get("Audio", "bit_rate", fallback="192k")
        
        # Create output directory if it doesn't exist
        self.output_dir = self.config.get("General", "output_dir", fallback="output")
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            logger.info(f"Created directory: {self.output_dir}")
    
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
            output_file = os.path.join(self.output_dir, f"{script_name}_{timestamp}.{self.audio_format}")
        
        # Process each chunk
        podcast = AudioSegment.silent(duration=self.intro_silence)
        
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
                # Generate sound effect
                sfx_clip = self.sfx_generator.generate_sfx(chunk["effect"])
                
                if sfx_clip:
                    # Determine how to add the sound effect
                    if self.config.getboolean("SoundEffects", "sfx_overlap", fallback=True) and len(podcast) > 2000:
                        # Overlap with previous audio
                        overlap_point = len(podcast) - 2000
                        
                        # Create a new audio segment with original audio
                        new_segment = podcast[:overlap_point]
                        
                        # Create the overlapped section
                        overlap_segment = podcast[overlap_point:]
                        
                        # Ensure sfx_clip is not longer than the section to overlay
                        if len(sfx_clip) > len(overlap_segment):
                            sfx_clip = sfx_clip[:len(overlap_segment)]
                        
                        # Overlay the sound effect
                        overlapped = overlap_segment.overlay(sfx_clip)
                        
                        # Combine segments
                        podcast = new_segment + overlapped
                    else:
                        # Just append the sound effect
                        podcast += sfx_clip
            
            # Add a short silence between chunks
            podcast += AudioSegment.silent(duration=self.silence_between_chunks)
        
        # Normalize audio levels if configured
        if self.normalize_audio:
            podcast = normalize(podcast)
        
        # Export the final podcast
        try:
            podcast.export(
                output_file, 
                format=self.audio_format, 
                bitrate=self.bit_rate
            )
            logger.info(f"Podcast saved to {output_file}")
            return True
        except Exception as e:
            logger.error(f"Error exporting podcast: {str(e)}")
            return False


def main():
    """Main function to run the podcast generator."""
    parser = argparse.ArgumentParser(description="Advanced Auto Podcast Generator with ElevenLabs SFX")
    
    # Basic arguments
    parser.add_argument("-s", "--script", required=True, help="Path to the script file")
    parser.add_argument("-o", "--output", help="Path to save the output file")
    parser.add_argument("-k", "--keys", help="Comma-separated list of ElevenLabs API keys")
    parser.add_argument("-c", "--config", help="Path to custom config file")
    
    # Voice synthesis customization
    parser.add_argument("--model", help="ElevenLabs model ID for voice synthesis")
    parser.add_argument("--stability", type=float, help="Voice stability (0.0-1.0)")
    parser.add_argument("--similarity-boost", type=float, help="Voice similarity boost (0.0-1.0)")
    
    # SFX customization
    parser.add_argument("--sfx-model", help="Model ID for sound effects generation")
    parser.add_argument("--sfx-duration", type=int, help="Default duration for sound effects in milliseconds")
    
    # Speaker and SFX mappings
    parser.add_argument("--speaker-mapping", action="append", 
                        help="Custom speaker to voice ID mapping (format: 'Speaker:VoiceID')")
    parser.add_argument("--sfx-prompt", action="append", 
                        help="Custom sound effect prompt (format: 'effect:prompt text')")
    
    # Output customization
    parser.add_argument("--format", choices=["mp3", "wav", "ogg"], help="Output audio format")
    parser.add_argument("--bit-rate", help="Output bit rate (e.g., '192k')")
    parser.add_argument("--normalize", type=bool, help="Normalize audio levels")
    
    args = parser.parse_args()
    
    try:
        # Initialize configuration
        config = ConfigManager(args.config if args.config else CONFIG_FILE)
        
        # Update config with command line arguments
        config.update_from_args(args)
        
        # Save updated config
        config.save_config()
        
        # Initialize API key manager
        api_keys = args.keys.split(",") if args.keys else None
        api_key_manager = ApiKeyManager(api_keys, config)
        
        # Initialize podcast generator
        podcast_generator = PodcastGenerator(api_key_manager, config)
        
        # Generate podcast
        success = podcast_generator.generate(args.script, args.output)
        
        if success:
            logger.info("Podcast generation completed successfully!")
        else:
            logger.error("Failed to generate podcast")
            return 1
            
    except Exception as e:
        logger.error(f"Error in main function: {str(e)}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
