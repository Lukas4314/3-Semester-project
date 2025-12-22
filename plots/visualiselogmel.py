import numpy as np
import torch
import matplotlib.pyplot as plt
import librosa
import librosa.display
import soundfile as sf
from pathlib import Path

# Method 1: Using OpenAI Whisper's built-in function
def compute_log_mel_with_whisper(wav_path, model_size="tiny"):
    """
    Compute log-Mel spectrogram using OpenAI Whisper's implementation
    """
    try:
        import whisper
        from whisper.audio import log_mel_spectrogram, load_audio, SAMPLE_RATE
        
        print(f"Loading audio with Whisper (sample rate: {SAMPLE_RATE}Hz)...")
        
        # Load audio using Whisper's loader (resamples to 16kHz automatically)
        audio = load_audio(wav_path)
        
        print(f"Audio loaded: {len(audio)} samples ({len(audio)/SAMPLE_RATE:.2f}s)")
        
        # Load model to get n_mels parameter
        model = whisper.load_model(model_size)
        n_mels = model.dims.n_mels
        
        print(f"Using {n_mels} mel bins from {model_size} model")
        
        # Compute log-Mel spectrogram
        mel = log_mel_spectrogram(audio, n_mels=n_mels)
        
        return mel, audio, SAMPLE_RATE
    
    except ImportError:
        print("Error: OpenAI Whisper not installed. Install with: pip install openai-whisper")
        return None, None, None

# Method 2: Using librosa (if Whisper is not available)
def compute_log_mel_with_librosa(wav_path, n_mels=80):
    """
    Compute log-Mel spectrogram using librosa
    """
    try:
        # Load audio with librosa (automatically resamples to given sr)
        audio, orig_sr = librosa.load(wav_path, sr=16000)
        
        print(f"Audio loaded: {len(audio)} samples at 16000Hz ({len(audio)/16000:.2f}s)")
        print(f"Original sample rate: {orig_sr}Hz")
        
        # Compute Mel spectrogram
        mel_spec = librosa.feature.melspectrogram(
            y=audio,
            sr=16000,
            n_fft=400,
            hop_length=160,
            win_length=400,
            window='hann',
            n_mels=n_mels,
            fmin=0,
            fmax=8000
        )
        
        # Convert to log scale (similar to Whisper)
        log_mel = librosa.power_to_db(mel_spec, ref=np.max)
        
        # Convert to tensor for consistency
        log_mel_tensor = torch.from_numpy(log_mel)
        
        return log_mel_tensor, audio, 16000
    
    except ImportError:
        print("Error: librosa not installed. Install with: pip install librosa")
        return None, None, None

