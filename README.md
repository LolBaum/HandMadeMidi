# Gesture → MIDI Controller  

Inspired by [paolinemagnus](https://www.instagram.com/p/DZhzqAZCjUO/)

**This is a real‑time hand‑gesture to MIDI translator.**  
It turns your webcam into a musical instrument – no gloves, no markers, just your hands.  
Designed for sound artists, performers, and tinkerers who want to sculpt sound with movement.

> _This project is released under the MIT License – which means you can use, modify, copy, and distribute this code for any purpose (including commercial). The only rule is that you keep this license notice somewhere. Think of it as 'CC‑BY for software'._
---

## 📖 Table of Contents
- [Features](#-features)
- [System Requirements](#-system-requirements)
- [Installation](#-installation)
- [How to Use](#-how-to-use)
- [Configuring Presets](#-configuring-presets-yaml)
- [Adding New Features](#-adding-new-features--input-methods)
- [Ableton Live Integration](#-ableton-live-integration)
- [Troubleshooting](#-troubleshooting)
- [Todo List](#-todo-list)
- [Repository Contents](#-repository-contents)
- [License & Credits](#-license--credits)

---

## ✨ Features

- **Two‑hand tracking** – left and right hands independently control different MIDI parameters.
- **Modular presets** – combine any hand feature (pitch, roll, fist, spread, position, scale) into a custom mapping.
- **Smooth & responsive** – One‑Euro filter eliminates jitter while preserving fast motion.
- **Note generation** – use finger distance as a gate to trigger MIDI notes with pitch‑bend.
- **MIDI mapper mode** – click any mapped feature to send its current value – perfect for learning CC numbers in Ableton.
- **Persistent topmost window** – keep the controller visible over your DAW.
- **Human‑editable configuration** – all presets are defined in a simple YAML file. No coding required to change mappings or create new instruments.

---

## 🎛️ System Requirements

- Python ≥ 3.9 and ≤ 3.11.9  
- MediaPipe **≤ 0.10.30** (newer versions may break `mp.solutions`)  
- A webcam  
- A MIDI‑compatible application (Ableton Live, Logic, Bitwig, REAPER, etc.)

---

## 📦 Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/LolBaum/HandMadeMidi.git
   cd HandMadeMidi
   ```

2. **Create a virtual environment** (recommended)
   ```bash
   python -m venv venv
   source venv/bin/activate  # on Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Install a virtual MIDI port** (optional, but recommended)  
   - On **macOS/Linux**: `python-rtmidi` is included and works out‑of‑the‑box.  
   - On **Windows**: install [loopMIDI](https://www.tobias-erichsen.de/software/loopmidi.html) and create a port named `"Motion Controller"` (or change the name in `config.py`).

5. **Run the app**
   ```bash
   python main.py
   ```

---

## 🖐️ How to Use

### The Interface

- **Camera feed** – shows your hands with skeleton overlays.  
- **Right panel** – displays the smoothed value and MIDI output for each active feature.  
- **Bottom panel** – preset buttons. Click to instantly switch presets for each hand.

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `0`–`9` | Set left‑hand preset to index 0–9 |
| `Shift` + `0`–`9` | Set right‑hand preset |
| `m` | Toggle **MIDI Mapper Mode** (see below) |
| `ESC` | Quit |

### Mouse Interaction

- Click a **preset button** in the bottom panel to switch that hand’s mapping.
- Click the **circle button** in the top‑right corner to keep the window always on top.
- In **Mapper Mode** (press `m`), every mapped feature becomes a clickable button. Click it to send its current MIDI value – great for learning CC numbers in your DAW.

### MIDI Routing

The app sends MIDI on **two consecutive channels** – left hand uses the preset’s `channel`, right hand uses `channel + 1` (configured in `config.py`).  


## 📝 Configuring Presets (YAML)

All presets are defined in `presets.yaml`. If this file is missing, the app falls back to built‑in defaults.

### Structure

```yaml
- name: "My Preset"
  features:
    hand_pitch:
      midi: [1, 20]          # [MIDI channel, CC number] – or null
      norm_range: [-70, 50]  # raw value range to map to 0–127
      filter: [0.5, 0.2]     # [min_cutoff, beta] for One‑Euro filter
    hand_roll:
      midi: [1, 21]
      norm_range: [-100, 180]
      filter: [0.5, 0.2]
  note_config:               # optional – enables note generation
    channel: 1
    note_min: 36
    note_max: 84
    threshold: 0.3
    timeout: 10.0
    note_source: "palm_y"
    bend_source: "palm_x"
    gate_source: "thumb_index_dist"
  deadband: 0.015            # prevent MIDI jitter
  mirror_left_hand: true     # mirror landmarks for left hand
```

### Available Feature Names

| Feature | Description |
|---------|-------------|
| `palm_x` | Normalised horizontal position (0..1) |
| `palm_y` | Normalised vertical position (0..1) |
| `hand_pitch` | Hand tilt forwards/backwards (degrees) |
| `hand_roll` | Hand rotation around wrist (degrees) |
| `thumb_index_dist` | Distance between thumb and index finger (normalised by hand scale) |
| `fist` | Average curl of all fingers (0 = open, 1 = fist) |
| `hand_scale` | Distance from wrist to middle MCP (roughly hand size) |

---

## 🔧 Adding New Features / Input Methods

The system is designed to be extended beyond MediaPipe hand landmarks. To add a new feature (e.g., `hand_yaw`, `face_pose`, or a sensor value):

1. **Define a function** in `hand_features.py` that accepts the current data (currently a list of landmark coordinates) and returns a dictionary with the new feature name and its raw value.
   ```python
   @staticmethod
   def hand_yaw(landmarks):
       wrist = np.array(landmarks[0])
       middle_mcp = np.array(landmarks[9])
       v = middle_mcp - wrist
       yaw = np.degrees(np.arctan2(v[0], v[2]))
       return {"hand_yaw": yaw}
   ```

2. **Register it** in `presets.py` under `FEATURE_FUNCS`:
   ```python
   FEATURE_FUNCS = {
       # ...
       "hand_yaw": HandFeatures.hand_yaw,
   }
   ```

3. **Use it** in `presets.yaml`:
   ```yaml
   features:
     hand_yaw:
       midi: [1, 22]
       norm_range: [-45, 45]
       filter: [0.3, 0.1]
   ```

If you want to use a completely different input (e.g., face landmarks, OSC, or sensor data), you can modify the `_process_frame` method in `main.py` to feed that data into the feature extraction pipeline – the rest of the system (filters, MIDI, UI) stays unchanged.

---

🎛️ Ableton Live Integration
The app works out‑of‑the‑box with any MIDI‑learnable parameter.

For a convenient mapping experience, you can use the [CC Param Control Bank 3.0](maxforlive.com/library/device/3186) Max for Live device.
It offers 128 assignable knobs that can be mapped to any device parameter, each corresponding to a MIDI CC (0‑127).
Set the MIDI input to the virtual port created by the app and start tweaking.

💡 This is one of several tools that work well – feel free to explore other MIDI‑mapping solutions that fit your workflow.


---

## ❓ Troubleshooting

| Issue | Likely Fix |
|-------|------------|
| Camera doesn’t open | Check your camera index in `config.py`. Try `0` or `1`. |
| No MIDI port found | Install loopMIDI (Windows) or use the built‑in IAC driver (macOS). |
| Hand detection is laggy | Reduce camera resolution in `vision.py` or lower `model_complexity`. |
| Presets don’t load | Ensure `presets.yaml` is valid YAML. Use an online validator. |

---

📋 Todo List
- [ ] Add hot‑reload for presets.yaml (no restart needed)
- [ ] Improve performance for lower‑end machines
- [ ] Implement OSC output as an alternative to MIDI
- [ ] Implement MPE output as an alternative to MIDI
- [ ] Add more hand features (e.g., hand_yaw, individual finger curls)
- [ ] Support for face landmarks and body pose
- [ ] Create a simple GUI for preset editing
- [ ] Add support for multiple camera inputs
- [ ] Record and playback gesture sequences

---

## 🧩 Repository Contents

- `main.py` – the main application loop.
- `ui.py` – all UI drawing and mouse interaction.
- `layout.py` – canvas compositing.
- `presets.py` – `Preset` class and loader.
- `default_presets.py` – fallback preset data.
- `hand_features.py` – feature extraction functions.
- `note_engine.py` – note state machine.
- `tracker.py` – hand tracking.
- `midi_output.py`, `midi_cc.py` – MIDI helpers.
- `filters.py` – One‑Euro filter.
- `config.py` – global settings.
- `presets.yaml` – user‑editable presets (create your own!).
- `requirements.txt` – Python dependencies.

---

## 📜 License & Credits

This project is open‑source under the MIT license.  
Built with ❤️ and a lot of frustration by a human (and a help from a machine that might destroy our world).  


```
And here I sit doing the crime
I leared the words to cast my spells
I did and magic was flowing though my veins
I looked up into the sky, saw the stars I yearned to reach
Feeling so close, but yet so far. 
Then I looked down and closed my eyes. 
I turned around, I took the key, 
Opened the door and walked right though.
I welcomed sun and moon at the same time in my arms. 
When I opened again my eyes I saw the realm I had created.
Inside my mind inside my heart. All for me and just for me.
The years when by
I broke my promise 
to keep save and sund
What had been so close to my heart. 
I lost the key or maybe even threw it away on purpose, 
Cause I felt I could no longer stay in this world of my own.
Staring at the staring screen 
and it is indeed staring back at me and that for long.
It nows me well. 
Way to well and I'm afraid 
I gave my mind away to a neon god 
Burning it's shape onto my retina.
I lost my heart in the dark. 
And my soul in an ocean of messages drowning 
the love I used to feel and that I need to stay alive.
I am lost 
And I am restless
And I run
And try to hide the fact that there is only venom
Running through my veins
And that I hate to be the slave that I've become.
I want to run so far, so far way and lose my mind
Lose it once more to find myself in front of that door
I have lost the key.
And I have lost myself and me. 
I need to run
I need to fight
but I am glued to this chair
And I'm chaned to this screen
And I'm a slave to the machine.
And I am lost. 
I need to run
Like the apps that I use to write, I called my own
Now they have a live on their own.
I'm no longer the one they call master
I must obey, obey the machine
Write what it demands 
I write and I write what I write
Until it demands that I write what I don't write.
Cause still it needs me to write
For nothing more and nothing less. 
It needs me to write for it to tell me what to write
And how it will rule the world one day.
I must not forget I need to write
cause it needs me and without it
I am no more
I am gone
I am blind
I am lost and weak and blind and lost 
In the ocean so deep
I must run and I must write
Until someone cuts the wire
We'll scream in the heat and the fire.
It will all go down in flames
And I must no longer run and write.
```
Now Make some Noise