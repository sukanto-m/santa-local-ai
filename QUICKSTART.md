# 🎅 Quick Start Guide

Get Santa Tracker running in **3 minutes**!

## Step 1: Install Ollama

**Mac:**
```bash
brew install ollama
```

**Linux:**
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

**Windows:**
Download from [ollama.ai](https://ollama.ai/download)

## Step 2: Get the Model

```bash
# This will take a few minutes (downloads ~2GB)
ollama pull llama3.2
```

## Step 3: Start Ollama

```bash
ollama serve
```

Leave this terminal running!

## Step 4: Run Santa Tracker

Open a **new terminal**:

```bash
# Navigate to the project
cd santa-tracker-local-ai

# Start the server
python3 server.py
```

## Step 5: Open in Browser

Go to: **http://localhost:8000/santa-tracker.html**

Click "Share My Location" and "Get a message from Santa"!

---

## Troubleshooting

**Error: "address already in use"**
- Ollama is already running! Just skip to Step 4.

**Error: "frosty connection"**
- Make sure both terminals are still running
- Try refreshing the browser
- Check `http://localhost:11434/api/tags` returns something

**Location not working?**
- Make sure you clicked "Allow" when asked for location
- Try using Chrome or Firefox
- Check you're using `http://localhost:8000` not `file://`

---

🎄 **That's it! Enjoy tracking Santa!** 🎅