def visualize_mel_comparison(mel_whisper, mel_librosa=None, sr=16000, hop_length=160):
    """
    Compare and visualize different Mel spectrogram computations
    """
    # Convert tensors to numpy if needed
    if torch.is_tensor(mel_whisper):
        mel_whisper_np = mel_whisper.cpu().numpy()
    else:
        mel_whisper_np = mel_whisper
    
    # Calculate duration based on Whisper's output
    duration_whisper = mel_whisper_np.shape[1] * hop_length / sr
    
    if mel_librosa is None:
        fig, axes = plt.subplots(1, 3, figsize=(15, 4))
        
        # 1. Whisper Mel spectrogram
        im1 = axes[0].imshow(mel_whisper_np, 
                           aspect='auto', 
                           origin='lower',
                           extent=[0, duration_whisper, 0, mel_whisper_np.shape[0]],
                           cmap='viridis')
        axes[0].set_xlabel('Time (s)')
        axes[0].set_ylabel('Mel Bins')
        axes[0].set_title(f'Whisper Log-Mel\nShape: {mel_whisper_np.shape}')
        plt.colorbar(im1, ax=axes[0], label='Normalized Value')
        
        # 2. Whisper frequency profile
        mean_freq_whisper = np.mean(mel_whisper_np, axis=1)
        axes[1].plot(mean_freq_whisper, np.arange(mel_whisper_np.shape[0]))
        axes[1].set_xlabel('Mean Value')
        axes[1].set_ylabel('Mel Bins')
        axes[1].set_title('Whisper: Frequency Profile')
        axes[1].grid(True, alpha=0.3)
        
        # 3. Whisper energy over time
        mean_time_whisper = np.mean(mel_whisper_np, axis=0)
        time_axis_whisper = np.linspace(0, duration_whisper, len(mean_time_whisper))
        axes[2].plot(time_axis_whisper, mean_time_whisper)
        axes[2].set_xlabel('Time (s)')
        axes[2].set_ylabel('Mean Value')
        axes[2].set_title('Whisper: Energy over Time')
        axes[2].grid(True, alpha=0.3)
        
    else:
        fig, axes = plt.subplots(2, 3, figsize=(15, 8))
        
        if torch.is_tensor(mel_librosa):
            mel_librosa_np = mel_librosa.cpu().numpy()
        else:
            mel_librosa_np = mel_librosa
        
        # Calculate duration based on librosa's output
        duration_librosa = mel_librosa_np.shape[1] * hop_length / sr
        
        # 1. Whisper Mel spectrogram
        im1 = axes[0, 0].imshow(mel_whisper_np, 
                               aspect='auto', 
                               origin='lower',
                               extent=[0, duration_whisper, 0, mel_whisper_np.shape[0]],
                               cmap='viridis')
        axes[0, 0].set_xlabel('Time (s)')
        axes[0, 0].set_ylabel('Mel Bins')
        axes[0, 0].set_title(f'Whisper Log-Mel\nShape: {mel_whisper_np.shape}')
        plt.colorbar(im1, ax=axes[0, 0], label='Normalized Value')
        
        # 2. Whisper frequency profile
        mean_freq_whisper = np.mean(mel_whisper_np, axis=1)
        axes[0, 1].plot(mean_freq_whisper, np.arange(mel_whisper_np.shape[0]))
        axes[0, 1].set_xlabel('Mean Value')
        axes[0, 1].set_ylabel('Mel Bins')
        axes[0, 1].set_title('Whisper: Frequency Profile')
        axes[0, 1].grid(True, alpha=0.3)
        
        # 3. Whisper energy over time
        mean_time_whisper = np.mean(mel_whisper_np, axis=0)
        time_axis_whisper = np.linspace(0, duration_whisper, len(mean_time_whisper))
        axes[0, 2].plot(time_axis_whisper, mean_time_whisper)
        axes[0, 2].set_xlabel('Time (s)')
        axes[0, 2].set_ylabel('Mean Value')
        axes[0, 2].set_title('Whisper: Energy over Time')
        axes[0, 2].grid(True, alpha=0.3)
        
        # 4. Librosa Mel spectrogram
        im2 = axes[1, 0].imshow(mel_librosa_np, 
                               aspect='auto', 
                               origin='lower',
                               extent=[0, duration_librosa, 0, mel_librosa_np.shape[0]],
                               cmap='viridis')
        axes[1, 0].set_xlabel('Time (s)')
        axes[1, 0].set_ylabel('Mel Bins')
        axes[1, 0].set_title(f'Librosa Log-Mel\nShape: {mel_librosa_np.shape}')
        plt.colorbar(im2, ax=axes[1, 0], label='dB')
        
        # 5. Librosa frequency profile
        mean_freq_librosa = np.mean(mel_librosa_np, axis=1)
        axes[1, 1].plot(mean_freq_librosa, np.arange(mel_librosa_np.shape[0]))
        axes[1, 1].set_xlabel('Mean Value (dB)')
        axes[1, 1].set_ylabel('Mel Bins')
        axes[1, 1].set_title('Librosa: Frequency Profile')
        axes[1, 1].grid(True, alpha=0.3)
        
        # 6. Librosa energy over time
        mean_time_librosa = np.mean(mel_librosa_np, axis=0)
        time_axis_librosa = np.linspace(0, duration_librosa, len(mean_time_librosa))
        axes[1, 2].plot(time_axis_librosa, mean_time_librosa)
        axes[1, 2].set_xlabel('Time (s)')
        axes[1, 2].set_ylabel('Mean Value (dB)')
        axes[1, 2].set_title('Librosa: Energy over Time')
        axes[1, 2].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.show()
    
    # Print statistics
    print(f"\n=== WHISPER MEL STATISTICS ===")
    print(f"Shape: {mel_whisper_np.shape}")
    print(f"Duration: {duration_whisper:.2f} seconds")
    print(f"Time per frame: {hop_length/sr*1000:.1f} ms")
    print(f"Value range: [{mel_whisper_np.min():.4f}, {mel_whisper_np.max():.4f}]")
    print(f"Mean: {mel_whisper_np.mean():.4f}, Std: {mel_whisper_np.std():.4f}")
    
    if mel_librosa is not None:
        print(f"\n=== LIBROSA MEL STATISTICS ===")
        print(f"Shape: {mel_librosa_np.shape}")
        print(f"Duration: {duration_librosa:.2f} seconds")
        print(f"Value range: [{mel_librosa_np.min():.2f}, {mel_librosa_np.max():.2f}] dB")
        print(f"Mean: {mel_librosa_np.mean():.2f}, Std: {mel_librosa_np.std():.2f}")

