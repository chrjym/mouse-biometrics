# Model Simulation Plan: Mouse Dynamics Continuous Authentication

**Thesis:** Measuring Behavioral Fingerprints of Users in Mouse Trajectories for Continuous Authentication  
**Segment:** Simulation & Experimental Verification  
**Status:** Planning Stage  
**Target:** Conceptualization, Requirements, Architecture, and Evaluation Design  

---

## 1. Executive Summary & Objective

This document outlines the **simulation plan** for testing and evaluating the continuous authentication model. The simulation models an active workstation environment where raw, asynchronous mouse movements are continuously monitored to verify user identity in real time using short-signal geometric mannerisms.

The objective of this simulation is to answer two core research questions:
1. **Discriminative Feasibility:** Can closed-form geometric mannerisms extracted from sub-second short mouse signals reliably distinguish between genuine users and zero-effort impostors?
2. **Continuous Security:** How quickly (in elapsed seconds and count of actions) does the dynamic trust scoring engine detect an unauthorized session hijack without generating intrusive false alarms during legitimate work?

---

## 2. Core Simulation Architecture

The simulation environment models five sequential stages:

```
+-------------------------------------------------------------------------------------------------------------+
|                                    SIMULATION PIPELINE FLOW                                                 |
+-------------------+     +--------------------+     +---------------------+     +----------------------------+
| 1. Stream Replay  | ──► | 2. Preprocessing & | ──► | 3. Profile Matching | ──► | 4. Dynamic Continuous      |
|    & Attack Splicer     |    Mannerism Engine|     |    (Fréchet Metric) |     |    Trust State Evaluation  |
+-------------------+     +--------------------+     +---------------------+     +----------------------------+
         │                                                                                      │
         ▼                                                                                      ▼
 [ Genuine Stream ]                                                                     [ Decision Output ]
 [ Impostor Stream ]                                                                    - Verified Active
 [ Hijack at t_switch ]                                                                 - Suspicious Drift
                                                                                        - Security Lockout
```

### Stage 1: Stream Replayer & Attack Splicer
- **Function:** Ingests benchmark datasets and replays timestamped mouse event tuples `(x, y, t, event_type, button_state)` preserving natural temporal intervals ($\Delta t$).
- **Attack Injection Protocol:**
  - Plays genuine user events to establish an active, verified session.
  - At a predefined or random timestamp $t_{\text{switch}}$, cleanly splices in an impostor user stream.
  - Tracks ground-truth labels (`GENUINE` vs. `IMPOSTOR`) for automated metric computation.

### Stage 2: Short-Signal Segmentation & Mannerism Extraction
- **Segmentation Boundaries:**
  - *Clickstream Trigger:* Slices trajectory between `MouseUp` and subsequent `MouseDown`.
  - *Motor Pause Trigger:* Slices trajectory if instantaneous velocity drops below $\epsilon_v$ for $\Delta t \ge \tau_{\text{pause}}$ ($150\text{--}250\text{ ms}$).
  - *Length & Duration Filters:* Enforces $N \ge 5$ points, displacement $\ge 10\text{ px}$, and duration $T \le 1.5\text{ s}$.
- **Arc-Length Resampling:** Uniformly samples $K = 32$ equidistant points along cumulative path length.
- **Closed-Form Geometric Mannerisms:**
  - *Discrete Menger Curvature ($\kappa$):* Circumcircle radius over point triplets (measuring corner-rounding sharpness) with collinearity safeguards.
  - *Chord Deviation Profile ($d_\perp$):* Orthogonal distance from baseline chord (measuring lateral motor drift) with zero-length chord safeguards.
  - *Straightness Ratio ($S$):* Ratio of net displacement to cumulative arc length.
  - *Convex Hull Envelope ($CH$):* Minimum enclosing polygon area and perimeter (quantifying terminal overshoot).

