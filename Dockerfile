# Use a lightweight Python base image
# python:3.9-slim is compatible with Raspberry Pi (ARM)
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
# ffmpeg is required for pydub audio processing
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install Python libraries
# We do this before copying code to leverage Docker cache
RUN pip install --no-cache-dir streamlit pydub

# Copy the application code
COPY dictation_buddy.py .

# Create the audio directory (so it exists even if empty)
RUN mkdir -p audio_files

# Expose Streamlit's default port
EXPOSE 8501

# Run the application
CMD ["streamlit", "run", "dictation_buddy.py", "--server.port=8501", "--server.address=0.0.0.0", "--logger.level=debug", "--browser.gatherUsageStats=false"]