def analyze_whisper_mel_details(mel_tensor, sr=16000, hop_length=160):
    """
    Analyze the details of Whisper's Mel spectrogram output
    """
    if torch.is_tensor(mel_tensor):
        mel_np = mel_tensor.cpu().numpy()
    else:
        mel_np = mel_tensor
    
    print(f"\n=== DETAILED ANALYSIS OF WHISPER MEL ===")
    print(f"Tensor shape: {mel_tensor.shape if torch.is_tensor(mel_tensor) else mel_np.shape}")
    print(f"Data type: {mel_tensor.dtype if torch.is_tensor(mel_tensor) else mel_np.dtype}")
    
    # Reverse Whisper's normalization to see actual dB values
    # Whisper does: (log_spec + 4.0) / 4.0
    log_spec_db = mel_np * 4.0 - 4.0  # Reverse normalization
    
    # Plot the de-normalized version
    fig, axes = plt.subplots(2, 3, figsize=(15, 8))
    
    # 1. Original (normalized)
    im1 = axes[0, 0].imshow(mel_np, aspect='auto', origin='lower', cmap='viridis')
    axes[0, 0].set_title('Normalized (as Whisper sees it)')
    axes[0, 0].set_xlabel('Time frames')
    axes[0, 0].set_ylabel('Mel bins')
    plt.colorbar(im1, ax=axes[0, 0])
    
    # 2. De-normalized (actual dB)
    im2 = axes[0, 1].imshow(log_spec_db, aspect='auto', origin='lower', cmap='viridis')
    axes[0, 1].set_title('De-normalized (actual dB values)')
    axes[0, 1].set_xlabel('Time frames')
    axes[0, 1].set_ylabel('Mel bins')
    plt.colorbar(im2, ax=axes[0, 1], label='dB')
    
    # 3. Difference between consecutive frames
    if mel_np.shape[1] > 1:
        frame_diff = np.abs(mel_np[:, 1:] - mel_np[:, :-1])
        im3 = axes[0, 2].imshow(frame_diff, aspect='auto', origin='lower', cmap='hot')
        axes[0, 2].set_title('Frame-to-frame difference')
        axes[0, 2].set_xlabel('Time frames')
        axes[0, 2].set_ylabel('Mel bins')
        plt.colorbar(im3, ax=axes[0, 2])
    
    # 4. Histogram of values
    axes[1, 0].hist(mel_np.flatten(), bins=100, alpha=0.7, density=True)
    axes[1, 0].set_title('Histogram of normalized values')
    axes[1, 0].set_xlabel('Normalized value')
    axes[1, 0].set_ylabel('Density')
    axes[1, 0].grid(True, alpha=0.3)
    
    # 5. Histogram of dB values
    axes[1, 1].hist(log_spec_db.flatten(), bins=100, alpha=0.7, density=True)
    axes[1, 1].set_title('Histogram of dB values')
    axes[1, 1].set_xlabel('dB')
    axes[1, 1].set_ylabel('Density')
    axes[1, 1].grid(True, alpha=0.3)
    
    # 6. Check variation across mel bins
    std_per_bin = np.std(mel_np, axis=1)
    axes[1, 2].plot(std_per_bin)
    axes[1, 2].set_title('Standard deviation per mel bin')
    axes[1, 2].set_xlabel('Mel bin index')
    axes[1, 2].set_ylabel('Standard deviation')
    axes[1, 2].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.show()
    
    # Print detailed statistics
    print(f"\nNormalized values: min={mel_np.min():.6f}, max={mel_np.max():.6f}")
    print(f"dB values: min={log_spec_db.min():.2f}, max={log_spec_db.max():.2f}")
    print(f"\nStandard deviation across:")
    print(f"  Time: {np.std(mel_np, axis=1).mean():.6f} (per bin)")
    print(f"  Frequency: {np.std(mel_np, axis=0).mean():.6f} (per frame)")
    
    # Check if values are constant across mel bins
    print(f"\nStatistics per mel bin (every 8th bin):")
    for i in range(0, mel_np.shape[0], 8):
        bin_values = mel_np[i, :]
        print(f"  Mel bin {i:3d}: mean={bin_values.mean():.6f}, std={bin_values.std():.6f}, "
              f"range=[{bin_values.min():.6f}, {bin_values.max():.6f}]")

