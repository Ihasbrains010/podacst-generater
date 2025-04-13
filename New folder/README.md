# Advanced Auto Podcast Generator with ElevenLabs SFX

An automated tool to generate Bhaskar Bose-style podcasts with multiple voice synthesis and sound effects, all generated through ElevenLabs API with complete customization options and credit tracking.

## Key Features

- **All-in-one ElevenLabs Solution**: Both voices and sound effects are generated using ElevenLabs API
- **API Key Rotation**: Automatically cycles through multiple API keys to avoid credit exhaustion
- **Comprehensive Credit Tracking**: Logs credit usage for both voice synthesis and sound effects
- **Full Customization**: Configure every aspect via config file or command-line arguments
- **Expressive Sound Effects**: Uses text prompts to generate realistic environmental sounds
- **High-Quality Output**: Produces professional podcasts with normalized audio

## Installation

1. Clone this repository or download the files
2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

3. Install FFmpeg (required for audio processing):
   - Windows: Download from [FFmpeg.org](https://ffmpeg.org/download.html) and add to PATH
   - macOS: `brew install ffmpeg`
   - Linux: `sudo apt-get install ffmpeg`

## Setting Up API Keys

You have two options for providing ElevenLabs API keys:

1. **Using Environment Variables**:
   Create a `.env` file in the project directory with:
   ```
   ELEVENLABS_API_KEYS=key1,key2,key3
   ```

2. **Command Line**:
   Provide API keys directly when running the script with the `-k` flag

## Script Format

Create a text file with the following format:

```
[SPEAKER: Bhaskar]
Welcome to another episode of Bhaskar Bose.
[SFX: thunder]
[SPEAKER: Mishra]
This case... it doesn't make sense, Bhaskar.
[SFX: ghat]
[SPEAKER: Bhaskar]
Yes, but I can feel there's something here, deep within Banaras.
[SFX: heartbeat]
```

## Usage

Run the podcast generator with:

```bash
python podcast_generator_v2.py -s script.txt
```

### Basic Options:
- `-s` or `--script`: Path to script file (required)
- `-o` or `--output`: Specify output file path
- `-k` or `--keys`: Provide comma-separated API keys
- `-c` or `--config`: Path to custom config file

### Voice Customization:
- `--model`: ElevenLabs model ID for voice synthesis
- `--stability`: Voice stability (0.0-1.0)
- `--similarity-boost`: Voice similarity boost (0.0-1.0)

### Sound Effects Customization:
- `--sfx-model`: Model ID for sound effects generation
- `--sfx-duration`: Default duration for sound effects in milliseconds
- `--sfx-prompt`: Custom sound effect prompt (format: 'effect:prompt text')

### Speaker Mapping:
- `--speaker-mapping`: Custom speaker to voice ID mapping (format: 'Speaker:VoiceID')

### Output Customization:
- `--format`: Output audio format (mp3, wav, ogg)
- `--bit-rate`: Output bit rate (e.g., '192k')
- `--normalize`: Whether to normalize audio levels (true/false)

Example with multiple customizations:
```bash
python podcast_generator_v2.py -s script.txt -o my_podcast.mp3 -k key1,key2,key3 --sfx-prompt "thunder:Loud continuous thunder with heavy rain" --speaker-mapping "Bhaskar:ErXwobaYiN019PkySvjV"
```

## Configuration

All settings can be configured in the `podcast_config.ini` file, which is automatically created on first run. You can also specify a custom configuration file with the `-c` flag.

### Default Sound Effects

The system comes with default prompts for generating these sound effects:
- thunder
- heartbeat
- ghat (ambient Ganges river bank sounds)
- water
- temple_bells
- whispers
- footsteps
- wind
- crowd
- door

You can add custom sound effects by adding new entries to the `SoundEffectsPrompts` section in the config file.

## Voice Customization

Default voices are:
- Bhaskar: Antoni (deep authoritative male)
- Mishra: Adam (mature male)
- Default: Rachel (female)

To use custom voices, add them to the `Speakers` section in the config file or use the `--speaker-mapping` argument.

## Credit Tracking

Credit usage is logged in `credits_log.json` and includes:
- Timestamp of each API call
- Operation type (speech_synthesis or sfx_generation)
- Character count used
- Credits consumed

## Advanced Features

- **API Call Retry Logic**: Automatically retries failed API calls
- **Sound Effect Caching**: Improves performance for repeated sound effects
- **Configurable Overlapping**: Control whether sound effects overlap with speech
- **Custom Audio Parameters**: Configure silence durations, normalization, etc.