### Stage 3: Baseline Enrollment & Morphometric Matching
- **Profile Enrollment:** Stores reference baseline short signals for each user, clustered by directional octant and displacement magnitude.
- **Discrete Fréchet Distance ($\delta_F$):** Evaluates candidate short signals against enrolled templates using dynamic programming to guarantee strict forward temporal/point ordering along the curve.

### Stage 4: Continuous Dynamic Trust Scoring
- **Action Verification Score:**
  $$\Psi_k = \exp\left(-\frac{\delta_F(P_k, Q^*)^2}{2\sigma_F^2}\right) \in [0, 1]$$
- **Dynamic Memory Accumulator:**
  $$T_k = \min\left(1.0, \; \max\left(0.0, \; \lambda \cdot T_{k-1} + (1 - \lambda) \cdot \Psi_k\right)\right)$$
  where $\lambda \in [0.85, 0.95]$ prevents erratic lockouts from isolated anomalies.
- **Tri-State Decision Boundaries:**
  - $T_k \ge \tau_{\text{safe}}$ ($0.70$): **Verified Genuine Active**.
  - $\tau_{\text{lock}} \le T_k < \tau_{\text{safe}}$: **Suspicious Drift** (passive monitoring / re-verification prompt).
  - $T_k < \tau_{\text{lock}}$ ($0.40$): **Impostor Lockout** (session terminated).

---

## 3. Simulation Requirements: What Is Needed

### A. Datasets Needed
1. **Balabit Mouse Dynamics Challenge Dataset (DFL):**
   - 10 users with dedicated training (clean, verified) and testing (mixed genuine + illegal impostor) sessions.
   - Primary benchmark for cross-comparison with published literature.
2. **SapiMouse Dataset (Antal et al.) or Chao Shen Dataset:**
   - Supplementary natural desktop interactions for robustness checks across tasks (browsing, text editing).

### B. Hardware & Environmental Assumptions
- Target screen resolution: Normalized to standard $1920 \times 1080$ virtual canvas.
- Mouse polling rates: Handled via spatial arc-length resampling ($K = 32$), ensuring hardware-invariant shape comparison.

### C. Evaluation Metrics Needed
1. **Biometric Discrimination Metrics:**
   - **False Acceptance Rate (FAR):** Percentage of impostor short signals classified as genuine.
   - **False Rejection Rate (FRR):** Percentage of genuine short signals falsely rejected.
   - **Equal Error Rate (EER):** The operational equilibrium point where $\text{FAR} = \text{FRR}$.
2. **Continuous Temporal Metrics (Session Level):**
   - **Time-to-Detection (TTD):** Elapsed wall-clock seconds from $t_{\text{switch}}$ until trust falls below $\tau_{\text{lock}}$.
   - **Average Actions to Detect (AAD):** Number of discrete short signals/actions executed by the impostor prior to lockout.
   - **False Lockout Rate per Hour:** Expected frequency of legitimate user interruption.

---

## 4. Phased Simulation Roadmap

| Phase | Milestone | Scope / Deliverable |
| :--- | :--- | :--- |
| **Phase 1** | **Dataset Ingestion & Prep** | Define standardized event schemas; format Balabit/DFL logs; verify normalization. |
| **Phase 2** | **Segmentation Calibration** | Tune pause threshold ($\tau_{\text{pause}}$) and minimum stroke length on real user data. |
| **Phase 3** | **Feature Sanity Validation** | Validate closed-form formulas against geometric edge cases (lines, circles, collinear paths). |
| **Phase 4** | **Baseline Profile Calibration** | Determine optimal template cluster sizes and directional partition bins. |
| **Phase 5** | **Attack Replay Experiments** | Run $N = 50$ randomized session-hijacking trials per user pair; log trust decay trajectories. |
| **Phase 6** | **Performance & Trade-Off Analysis** | Plot FAR/FRR trade-off curves; report final EER, TTD, and AAD for Chapter 4/5 of the thesis. |