def plot_audio_waveform_with_spectrogram(audio, sr, mel_spec, hop_length=160):
    """
    Plot audio waveform with spectrogram
    """
    duration = len(audio) / sr
    mel_duration = mel_spec.shape[1] * hop_length / sr
    
    if torch.is_tensor(mel_spec):
        mel_np = mel_spec.cpu().numpy()
    else:
        mel_np = mel_spec
    
    fig, axes = plt.subplots(2, 1, figsize=(14, 9))
    
    # 1. Audio waveform
    time_axis = np.linspace(0, duration, len(audio))
    axes[0].plot(time_axis, audio)
    axes[0].set_xlabel('Time (s)', fontsize=22)
    axes[0].set_ylabel('Amplitude',fontsize=22)
    axes[0].set_title(f'Audio Waveform ({len(audio)} samples, {duration:.2f}s)', fontsize=26)
    axes[0].grid(True, alpha=0.3)
    axes[0].set_xlim(0, duration)
    axes[0].tick_params(axis='both', which='major', labelsize=22)
    
    # 2. Zoomed in waveform (first 0.1 seconds)
    """zoom_samples = min(int(0.1 * sr), len(audio))
    axes[1].plot(time_axis[:zoom_samples], audio[:zoom_samples])
    axes[1].set_xlabel('Time (s)')
    axes[1].set_ylabel('Amplitude')
    axes[1].set_title('Zoom: First 0.1 seconds')
    axes[1].grid(True, alpha=0.3)"""
    
    # 3. Spectrogram
    im = axes[1].imshow(mel_np, 
                       aspect='auto', 
                       origin='lower',
                       extent=[0, mel_duration, 0, mel_np.shape[0]],
                       cmap='viridis')
    axes[1].set_xlabel('Time (s)', fontsize=22)
    axes[1].set_ylabel('Mel Bins', fontsize=22)
    axes[1].set_title(f'Log-Mel Spectrogram ({mel_np.shape[1]} frames)', fontsize=26)
    cbar = plt.colorbar(im, ax=axes[1], label='Normalized Value')
    cbar.ax.tick_params(labelsize=22)
    axes[1].tick_params(axis='both', which='major', labelsize=22)
    
    plt.tight_layout()
    plt.show()

def plot_mel_as_seen_by_model(mel_tensor):
    """
    Plot exactly what the Whisper model sees
    """
    if torch.is_tensor(mel_tensor):
        mel_np = mel_tensor.cpu().numpy()
    else:
        mel_np = mel_tensor
    
    print(f"\n=== WHAT WHISPER MODEL SEES ===")
    print(f"Shape: {mel_np.shape}")
    print(f"Value range: [{mel_np.min():.6f}, {mel_np.max():.6f}]")
    
    # The model expects input in this specific range
    plt.figure(figsize=(12, 5))
    
    # Plot the entire spectrogram
    plt.subplot(1, 2, 1)
    im = plt.imshow(mel_np, aspect='auto', origin='lower', cmap='viridis')
    plt.colorbar(im, label='Normalized Value')
    plt.xlabel('Time frames')
    plt.ylabel('Mel bins')
    plt.title(f'Input to Whisper Model\nShape: {mel_np.shape}')
    
    # Plot a zoomed-in section
    plt.subplot(1, 2, 2)
    time_frames_to_show = min(50, mel_np.shape[1])
    mel_bins_to_show = min(40, mel_np.shape[0])
    
    im_zoom = plt.imshow(mel_np[:mel_bins_to_show, :time_frames_to_show], 
                         aspect='auto', origin='lower', cmap='viridis')
    plt.colorbar(im_zoom, label='Normalized Value')
    plt.xlabel(f'Time frames (first {time_frames_to_show})')
    plt.ylabel(f'Mel bins (first {mel_bins_to_show})')
    plt.title('Zoomed-in View')
    
    plt.tight_layout()
    plt.show()
    
    # Print first few values to see actual numbers
    print("\nFirst 5 frames, first 10 mel bins:")
    for i in range(min(5, mel_np.shape[1])):
        print(f"Frame {i}: {mel_np[:10, i].round(4)}")
    
    print("\nLast 5 frames, first 10 mel bins:")
    for i in range(max(0, mel_np.shape[1]-5), mel_np.shape[1]):
        print(f"Frame {i}: {mel_np[:10, i].round(4)}")

