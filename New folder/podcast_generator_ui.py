#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Simple GUI for the Auto Podcast Generator
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
import threading
import configparser
import subprocess
import webbrowser
from pathlib import Path

# Set the current directory as the base path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "podcast_config.ini")


class PodcastGeneratorUI:
    """Simple GUI for the Auto Podcast Generator."""
    
    def __init__(self, root):
        """Initialize the UI."""
        self.root = root
        self.root.title("Auto Podcast Generator")
        self.root.geometry("800x700")
        self.root.resizable(True, True)
        
        # Variables
        self.script_path_var = tk.StringVar()
        self.output_path_var = tk.StringVar()
        self.api_keys_var = tk.StringVar()
        self.config_path_var = tk.StringVar(value=CONFIG_FILE)
        
        # Set up the UI
        self.create_widgets()
        self.load_config()
    
    def create_widgets(self):
        """Create UI widgets."""
        # Create main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Style
        style = ttk.Style()
        style.configure("TLabel", font=("Arial", 11))
        style.configure("TButton", font=("Arial", 11))
        style.configure("TEntry", font=("Arial", 11))
        style.configure("Header.TLabel", font=("Arial", 14, "bold"))
        style.configure("Title.TLabel", font=("Arial", 16, "bold"))
        
        # Title
        title_label = ttk.Label(
            main_frame, 
            text="Auto Podcast Generator with ElevenLabs SFX",
            style="Title.TLabel"
        )
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # File Selection Section
        file_frame = ttk.LabelFrame(main_frame, text="Files", padding=10)
        file_frame.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(0, 10))
        
        # Script file
        ttk.Label(file_frame, text="Script File:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        ttk.Entry(file_frame, textvariable=self.script_path_var, width=50).grid(
            row=0, column=1, sticky="ew", padx=5, pady=5
        )
        ttk.Button(file_frame, text="Browse...", command=self.browse_script).grid(
            row=0, column=2, sticky="e", padx=5, pady=5
        )
        
        # Output file
        ttk.Label(file_frame, text="Output File:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        ttk.Entry(file_frame, textvariable=self.output_path_var, width=50).grid(
            row=1, column=1, sticky="ew", padx=5, pady=5
        )
        ttk.Button(file_frame, text="Browse...", command=self.browse_output).grid(
            row=1, column=2, sticky="e", padx=5, pady=5
        )
        
        # API Keys Section
        api_frame = ttk.LabelFrame(main_frame, text="API Keys (comma-separated)", padding=10)
        api_frame.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(0, 10))
        
        # API keys
        api_entry = ttk.Entry(api_frame, textvariable=self.api_keys_var, width=70)
        api_entry.grid(row=0, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        
        # Voices Section - Simplified Direct Link Approach
        voices_frame = ttk.LabelFrame(main_frame, text="Voice Settings", padding=10)
        voices_frame.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(0, 10))
        
        # Default voice (main character)
        ttk.Label(voices_frame, text="Bhaskar Voice ID:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.bhaskar_voice_var = tk.StringVar(value="ErXwobaYiN019PkySvjV")
        ttk.Entry(voices_frame, textvariable=self.bhaskar_voice_var, width=40).grid(
            row=0, column=1, sticky="ew", padx=5, pady=5
        )
        ttk.Button(voices_frame, text="Browse Voices", command=lambda: self.open_elevenlabs_voices()).grid(
            row=0, column=2, sticky="e", padx=5, pady=5
        )
        
        # Secondary voice
        ttk.Label(voices_frame, text="Mishra Voice ID:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.mishra_voice_var = tk.StringVar(value="VR6AewLTigWG4xSOukaG")
        ttk.Entry(voices_frame, textvariable=self.mishra_voice_var, width=40).grid(
            row=1, column=1, sticky="ew", padx=5, pady=5
        )
        
        # Default for other characters
        ttk.Label(voices_frame, text="Default Voice ID:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.default_voice_var = tk.StringVar(value="21m00Tcm4TlvDq8ikWAM")
        ttk.Entry(voices_frame, textvariable=self.default_voice_var, width=40).grid(
            row=2, column=1, sticky="ew", padx=5, pady=5
        )
        
        # Voice model
        ttk.Label(voices_frame, text="Voice Model:").grid(row=3, column=0, sticky="w", padx=5, pady=5)
        self.voice_model_var = tk.StringVar(value="eleven_monolingual_v1")
        ttk.Combobox(voices_frame, textvariable=self.voice_model_var, 
                     values=["eleven_monolingual_v1", "eleven_multilingual_v2"]).grid(
            row=3, column=1, sticky="ew", padx=5, pady=5
        )
        
        # Help text
        help_text = "Paste voice IDs directly from ElevenLabs. Click 'Browse Voices' to find voice IDs."
        ttk.Label(voices_frame, text=help_text, font=("Arial", 9, "italic")).grid(
            row=4, column=0, columnspan=3, sticky="w", padx=5, pady=(5, 0)
        )
        
        # Sound Effects Section
        sfx_frame = ttk.LabelFrame(main_frame, text="Sound Effects", padding=10)
        sfx_frame.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(0, 10))
        
        # SFX Prompts
        ttk.Label(sfx_frame, text="Sound Effect Prompts:").grid(
            row=0, column=0, sticky="w", padx=5, pady=(5, 5)
        )
        
        # Add some help text
        sfx_help = "Format: effect_name:detailed description of the sound (one per line)"
        ttk.Label(sfx_frame, text=sfx_help, font=("Arial", 9, "italic")).grid(
            row=1, column=0, columnspan=3, sticky="w", padx=5, pady=(0, 5)
        )
        
        self.sfx_prompts_text = scrolledtext.ScrolledText(sfx_frame, width=70, height=8)
        self.sfx_prompts_text.grid(row=2, column=0, columnspan=3, padx=5, pady=5, sticky="ew")
        
        # Add default prompts button
        ttk.Button(sfx_frame, text="Load Default Prompts", command=self.load_default_sfx_prompts).grid(
            row=3, column=0, sticky="w", padx=5, pady=5
        )
        
        # Console output
        ttk.Label(main_frame, text="Console Output:").grid(
            row=5, column=0, sticky="w", padx=5, pady=(10, 5)
        )
        
        self.console_output = scrolledtext.ScrolledText(main_frame, width=80, height=10)
        self.console_output.grid(row=6, column=0, columnspan=3, padx=5, pady=5, sticky="nsew")
        self.console_output.config(state=tk.DISABLED)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=7, column=0, columnspan=3, pady=10)
        
        ttk.Button(button_frame, text="Generate Podcast", command=self.generate_podcast, width=20).grid(
            row=0, column=0, padx=5
        )
        
        ttk.Button(button_frame, text="Save Settings", command=self.save_config, width=15).grid(
            row=0, column=1, padx=5
        )
        
        # Configure grid weights
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(6, weight=1)
        
        for frame in [file_frame, api_frame, voices_frame, sfx_frame]:
            frame.columnconfigure(1, weight=1)
    
    def open_elevenlabs_voices(self):
        """Open ElevenLabs voices page in browser."""
        webbrowser.open("https://elevenlabs.io/voice-library")
        self.log_to_console("Opened ElevenLabs voice library in browser")
        messagebox.showinfo("Voice Selection", 
                           "1. Select a voice you like\n"
                           "2. Click on the voice\n"
                           "3. Locate the Voice ID in the URL or settings\n"
                           "4. Copy and paste the ID into the appropriate field")
    
    def load_default_sfx_prompts(self):
        """Load default sound effect prompts."""
        default_prompts = [
            "thunder:Loud rumbling thunder during a storm",
            "heartbeat:Deep rhythmic heartbeat sounds",
            "ghat:Ambient sounds from the Ganges river bank with distant temple bells",
            "water:Flowing water sound with gentle splashes",
            "temple_bells:Sacred Indian temple bells ringing",
            "whispers:Ghostly whispers in a dark room",
            "footsteps:Heavy footsteps on wooden floor",
            "wind:Howling wind through narrow streets",
            "crowd:Busy Indian market crowd noises",
            "door:Old wooden door creaking open"
        ]
        
        self.sfx_prompts_text.delete(1.0, tk.END)
        self.sfx_prompts_text.insert(tk.END, "\n".join(default_prompts))
        self.log_to_console("Loaded default sound effect prompts")
    
    def browse_script(self):
        """Browse for script file."""
        filepath = filedialog.askopenfilename(
            title="Select Script File",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        if filepath:
            self.script_path_var.set(filepath)
            
            # Generate default output path if empty
            if not self.output_path_var.get():
                script_name = os.path.basename(filepath).split('.')[0]
                output_dir = os.path.join(os.path.dirname(filepath), "output")
                os.makedirs(output_dir, exist_ok=True)
                self.output_path_var.set(os.path.join(output_dir, f"{script_name}_output.mp3"))
    
    def browse_output(self):
        """Browse for output file location."""
        filepath = filedialog.asksaveasfilename(
            title="Save Podcast As",
            defaultextension=".mp3",
            filetypes=[("MP3 Files", "*.mp3"), ("WAV Files", "*.wav"), ("OGG Files", "*.ogg")]
        )
        if filepath:
            self.output_path_var.set(filepath)
    
    def load_config(self, config_path=None):
        """Load settings from config file."""
        if config_path is None:
            config_path = self.config_path_var.get()
        
        if not os.path.exists(config_path):
            # Don't show an error for the default config on first run
            if config_path != CONFIG_FILE:
                messagebox.showwarning("Warning", f"Config file {config_path} does not exist.")
            return
        
        try:
            config = configparser.ConfigParser()
            config.read(config_path)
            
            # Load voice settings
            if "Speakers" in config:
                if "bhaskar" in config["Speakers"]:
                    self.bhaskar_voice_var.set(config["Speakers"]["bhaskar"])
                if "mishra" in config["Speakers"]:
                    self.mishra_voice_var.set(config["Speakers"]["mishra"])
                if "default" in config["Speakers"]:
                    self.default_voice_var.set(config["Speakers"]["default"])
            
            if "VoiceSynthesis" in config:
                if "model" in config["VoiceSynthesis"]:
                    self.voice_model_var.set(config["VoiceSynthesis"]["model"])
            
            # Load SFX prompts
            if "SoundEffectsPrompts" in config:
                self.sfx_prompts_text.delete(1.0, tk.END)
                for key, value in config["SoundEffectsPrompts"].items():
                    self.sfx_prompts_text.insert(tk.END, f"{key}:{value}\n")
            
            self.log_to_console(f"Loaded configuration from {config_path}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error loading config: {str(e)}")
    
    def save_config(self):
        """Save current settings to config file."""
        config_path = self.config_path_var.get()
        
        try:
            config = configparser.ConfigParser()
            
            # If the file exists, read it first to preserve other settings
            if os.path.exists(config_path):
                config.read(config_path)
            
            # Ensure all required sections exist
            for section in ["General", "VoiceSynthesis", "SoundEffects", 
                           "SoundEffectsPrompts", "Speakers", "Audio"]:
                if not config.has_section(section):
                    config.add_section(section)
            
            # Update voice settings
            config["Speakers"]["bhaskar"] = self.bhaskar_voice_var.get()
            config["Speakers"]["mishra"] = self.mishra_voice_var.get()
            config["Speakers"]["default"] = self.default_voice_var.get()
            
            config["VoiceSynthesis"]["model"] = self.voice_model_var.get()
            config["VoiceSynthesis"]["stability"] = "0.5"  # Default
            config["VoiceSynthesis"]["similarity_boost"] = "0.75"  # Default
            
            # Update SFX settings
            config["SoundEffects"]["sfx_model"] = "eleven_multilingual_v2"  # Better for SFX
            config["SoundEffects"]["default_duration"] = "3000"  # Default
            
            # Update SFX prompts
            # First clear existing prompts
            if "SoundEffectsPrompts" in config:
                config.remove_section("SoundEffectsPrompts")
            config.add_section("SoundEffectsPrompts")
            
            # Add new prompts
            sfx_prompts = self.sfx_prompts_text.get(1.0, tk.END).strip().split("\n")
            for prompt in sfx_prompts:
                if prompt and ":" in prompt:
                    key, value = prompt.split(":", 1)
                    config["SoundEffectsPrompts"][key.strip()] = value.strip()
            
            # Update audio settings
            config["Audio"]["format"] = "mp3"  # Default
            config["Audio"]["bit_rate"] = "192k"  # Default
            config["Audio"]["normalize_audio"] = "True"  # Default
            
            # Save to file
            with open(config_path, 'w') as f:
                config.write(f)
            
            self.log_to_console(f"Saved configuration to {config_path}")
            messagebox.showinfo("Success", "Configuration saved successfully")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error saving config: {str(e)}")
    
    def log_to_console(self, message):
        """Log message to console output."""
        self.console_output.config(state=tk.NORMAL)
        self.console_output.insert(tk.END, f"{message}\n")
        self.console_output.see(tk.END)
        self.console_output.config(state=tk.DISABLED)
    
    def generate_podcast(self):
        """Generate podcast based on current settings."""
        # Validate inputs
        if not self.script_path_var.get():
            messagebox.showerror("Error", "Script file is required")
            return
        
        if not os.path.exists(self.script_path_var.get()):
            messagebox.showerror("Error", "Script file does not exist")
            return
        
        if not self.api_keys_var.get():
            messagebox.showerror("Error", "At least one API key is required")
            return
        
        # Save current configuration
        self.save_config()
        
        # Build command
        script_file = self.script_path_var.get()
        output_file = self.output_path_var.get()
        api_keys = self.api_keys_var.get()
        config_file = self.config_path_var.get()
        
        # Create command arguments
        cmd = [
            sys.executable,
            os.path.join(BASE_DIR, "podcast_generator_v2.py"),
            "-s", script_file,
            "-k", api_keys,
            "-c", config_file
        ]
        
        if output_file:
            cmd.extend(["-o", output_file])
        
        self.log_to_console(f"Starting podcast generation...")
        self.log_to_console(f"Command: {' '.join(cmd)}")
        
        # Run in a separate thread to keep UI responsive
        thread = threading.Thread(target=self.run_command, args=(cmd,))
        thread.daemon = True
        thread.start()
    
    def run_command(self, cmd):
        """Run command in a separate thread and display output."""
        try:
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            for line in process.stdout:
                self.root.after(10, self.log_to_console, line.strip())
            
            process.wait()
            
            if process.returncode == 0:
                self.root.after(10, messagebox.showinfo, "Success", "Podcast generated successfully")
            else:
                self.root.after(10, messagebox.showerror, "Error", 
                               f"Podcast generation failed with code {process.returncode}")
                
        except Exception as e:
            self.root.after(10, messagebox.showerror, "Error", f"Error running command: {str(e)}")


def main():
    """Run the UI."""
    root = tk.Tk()
    app = PodcastGeneratorUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
