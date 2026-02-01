import streamlit as st
import os
from pydub import AudioSegment, silence
import base64

# --- CONFIGURATION ---
AUDIO_DIR = "audio_files"  # Directory where your MP3/MP4s are
CACHE_DIR = "processed_cache" # Where we store split data
# ---------------------

st.set_page_config(page_title="Dictation Buddy", layout="wide")

@st.cache_data
def load_audio_ranges(file_path, min_silence_len=700, silence_thresh=-40):
    """
    Splits audio into sentences by detecting silence.
    Returns: List of [start_ms, end_ms]
    """
    try:
        audio = AudioSegment.from_file(file_path)
        # Detect nonsilent chunks (where the talking is)
        # min_silence_len: milliseconds of silence to consider a break
        # silence_thresh: dBFS threshold (relative to peak)
        ranges = silence.detect_nonsilent(
            audio, 
            min_silence_len=min_silence_len, 
            silence_thresh=silence_thresh
        )
        
        # Add a tiny buffer (padding) to start/end so it doesn't sound clipped
        padded_ranges = []
        for start, end in ranges:
            s = max(0, start - 200)
            e = min(len(audio), end + 300)
            padded_ranges.append((s, e))
            
        return padded_ranges, len(audio)
    except Exception as e:
        st.error(f"Error processing audio: {e}")
        return [], 0

def get_binary_file_downloader_html(bin_file, file_label='File'):
    with open(bin_file, 'rb') as f:
        data = f.read()
    bin_str = base64.b64encode(data).decode()
    href = f'<a href="data:application/octet-stream;base64,{bin_str}" download="{os.path.basename(bin_file)}">Download {file_label}</a>'
    return href

# --- UI ---
st.title("🎧 Dictation Buddy")

# 1. File Selector
if not os.path.exists(AUDIO_DIR):
    st.error(f"Folder '{AUDIO_DIR}' not found!")
    st.stop()

files = sorted([f for f in os.listdir(AUDIO_DIR) if f.endswith(('.mp3', '.mp4', '.m4a'))])
selected_file = st.sidebar.selectbox("Select Page/File", files)

if selected_file:
    file_path = os.path.join(AUDIO_DIR, selected_file)
    
    # 2. Tuning Parameters (Sidebar)
    st.sidebar.header("⚙️ Tuning")
    thresh = st.sidebar.slider("Silence Threshold (dB)", -60, -10, -40, help="Lower = treats more noise as silence")
    min_len = st.sidebar.slider("Min Pause Length (ms)", 100, 2000, 700, help="Shorter = splits more often")
    
    # 3. Process Audio
    with st.spinner("Analyzing audio sentences..."):
        sentence_ranges, total_duration = load_audio_ranges(file_path, min_len, thresh)
    
    # 4. Custom Audio Player (JavaScript)
    # We embed a custom HTML player that allows playing specific ranges
    
    # Convert audio to base64 for embedding (works for local hosting)
    with open(file_path, "rb") as f:
        audio_bytes = f.read()
        audio_b64 = base64.b64encode(audio_bytes).decode()
        ext = os.path.splitext(selected_file)[1].replace('.', '')
        mime = f"audio/{ext}" if ext != 'mp3' else 'audio/mpeg'

    # The HTML/JS Player
    player_html = f"""
    <audio id="main-audio" controls style="width: 100%;">
        <source src="data:{mime};base64,{audio_b64}" type="{mime}">
    </audio>
    
    <script>
        var audio = document.getElementById('main-audio');
        
        function playRange(startMs, endMs) {{
            audio.currentTime = startMs / 1000;
            audio.play();
            
            // Stop logic
            var stopTime = endMs / 1000;
            
            // Remove existing listener to avoid stacking
            if (window.checkTime) {{
                audio.removeEventListener('timeupdate', window.checkTime);
            }}
            
            window.checkTime = function() {{
                if (audio.currentTime >= stopTime) {{
                    audio.pause();
                    audio.removeEventListener('timeupdate', window.checkTime);
                }}
            }};
            
            audio.addEventListener('timeupdate', window.checkTime);
        }}
    </script>
    """
    
    st.markdown(player_html, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # 5. Sentence Grid
    st.subheader(f"Found {len(sentence_ranges)} Sentences")
    st.caption("Click a button to play just that sentence.")
    
    # CSS for buttons
    st.markdown("""
    <style>
    .stButton button { width: 100%; height: 60px; font-size: 18px; }
    </style>
    """, unsafe_allow_html=True)
    
    # Create a grid of buttons
    cols = st.columns(3)
    for i, (start, end) in enumerate(sentence_ranges):
        col = cols[i % 3]
        with col:
            # We use a trick: The button triggers a re-run, but we want JS to run.
            # Streamlit buttons are server-side. To control client-side audio seamlessly
            # is tricky. 
            # BEST APPROACH for simple dictation: Generate HTML buttons that call the JS directly.
            
            duration_sec = (end - start) / 1000
            
            btn_html = f"""
            <button onclick="parent.document.getElementById('main-audio').currentTime={start/1000}; parent.document.getElementById('main-audio').play(); 
                             var stop = {end/1000}; 
                             var aud = parent.document.getElementById('main-audio');
                             var func = function() {{ if(aud.currentTime >= stop) {{ aud.pause(); aud.removeEventListener('timeupdate', func); }} }};
                             aud.addEventListener('timeupdate', func);"
                    style="
                    background-color: #f0f2f6; border: 1px solid #d1d5db; 
                    border-radius: 8px; padding: 15px; margin: 5px; width: 100%;
                    cursor: pointer; font-size: 16px; font-weight: bold; color: #31333F;
                    transition: background 0.2s;">
                Sentence {i+1} <br>
                <span style="font-size: 12px; color: #666; font-weight: normal;">{duration_sec:.1f}s</span>
            </button>
            """
            st.components.v1.html(btn_html, height=80)