def main():
    # Get WAV file path
    wav_path = input("Enter path to WAV file (or press Enter for default): ").strip()
    
    if not wav_path:
        # Try to find a WAV file in current directory
        wav_files = list(Path(".").glob("*.wav"))
        if wav_files:
            wav_path = str(wav_files[0])
            print(f"Using found WAV file: {wav_path}")
        else:
            print("No WAV file found. Please provide a path.")
            return
    
    print(f"Processing: {wav_path}")
    
    # Try to use Whisper's implementation
    mel_whisper, audio, sr = compute_log_mel_with_whisper(wav_path)
    
    if mel_whisper is not None:
        print(f"\n✓ Successfully computed with Whisper")
        
        # Visualize
        visualize_mel_comparison(mel_whisper, None, sr=sr)
        
        # Analyze details
        analyze_whisper_mel_details(mel_whisper, sr=sr)
        
        # Plot audio with spectrogram
        plot_audio_waveform_with_spectrogram(audio, sr, mel_whisper)
        
        # Plot exactly what the model sees
        plot_mel_as_seen_by_model(mel_whisper)
        
        # Save the spectrogram as image
        if torch.is_tensor(mel_whisper):
            mel_np = mel_whisper.cpu().numpy()
        
        plt.figure(figsize=(10, 4))
        plt.imshow(mel_np, aspect='auto', origin='lower', cmap='viridis')
        plt.colorbar(label='Normalized Value')
        plt.xlabel('Time frames')
        plt.ylabel('Mel bins')
        plt.title(f'Whisper Log-Mel Spectrogram: {Path(wav_path).name}')
        plt.tight_layout()
        plt.savefig('whisper_mel_spectrogram.png', dpi=150, bbox_inches='tight')
        print(f"\n✓ Spectrogram saved as 'whisper_mel_spectrogram.png'")
        
        # Also try librosa for comparison (but handle dimension mismatch)
        try:
            mel_librosa, _, _ = compute_log_mel_with_librosa(wav_path, n_mels=mel_whisper.shape[0])
            if mel_librosa is not None:
                print("\nComputing with librosa for comparison...")
                # Visualize separately to avoid dimension issues
                visualize_mel_comparison(mel_librosa, None, sr=sr)
        except Exception as e:
            print(f"Could not compute with librosa: {e}")
        
    else:
        print("\nTrying librosa fallback...")
        mel_librosa, audio, sr = compute_log_mel_with_librosa(wav_path)
        
        if mel_librosa is not None:
            visualize_mel_comparison(mel_librosa, None, sr=sr)
            plot_audio_waveform_with_spectrogram(audio, sr, mel_librosa)
            plot_mel_as_seen_by_model(mel_librosa)
        else:
            print("Failed to compute spectrogram with both methods.")

if __name__ == "__main__":
    # Install required packages if not already installed
    required_packages = ['numpy', 'torch', 'matplotlib', 'librosa', 'soundfile']
    
    print("Checking for required packages...")
    for package in required_packages:
        try:
            __import__(package)
            print(f"  ✓ {package}")
        except ImportError:
            print(f"  ✗ {package} - Install with: pip install {package}")
    
    print("\n" + "="*50)
    main()