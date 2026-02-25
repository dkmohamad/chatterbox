# Troubleshooting

## Audio

**"PortAudio library not found"**
```bash
sudo apt install libportaudio2 portaudio19-dev
```

**No audio devices found**
```bash
python -c "import sounddevice; print(sounddevice.query_devices())"
```
Check that your mic and speakers are connected and not muted.

## Wake Word

**Wake word not triggering**
- Lower the threshold in `config/chatterbox.toml`:
  ```toml
  [wake]
  threshold = 0.3
  ```
- Speak clearly and close to the mic
- Run with `--debug` to see detection scores
- Try a different wake word model (`alexa`, `hey_mycroft`)

## Turn-Taking

**Chatterboxcuts me off mid-sentence**
- Increase the silence timeout:
  ```toml
  [vad]
  silence_timeout_ms = 1200
  ```

**Chatterboxtakes too long to respond after I stop talking**
- Decrease the silence timeout:
  ```toml
  [vad]
  silence_timeout_ms = 500
  ```

## Speech-to-Text

**"whisper.cpp binary not found"**
- Run `./setup.sh` to build whisper.cpp from source
- Or update the path in `config/chatterbox.toml`:
  ```toml
  [stt]
  whisper_binary = "/full/path/to/whisper-cli"
  ```

**Transcription is slow**
- If built without CUDA, whisper runs on CPU. Rebuild with CUDA:
  ```bash
  cd vendor/whisper.cpp
  cmake -B build -DGGML_CUDA=ON
  cmake --build build --config Release -j$(nproc)
  ```

## LLM

**"Cannot connect to Ollama"**
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Start it
ollama serve

# Pull the model
ollama pull llama3.2:3b
```

**Responses are slow**
- Try a smaller model:
  ```toml
  [llm]
  model = "llama3.2:1b"
  ```

## TTS

**"Piper model not found"**
- Run `./setup.sh` to download the model
- Or update the path in `config/chatterbox.toml`

**Voice sounds wrong**
- Try a different piper voice. Browse models at https://rhasspy.github.io/piper-samples/
- Download both the `.onnx` and `.onnx.json` files
