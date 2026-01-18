"""
Converts a stereo WAV file into a C++ wavetable header format.
Resamples to 1024 samples and outputs signed 16-bit integer arrays.
"""

import sys
import os
import wave
import numpy as np
from scipy import signal
import argparse


def resample_audio(audio_data, original_rate, target_samples):
    """
    Resample audio data to target number of samples using high-quality resampling.
    
    Args:
        audio_data: numpy array of audio samples
        original_rate: original sample rate
        target_samples: target number of samples (1024)
    
    Returns:
        Resampled audio data
    """
    current_samples = len(audio_data)
    resampled = signal.resample(audio_data, target_samples)
    return resampled


def normalize_to_int16(audio_data):
    """
    Normalize audio data and convert to signed 16-bit integers.
    
    Args:
        audio_data: numpy array of float audio samples
    
    Returns:
        numpy array of int16 values
    """
    # Normalize to -1.0 to 1.0
    max_val = np.max(np.abs(audio_data))
    if max_val > 0:
        audio_data = audio_data / max_val
    
    # Scale to int16 range and convert
    audio_int16 = np.clip(audio_data * 32767, -32768, 32767).astype(np.int16)
    return audio_int16


def read_wav_file(filename):
    """
    Read a WAV file and return stereo audio data.
    
    Args:
        filename: path to WAV file
    
    Returns:
        tuple of (left_channel, right_channel) as numpy arrays
    """
    with wave.open(filename, 'rb') as wav_file:
        # Get WAV file parameters
        n_channels = wav_file.getnchannels()
        sampwidth = wav_file.getsampwidth()
        framerate = wav_file.getframerate()
        n_frames = wav_file.getnframes()
        
        print(f"Input WAV: {n_channels} channels, {framerate} Hz, {n_frames} frames")
        
        # Read all frames
        frames = wav_file.readframes(n_frames)
        
        # Convert to numpy array based on sample width
        if sampwidth == 1:
            dtype = np.uint8
            audio_data = np.frombuffer(frames, dtype=dtype).astype(np.float32)
            audio_data = (audio_data - 128) / 128.0
        elif sampwidth == 2:
            dtype = np.int16
            audio_data = np.frombuffer(frames, dtype=dtype).astype(np.float32)
            audio_data = audio_data / 32768.0
        elif sampwidth == 4:
            dtype = np.int32
            audio_data = np.frombuffer(frames, dtype=dtype).astype(np.float32)
            audio_data = audio_data / 2147483648.0
        else:
            raise ValueError(f"Unsupported sample width: {sampwidth}")
        
        # Separate channels
        if n_channels == 1:
            # Mono - duplicate to stereo
            left = audio_data
            right = audio_data.copy()
        elif n_channels == 2:
            # Stereo - separate channels
            left = audio_data[0::2]
            right = audio_data[1::2]
        else:
            # More than 2 channels - take first two
            audio_data = audio_data.reshape(-1, n_channels)
            left = audio_data[:, 0]
            right = audio_data[:, 1]
        
        return left, right, framerate


def format_stereo_array_for_cpp(left_array, right_array, values_per_line=8):
    """
    Format two numpy arrays as C++ StereoTable initialization code.
    
    Args:
        left_array: numpy array of int16 values for left channel
        right_array: numpy array of int16 values for right channel
        values_per_line: number of values per line in output
    
    Returns:
        String containing formatted arrays for left and right channels
    """
    lines = []
    
    # Format left channel
    lines.append("    {")
    for i in range(0, len(left_array), values_per_line):
        chunk = left_array[i:i + values_per_line]
        values = ', '.join(f'{v:6d}' for v in chunk)
        if i + values_per_line < len(left_array):
            lines.append(f"        {values},")
        else:
            lines.append(f"        {values}")
    lines.append("    },")
    
    # Format right channel
    lines.append("    {")
    for i in range(0, len(right_array), values_per_line):
        chunk = right_array[i:i + values_per_line]
        values = ', '.join(f'{v:6d}' for v in chunk)
        if i + values_per_line < len(right_array):
            lines.append(f"        {values},")
        else:
            lines.append(f"        {values}")
    lines.append("    }")
    
    return '\n'.join(lines)


def wav_to_wavetable(input_file, table_name="WAVETABLE", output_file=None):
    """
    Convert WAV file to C++ wavetable header.
    
    Args:
        input_file: path to input WAV file
        table_name: base name for the C++ arrays
        output_file: optional output file path (if None, prints to stdout)
    """
    # Read WAV file
    left, right, sample_rate = read_wav_file(input_file)
    
    # Resample to 1024 samples
    target_samples = 1024
    left_resampled = resample_audio(left, sample_rate, target_samples)
    right_resampled = resample_audio(right, sample_rate, target_samples)
    
    # Convert to int16
    left_int16 = normalize_to_int16(left_resampled)
    right_int16 = normalize_to_int16(right_resampled)
    
    # Generate C++ code
    output_lines = [
        "#pragma once",
        "#include <cstdint>",
        "",
        f"// Generated from: {input_file}",
        f"// Original sample rate: {sample_rate} Hz",
        f"// Resampled to: {target_samples} samples",
        "",
        "// StereoTable type defined in lookup_tables.h",
        "// Copy below into lookup_tables.h",
        "",
        f"inline constexpr StereoTable {table_name}_TABLE = {{",
    ]
    
    # Format stereo arrays
    output_lines.append(format_stereo_array_for_cpp(left_int16, right_int16))
    
    output_lines.append("};")
    output_lines.append("")
    
    result = '\n'.join(output_lines)
    
    # Output
    if output_file:
        with open(output_file, 'w') as f:
            f.write(result)
        print(f"Wavetable written to: {output_file}")
    else:
        print(result)
    
    print(f"\nConversion complete!")
    print(f"Left channel range: [{left_int16.min()}, {left_int16.max()}]")
    print(f"Right channel range: [{right_int16.min()}, {right_int16.max()}]")


def main():
    parser = argparse.ArgumentParser(
        description='Convert stereo WAV file to C++ wavetable header (1024 samples, signed 16-bit)'
    )
    parser.add_argument('input', help='Input WAV file path')
    parser.add_argument('-o', '--output', 
                        help='Output header file path (default: ../data/<input_name>_table.h)')
    
    args = parser.parse_args()
    
    # Set default output path if not provided
    if args.output is None:
        # Generate output filename based on input filename
        input_basename = os.path.splitext(os.path.basename(args.input))[0]
        output_filename = f"{input_basename}_table.h"
        args.output = os.path.join(os.path.dirname(__file__), '..', 'data', output_filename)
    
    try:
        wav_to_wavetable(args.input, 'WAVETABLE', args.output)
    except FileNotFoundError:
        print(f"Error: File '{args.input}' not found.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
