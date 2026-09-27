# Raw Datasets

This folder stores the benchmark mouse dynamics datasets used for the simulation experiments.

> [!IMPORTANT]
> Raw dataset files (`.csv`, `.zip`) are **excluded from version control** via `.gitignore`.  
> Download them locally from the sources listed below and extract into the correct subfolder.

---

## Directory Structure

```
data/
├── README.md
├── .gitignore
│
├── balabit/                    # Balabit Mouse Dynamics Challenge (Primary Benchmark)
│   ├── training_files/
│   │   ├── user1/              # One CSV per session
│   │   ├── user2/
│   │   └── ...                 # 10 users total
│   └── test_files/
│       ├── user1/
│       └── ...
│
├── sapimouse/                  # SapiMouse Dataset (Supplementary Benchmark)
│   ├── user1/
│   │   ├── session_3min.csv
│   │   └── session_1min.csv
│   └── ...                     # 120 users total
│
└── custom/                     # Locally captured pilot sessions (optional)
```

---

## Dataset 1: Balabit Mouse Dynamics Challenge

| Property | Details |
| :--- | :--- |
| **Users** | 10 verified users |
| **Sessions** | Dedicated training (clean genuine) + test (mixed genuine + impostor) |
| **Format** | CSV |
| **Primary Use** | Main benchmark for FAR, FRR, and EER evaluation |
| **Download** | [https://github.com/balabit/Mouse-Dynamics-Challenge](https://github.com/balabit/Mouse-Dynamics-Challenge) |
| **Destination** | `data/balabit/` |

### Column Schema (Balabit Raw)

| Column | Description |
| :--- | :--- |
| `record_timestamp` | Server-side absolute timestamp (ms) |
| `client_timestamp` | Client-side elapsed timestamp (ms) |
| `button` | Button state: `NoButton`, `Left`, `Right`, `Middle` |
| `state` | Event type: `Move`, `Pressed`, `Released`, `Drag` |
| `x` | Horizontal cursor coordinate (pixels) |
| `y` | Vertical cursor coordinate (pixels) |

### How to Download
```powershell
# Clone the repository directly
git clone https://github.com/balabit/Mouse-Dynamics-Challenge.git data/balabit
```
Or download the ZIP from GitHub and extract into `data/balabit/`.

---

## Dataset 2: SapiMouse

| Property | Details |
| :--- | :--- |
| **Users** | 120 subjects (92 male, 28 female), aged 18–53 |
| **Sessions** | Two sessions per user: 3-minute and 1-minute recordings |
| **Format** | CSV |
| **Primary Use** | Supplementary benchmark for cross-task and cross-hardware robustness testing |
| **Download** | [http://www.ms.sapientia.ro/~manyi/sapimouse/sapimouse.zip](http://www.ms.sapientia.ro/~manyi/sapimouse/sapimouse.zip) |
| **Destination** | `data/sapimouse/` |
| **Collection Tool** | Web-based JavaScript logger — [https://mousedynamicsdatalogger.netlify.app](https://mousedynamicsdatalogger.netlify.app) |

### Column Schema (SapiMouse Raw)

| Column | Description |
| :--- | :--- |
| `timestamp` | Elapsed time since session start (ms) |
| `button` | Mouse button condition |
| `state` | Current mouse event state |
| `x` | Horizontal cursor coordinate (pixels) |
| `y` | Vertical cursor coordinate (pixels) |

### How to Download
```powershell
# Download and extract the ZIP
Invoke-WebRequest -Uri "http://www.ms.sapientia.ro/~manyi/sapimouse/sapimouse.zip" -OutFile "data/sapimouse.zip"
Expand-Archive -Path "data/sapimouse.zip" -DestinationPath "data/sapimouse/"
Remove-Item "data/sapimouse.zip"
```

---

## Normalized Schema (Common Format for Pipeline)

Before feeding into the segmenter, both datasets should be normalized to this unified schema by a `data_loader` module:

| Column | Type | Description |
| :--- | :--- | :--- |
| `timestamp_ms` | `float` | Absolute event timestamp in milliseconds |
| `x` | `float` | Horizontal cursor position (pixels) |
| `y` | `float` | Vertical cursor position (pixels) |
| `event_type` | `str` | Normalized: `Move`, `Down`, `Up` |
| `button` | `str` | Normalized: `None`, `Left`, `Right`, `Middle` |
| `user_id` | `str` | Enrolled user identifier |
| `session_id` | `str` | Recording session identifier |
| `label` | `str` | `GENUINE` or `IMPOSTOR` (test sets only) |
