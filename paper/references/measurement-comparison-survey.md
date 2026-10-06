# Survey of Mouse Dynamics Measurements and Profile Comparison Methods

**Author / Project:** Thesis: *Mouse Dynamics Behavioral Biometrics for Continuous Authentication*  
**Date:** 2026-08-28  
**Reference Deliverable:** Response to Adviser Log Entry [2026-08-28]  
**Source Literature:** [Annotated Bibliography](file:///c:/Users/tulal/thesis-mouse-biometrics/references/annotated-bibliography.md) (~46 compiled sources)

---

## 1. Overview & Survey Objective

In behavioral biometrics, mouse dynamics systems capture the idiosyncratic neuromuscular patterns individuals exhibit when interacting with a pointing device. To authenticate users continuously and silently, two core questions must be answered:
1. **What is measured?** (The exact features, physical signals, spatial curves, and learned representations extracted from raw mouse event streams).
2. **How are signatures and profiles compared?** (How enrolled user templates are structured, how candidate samples are evaluated against them, and the underlying mathematical mechanisms used to decide *"same user or not"*).

This survey directly fulfills the thesis adviser's request by providing:
- An **exhaustive catalog of all measurements** used across the literature, complete with their physical and mathematical descriptions.
- A **consolidated comparative analysis** of how researchers construct profiles and compare candidate signatures.
- A detailed contrast focusing specifically on the **operational differences in how decision boundaries and matching metrics operate** (e.g., fixed scalar thresholds vs. supervised separating hyperplanes vs. one-class anomaly envelopes vs. deep latent metric embeddings).
- A visually distinct specification of **our thesis's proposed closed-form geometric and Fréchet distance approach**, demonstrating how it fills the identified literature gaps.

---

## 2. Comprehensive Inventory: Full List of Measurements in Mouse Dynamics

Researchers extract features across several distinct physical, temporal, and mathematical domains. Below is the full inventory of measurements documented across the reviewed literature:

```
+--------------------------------------------------------------------------------------------------------------------+
|                                    TAXONOMY OF MOUSE DYNAMICS MEASUREMENTS                                         |
+----------------------+----------------------+-----------------------+-----------------------+----------------------+
| 1. Kinematic & Motion| 2. Temporal & Clicks | 3. Angles & Direction | 4. Curve Geometry     | 5. Learned / Deep    |
| - Velocity (v_x, v_y)| - Click duration     | - Movement angle (θ)  | - Chord deviation     | - 1D velocity filters|
| - Acceleration       | - Down-to-up latency | - Curvature angle (Δθ)| - Discrete curvature  | - 2D raster heatmaps |
| - Jerk (da/dt)       | - Double-click timing| - Angular velocity (ω)| - Straightness ratio  | - Recurrent states   |
| - Path displacement  | - Motor pause length | - Angular acceleration| - Convex hull / Area  | - Latent embeddings  |
+----------------------+----------------------+-----------------------+-----------------------+----------------------+
```

### 2.1 Kinematic & Motion Measurements
* **Instantaneous Tangential Velocity ($v$):** Displacement per unit time between consecutive discrete mouse coordinates: $v_t = \frac{\sqrt{(x_t - x_{t-1})^2 + (y_t - y_{t-1})^2}}{t_t - t_{t-1}}$.
* **Directional Velocities ($v_x, v_y$):** Independent horizontal and vertical velocity components: $v_{x,t} = \frac{x_t - x_{t-1}}{\Delta t}$ and $v_{y,t} = \frac{y_t - y_{t-1}}{\Delta t}$. Translation-invariant representation of hand movement direction and speed.
* **Instantaneous Acceleration ($a$):** Rate of change of velocity over time: $a_t = \frac{v_t - v_{t-1}}{\Delta t}$. Reflects ballistic force and neuromuscular initiation/braking.
* **Directional Acceleration ($a_x, a_y$):** Coordinate-specific acceleration components tracking distinct motor axis control.
* **Jerk ($j$):** The first derivative of acceleration (third derivative of position) with respect to time: $j_t = \frac{a_t - a_{t-1}}{\Delta t}$. Measures the smoothness and tremor of motor control.
* **Statistical Kinematic Moments:** Aggregations across an action or window, including the mean, standard deviation, variance, skewness, kurtosis, minimum, and maximum of velocity, acceleration, and jerk.

### 2.2 Temporal, Clickstream, & Event-Interval Measurements
* **Click Down-to-Up Duration (Dwell Time):** Elapsed time between `MouseButtonDown` and `MouseButtonUp` events for a single click. Reflects finger press mechanics and tactile release speed.
* **Click-to-Click Latency (Flight Time):** Elapsed time between the release of one click and the depression of the subsequent click.
* **Double-Click Interval:** Elapsed time between two consecutive clicks occurring within a rapid predefined system threshold.
* **Motor Pause Duration & Frequency:** Duration and occurrence rate of zero-velocity or near-zero displacement episodes ($v < \epsilon$) during continuous movement. Differentiates cognitive planning pauses from motor hesitation.
* **Action Elapsed Time:** Total duration required to execute a discrete action (e.g., Point-and-Click, Drag-and-Drop, or Pure Mouse Movement).
* **Action Type Distribution / Frequency:** Relative proportions of point-and-clicks, drags, scrolls, and idle pauses per unit time.

### 2.3 Angular & Directional Measurements
* **Movement Direction Angle ($\theta$):** Direction of motion relative to the horizontal axis: $\theta_t = \text{atan2}(y_t - y_{t-1}, x_t - x_{t-1}) \in [-\pi, \pi]$.
* **Angle of Curvature / Angular Shift ($\Delta\theta$):** Angular difference between two consecutive motion vectors: $\Delta\theta_t = \theta_t - \theta_{t-1}$. Measures localized path turning and trajectory deflection.
* **Angular Velocity ($\omega$):** Rate of angular directional change per unit time: $\omega_t = \frac{\Delta\theta_t}{\Delta t}$.
* **Angular Acceleration ($\alpha$):** Rate of change of angular velocity: $\alpha_t = \frac{\omega_t - \omega_{t-1}}{\Delta t}$.
* **Directional Histograms:** 8-direction or 16-direction spatial histograms binning cumulative travel distance or frequency across distinct compass trajectories.

### 2.4 Classical & Differential Geometric Curve Measurements
* **Straightness Ratio / Efficiency ($S$):** Ratio of net direct Euclidean displacement to cumulative trajectory path length: $S = \frac{\sqrt{(x_N - x_0)^2 + (y_N - y_0)^2}}{\sum_{i=1}^N \sqrt{(x_i - x_{i-1})^2 + (y_i - y_{i-1})^2}} \in [0, 1]$.
* **Chord Deviation ($d_\perp$):** Orthogonal distance from intermediate trajectory points to the linear chord connecting stroke origin $(x_0, y_0)$ to destination $(x_N, y_N)$. Measures lateral drift and path bow.
* **Inflection Point Count:** Number of sign changes in the trajectory's second spatial derivative, counting path oscillations or corrective s-curves.
* **Discrete Menger Curvature ($\kappa$):** Reciprocal radius of the circumcircle passing through three consecutive discrete trajectory points $p_i, p_j, p_k$: $\kappa = \frac{4 \cdot \text{Area}(\triangle p_i p_j p_k)}{a \cdot b \cdot c}$.
* **Area Under the Curve (AUC) & Spatial Integral:** Area enclosed between the actual mouse path and the direct linear chord.
* **Convex Hull Metrics:** Area, perimeter, and bounding polygon vertices of the minimum convex set containing all points in a mouse stroke.
* **Spatial Invariant Moments:** Normalized geometric moments of trajectory curves providing translation-, rotation-, and scale-invariance.
* **Rough Path Signatures:** Truncated tensor series capturing the non-commutative geometric path integrals and temporal ordering of coordinate curves.
* **Optimal-Control Motor Residuals:** Differences between observed mouse trajectories and theoretical minimum-jerk or optimal-control kinematic models.

### 2.5 Frequency-Domain & Spectral Measurements
* **Lomb-Scargle Spectral Density:** Frequency-domain power spectral density computed across unevenly sampled coordinate streams, capturing neuromuscular tremor frequencies (typically 2–12 Hz).
* **Spectral Energy Distribution:** Cumulative power concentrated across low-, medium-, and high-frequency motion bands.

### 2.6 Deep & Learned Representations
* **1D Temporal Convolutional Feature Maps:** Hierarchical feature vectors extracted by 1D-CNN kernels sweeping across directional velocity sequences.
* **2D Spatial Raster Trajectory Images:** Pixel renderings (RGB/grayscale) where trajectory paths, speed, and click events are drawn as lines/heatmaps for 2D-CNN processing.
* **Recurrent Hidden State Vectors:** Latent internal memory states generated by LSTM/GRU layers processing continuous coordinate sequences over time.
* **Latent Metric Space Embeddings:** Low-dimensional dense embeddings produced by Siamese, Contrastive, or Fully Convolutional Networks where distance correlates directly with identity similarity.

### 2.7 Sensor-Augmented & Multimodal Measurements
* **Grip Pressure Distribution:** Real-time force readings (in Newtons or millivolts) captured from 5-point resistive sensors embedded in mouse chassis.
* **Wearable Wrist Inertial Dynamics:** 3-axis acceleration and angular rate captured from smartwatch sensors synchronized with mouse clicks.

---

## 3. How Researchers Construct Profiles and Compare Signatures

To evaluate authenticity, systems build a stored representation (the *profile* or *template*) from enrollment data and use a matching algorithm to compare newly observed candidate samples against that profile.

```
+--------------------------------------------------------------------------------------------------------------------+
|                                    PROFILE CONSTRUCTION & COMPARISON SPECTRUM                                      |
+-------------------------+-------------------------+-------------------------+--------------------------------------+
| Paradigm                | Profile Representation  | Comparison Operation    | Operational Decision Rule            |
+-------------------------+-------------------------+-------------------------+--------------------------------------+
| 1. Distance Metric      | Centroid vector (μ) &   | Euclidean / Manhattan / | Accept if D(x, μ) < θ;               |
|    Matching             | Covariance matrix (Σ)   | Mahalanobis distance    | Reject if distance exceeds threshold |
+-------------------------+-------------------------+-------------------------+--------------------------------------+
| 2. Supervised           | Support vectors /       | Dot product / tree path | Accept if f(x) > 0 (genuine side);   |
|    Classification       | Decision forest trees   | evaluations             | Reject if f(x) < 0 (impostor side)   |
+-------------------------+-------------------------+-------------------------+--------------------------------------+
| 3. One-Class / Anomaly  | Support boundary /      | Distance to boundary /  | Accept if score > τ (within cluster);|
|    Detection            | Isolation tree depths   | Average isolation depth | Reject if outlier score is flagged   |
+-------------------------+-------------------------+-------------------------+--------------------------------------+
| 4. Deep Metric          | Latent vector cluster   | Cosine / Euclidean      | Accept if Sim(e_x, e_ref) > threshold|
|    Embeddings           | in embedding space      | distance in latent space| in shared metric projection space    |
+-------------------------+-------------------------+-------------------------+--------------------------------------+
| 5. Continuous Curve     | Baseline discrete curve | Discrete Fréchet        | Compute exact alignment cost; feed   |
|    Morphometry (Ours)   | geometric distributions | distance (δ_F)          | into per-action dynamic trust score  |
+-------------------------+-------------------------+-------------------------+--------------------------------------+
```

### Detailed Operational Differences Across Paradigms

1. **Distance-Based Centroid Profiles:**  
   * **Profile Construction:** A user's enrollment data is summarized into an average feature vector (centroid $\mu$) and feature-variance vector $\sigma$ (or covariance matrix $\Sigma$).
   * **Comparison Mechanism:** When a new action is logged, its feature vector $x$ is compared against $\mu$. The system computes $D(x, \mu) = \sqrt{(x - \mu)^T \Sigma^{-1} (x - \mu)}$ (Mahalanobis) or $\sum |x_i - \mu_i|$ (Manhattan).
   * **Decision:** If $D(x, \mu) \le \theta$, the action is accepted; if $D(x, \mu) > \theta$, it is flagged as an impostor.
   * **Core Limitation:** Treats complex multi-modal behavior as a single unimodal distribution; high sensitivity to outliers.

2. **Supervised Classification Profiles (SVM, Random Forest, k-NN):**  
   * **Profile Construction:** The system pools genuine user feature vectors (Class +1) with negative/impostor vectors collected from other users or synthetic generators (Class -1). It fits a maximal-margin hyperplane ($w \cdot \phi(x) + b = 0$) or an ensemble of orthogonal decision splits.
   * **Comparison Mechanism:** The candidate vector $x$ is evaluated directly against the learned boundary: $f(x) = \text{sign}(w \cdot \phi(x) + b)$.
   * **Decision:** Rejection occurs if the candidate lands on the negative side of the separating boundary.
   * **Core Limitation:** Requires negative training data (unrealistic in closed enrollment) and assumes the background impostor cohort accurately represents all possible future attackers.

3. **One-Class & Outlier Detection Profiles (One-Class SVM, Isolation Forest):**  
   * **Profile Construction:** Trained exclusively on genuine user samples without negative data. One-Class SVM maps genuine data into feature space and wraps a minimal hypersphere or support envelope around them. Isolation Forests recursively partition feature space, observing that normal points require many splits to isolate.
   * **Comparison Mechanism:** Candidate vectors are tested against the support boundary or scored by average tree path length: $s(x, n) = 2^{-\frac{E(h(x))}{c(n)}}$.
   * **Decision:** Actions with path lengths shorter than threshold (or lying outside the OC-SVM support) are flagged as anomalies.
   * **Core Limitation:** Highly susceptible to false rejections when genuine users experience fatigue, posture shifts, or task changes.

4. **Deep Metric Learning Profiles (Siamese, Contrastive Embeddings):**  
   * **Profile Construction:** A deep neural network is trained across multiple users using contrastive or triplet loss to map raw strokes into a shared latent metric space. The enrolled user's profile is stored as a cluster of latent embedding vectors $e_{\text{ref}} = \Phi(\text{strokes})$.
   * **Comparison Mechanism:** Candidate stroke $x$ is passed through the network to generate embedding $e_x = \Phi(x)$, and the cosine distance $d_{\cos}(e_x, e_{\text{ref}}) = 1 - \frac{e_x \cdot e_{\text{ref}}}{\|e_x\| \|e_{\text{ref}}\|}$ is computed.
   * **Decision:** If cosine distance is below threshold, identity is confirmed.
   * **Core Limitation:** The latent space is uninterpretable; impossible to verify which physical geometric deviation caused a rejection.

5. **Elastic Sequence Matching Profiles (Dynamic Time Warping - DTW):**  
   * **Profile Construction:** Stores a set of reference trajectory coordinate sequences $R = \{(x_1, y_1), \dots, (x_M, y_M)\}$.
   * **Comparison Mechanism:** Evaluates a candidate trajectory $C$ by building an $N \times M$ distance matrix and finding the minimum-cost warping path that aligns the indices of $C$ and $R$ under temporal stretching/compression constraints.
   * **Decision:** Rejects if minimal alignment cost exceeds threshold.
   * **Core Limitation:** Unconstrained time-warping can allow artificial distortion of velocity profiles to force an alignment.

---

## 4. Consolidated Literature Survey: Measurements vs. Comparison Methods

The following consolidated table deduplicates the literature by pairing distinct measurement representations with profile comparison algorithms, citing source papers in parentheses:

| What's Measured | Description | Comparison Method Used | Key Difference From Other Approaches (Decision Mechanism) |
| :--- | :--- | :--- | :--- |
| **Kinematic Summary Statistics & Clickstream Metrics** | Windowed statistical aggregations: mean, max, and standard deviation of velocity, acceleration, jerk, angular velocity, movement distance, click duration, and button release latencies. | **Supervised Ensemble Classifiers & Decision Trees** *(Random Forest, Decision Tree, k-Nearest Neighbors)*<br><br>*(Continuous Authentication Using Mouse Clickstream Data Analysis; From Clicks to Security)* | **Multi-Feature Orthogonal Partitioning:** Splits high-dimensional statistical vectors using decision trees or local neighborhood voting. Unlike single-threshold distance models, it captures complex non-linear combinations of summary metrics, but relies on supervised negative samples and discards spatial path trajectory details. |
| **Kinematic & Directional Feature Vectors** | Comprehensive kinematic profiles including movement direction histograms, trajectory curvature approximations, tangential velocity, and acceleration profiles. | **Support Vector Machines (SVM) with RBF/Linear Kernels**<br><br>*(Phase 2 Classical Literature; MFCA Mouse Module)* | **Maximal-Margin Hyperplane Boundary:** Projects handcrafted kinematic vectors into a kernel space to find the optimal separating hyperplane between genuine user samples and background impostor cohorts. Authentication requires offline negative training data and assumes impostor dynamics are representative. |
| **Time-Series Kinematic & Autoregressive Coefficients** | Autoregressive (AR) model parameters modeling horizontal ($x$) and vertical ($y$) coordinate transitions, velocity decay, and interaction speeds. | **Parametric Vector Distance Metrics** *(Euclidean, Manhattan, and Mahalanobis Distance)*<br><br>*(Memory Game Study; Early Feasibility Studies)* | **Centroid Proximity Thresholding:** Computes the scalar geometric distance between a candidate feature vector and the enrolled user's mean profile. Mahalanobis distance incorporates feature covariance, whereas Euclidean/Manhattan treat dimensions independently. Highly sensitive to dimensional scaling and lacks adaptability to temporal drift. |
| **Windowed Kinematic Aggregates** | Aggregated action distributions (speed distributions, pause frequencies, drag-vs-move ratios) collected over continuous sliding windows without prior user enrollment data. | **One-Class Support Vector Machine (OC-SVM)**<br><br>*(Secure System of Continuous User Authentication Using Mouse Dynamics)* | **Single-Class Support Bounding:** Learns a tight boundary encompassing the target user's feature distribution in kernel space without needing impostor training data. Evaluates whether candidate vectors lie inside or outside the support region, though prone to high false-rejection rates when behavior naturally varies. |
| **Frequency-Domain Spectral Dynamics** | Spectral energy distributions, frequency peaks, and cadence extracted from mouse coordinates using Lomb-Scargle periodograms to handle unevenly sampled trajectory points. | **Ensemble Probability Scoring & Time-Domain Legality Aggregation**<br><br>*(Mitigating Insider Threat by Profiling Users Based on Mouse Usage Pattern)* | **Spectral Regularity & Confidence Accumulation:** Translates frequency dynamics into an instantaneous "legality score" per action, which is aggregated across sliding windows into a session-level probability. Contrasts with spatial curve matching by assessing neuromuscular rhythm rather than path geometry. |
| **Point-by-Point Angle & Directional Metrics** | Local angle-based geometric metrics computed across consecutive point triplets: movement direction angle $\theta$, angle of curvature $\Delta\theta$, angular velocity $\omega$, and angular curvature distance. | **Support Vector Machines (SVM)**<br><br>*(Ahmed et al., 2016; Shen et al., 2013)* | **Local Directional Sequence Classification:** Classifies angle-transition distributions using a learned boundary. Focuses on fine-grained directional shifts rather than global kinematics, making it translation-invariant, but computes curvature as discrete angular differences rather than formal continuous geometry. |
| **Parametric Curve-Fitting & Autoregressive Trajectory Profiles** | Polynomial or spline curve approximations fitted to mouse movement trajectories, extracting polynomial coefficients, inflection points, and AR residual errors. | **Curve Parameter Matching & AR Residual Thresholding**<br><br>*(Tan, Binder, & Boshmaf; Memory Game Study)* | **Model-Fitting Residual Evaluation:** Fits an explicit mathematical curve function to the trajectory and evaluates how closely observed points follow the fitted model. Compares fitted parameter vectors against enrollment profiles rather than directly measuring raw differential geometry. |
| **Classical Spatial Curve Invariants (9 Schulz Descriptors)** | Nine normalized geometric features per movement curve: straightness ratio, curve length, maximum deviation, inflection count, center-of-gravity displacement, and rotation/scale-invariant spatial moments. | **Back-Propagation Neural Networks (BPNN / Multi-Layer Perceptrons)**<br><br>*(Schulz, 2006; Dynamic User Authentication Based on Mouse Movement Curves)* | **Non-Linear Invariant Vector Classification:** Feeds normalized, scale- and translation-invariant geometric descriptors through a multi-layer feedforward network. The network learns non-linear combinations of curve descriptors, but requires large sample batches (e.g., 300 curves) for stable convergence. |
| **Differential-Geometric Cursor Descriptors & Motor-Control Residuals** | Three mathematically grounded feature families: rough path signatures (capturing sequence order and path area), discrete differential curvature/torsion, and optimal-control motor-command residuals. | **One-Class Mahalanobis Distance / Anomaly Detector**<br><br>*(Mathematical Feature Representations of Mouse Dynamics — JPIT 2024)* | **Covariance-Normalized Anomaly Scoring:** Uses differential geometry and motor-control theory to construct a low-dimensional descriptor bank (e.g., 7–23 features), then scores candidates via Mahalanobis distance against the user's enrollment covariance matrix. Eliminates the need for impostor training data while maintaining mathematical interpretability. |
| **Global Trajectory Summaries & Spatial Integrals** | Macroscopic spatial envelope descriptors: Area Under the Curve (AUC), maximum chord deviation, convex hull boundaries, and Entropy of Motion (EMOT) distinguishing rapid ballistic motion from motor pauses. | **Heuristic Distance Thresholding & Entropy Density Estimation**<br><br>*(EMOT Study; Descriptive Geometric Approach Surveys)* | **Gross Spatial Envelope Comparison:** Checks whether a candidate movement path falls within a scalar spatial envelope or matches baseline entropy distributions. Often sensitive to trajectory noise and motor pauses, and lacks point-by-point spatial alignment. |
| **Whole-Trajectory Discrete Path Sequences** | Ordered sequences of raw discrete coordinates $(x_t, y_t)$ capturing full spatial-temporal movement trajectories without loss of intermediate points. | **Dynamic Time Warping (DTW) & Trajectory Clustering**<br><br>*(ReMouse Dataset Study)* | **Non-Linear Temporal Alignment Distance:** Warps the time axis to find the minimal Euclidean distance alignment between candidate and template strokes of different speeds and lengths. Directly measures curve-to-curve dissimilarity without fixed feature vectors, but can allow unconstrained temporal warping that distorts velocity profiles. |
| **1D Kinematic Sequences (Velocity Streams)** | Raw temporal sequences of translation-invariant directional velocities ($v_x = \Delta x/\Delta t$, $v_y = \Delta y/\Delta t$) sampled across continuous mouse strokes. | **1D Convolutional Neural Networks (1D-CNN)**<br><br>*(Ausilio et al., 2020; Comprehensive Study on Deep Neural Networks)* | **Hierarchical Temporal Filter Optimization:** Applies 1D convolutional kernels directly across velocity streams to learn discriminative temporal motion patterns end-to-end. Bypasses manual feature extraction, but functions as a black box with limited geometric explainability. |
| **Rendered 2D Trajectory Images & Spatial Heatmaps** | Mouse movement paths, click locations, and drag operations rendered into 2D raster images or spatial heatmaps (e.g., RGB composite images encoding movement type). | **2D Convolutional Neural Networks (VGG16, ResNet) with Grad-CAM Explainability**<br><br>*(Mouse Auth Without Temporal Aspect; Explainable DL with VGG16)* | **Visual Shape Pattern Recognition:** Treats mouse trajectories as 2D spatial drawings, applying standard computer vision convolutions to recognize stroke shapes and spatial curvature. Discards fine-grained temporal timestamps in favor of purely visual spatial geometry; explainability is retrieved via Grad-CAM activation maps. |
| **Sequential Recurrent Trajectory Streams** | Variable-length sequences of raw mouse coordinates, timestamps, and instantaneous kinematic states. | **Recurrent Neural Networks (LSTM, sLSTM, GRU, Hybrid CNN-RNN)**<br><br>*(From Clicks to Security; Comprehensive Study on Deep Neural Networks)* | **Recurrent State Tracking & Sequence Memory:** Passes sequential trajectory steps through recurrent memory cells to capture long-range temporal dependencies and neuromuscular habits across actions. High computational complexity during continuous inference. |
| **Hybrid Spatiotemporal Convolutions** | Spatiotemporal representation combining spatial convolution filters (MixConv) with recurrent temporal modeling (sLSTM) over multi-channel trajectory inputs. | **User-Specific Isolation Forests**<br><br>*(User Identity Authentication via Spatiotemporal Mouse Dynamics Modeling)* | **Deep Spatiotemporal Outlier Isolation:** Transforms raw trajectories through hybrid deep layers into rich feature vectors, then evaluates authenticity using personalized Isolation Forests. Anomaly scores are determined by the average path length required to isolate a sample on random feature splits. |
| **Lightweight Convolutional Embeddings with Synthetic Impostors** | Compact convolutional architectures (e.g., EfficientNet variants) extracting localized temporal-spatial feature representations from short interaction windows (e.g., 50 events). | **Generative Adversarial Multi-Class Classification (CGAN + Softmax)**<br><br>*(User Authentication Based on Mouse Dynamics Using an Efficient-Net Model)* | **Synthetic Impostor Boundary Regularization:** Trains a Conditional GAN to generate synthetic "Unknown/Impostor" feature profiles, converting open-set continuous authentication into a balanced, closed-set multi-class classification problem with high computational throughput. |
| **Deep Metric Embeddings (Metric Learning)** | Deep neural networks (Siamese or Contrastive architectures) mapping variable-length mouse trajectories into a shared latent metric space. | **Latent Space Metric Distance (Cosine / Euclidean Similarity Matching)**<br><br>*(User Authentication and Identity Inconsistency Detection via Mouse-Trajectory Similarity)* | **Latent Projection Proximity:** Projects candidate trajectories into a low-dimensional embedding space where samples from the same user have small angular/Euclidean distance and samples from different users are pushed far apart. Requires only a single global network for all users rather than training per-user classifiers. |
| **Raw Discrete Trajectory Streams** | Unprocessed sequences of $(x, y, t)$ coordinates gathered across heterogeneous hardware and varying screen resolutions. | **Fully Convolutional Networks (FCN) + One-Class SVM**<br><br>*(SapiMouse / Antal & Egyed-Zsigmond)* | **Deep Unsupervised Feature Extraction + Support Envelope:** FCN layers automatically extract non-linear representations from raw sequences without manual feature engineering, which are then fed into per-user One-Class SVMs to define genuine behavioral boundaries. |
| **Sensor-Augmented Grip Pressure & Wearable Dynamics** | Multi-modal fusion combining mouse movement coordinates with 5-point resistive grip pressure sensors on the mouse body or smartwatch inertial sensors (accelerometer/gyroscope). | **Hierarchical Domain Matching & Random Forest Sequential Sampling**<br><br>*(Fine-Grained Continuous Auth via Grip Pressure; Hand in Motion; Wrist in Motion)* | **Multi-Modal Physical Constraint Verification:** Supplements digital mouse dynamics with direct physiological measurements (grip force, wrist orientation). Decisions are made via hierarchical domain classification or Sequential Probability Ratio Tests (SPRT), achieving rapid verification at the cost of specialized hardware requirements. |

---

## 5. Synthesis of Methodological Differences Across Approaches

| Analytical Dimension | Classical Statistical / ML | Deep Learning & Embeddings | Proposed Geometric Morphometry |
| :--- | :--- | :--- | :--- |
| **Representation Space** | Fixed-size scalar feature vectors ($d \in [10, 100]$) | Latent dense projection vectors or weights | Continuous discrete curves & closed-form descriptors |
| **Temporal Granularity** | Aggregated over 20–300 clicks or 1–5 min windows | 15–60 second windows or fixed token lengths | Single action / stroke ($<1.0$ second) |
| **Impostor Requirement** | Yes (supervised) or No (One-Class SVM) | Yes (contrastive/triplet pairs or CGAN) | No (enrolled genuine baseline only) |
| **Geometric Precision** | Approximate angle steps or fitted polynomial models | Implicit/unobserved spatial convolutions | Exact differential geometry & point-ordered Fréchet alignment |
| **Decision Explainability** | Moderate (feature importance ranking) | Low (black-box neural activations) | High (direct mathematical attribution to specific geometric anomalies) |
| **Computational Footprint** | Very low ($<1$ ms) | High (GPU/tensor acceleration required) | Low ($O(MN)$ dynamic programming per stroke) |

---

## 6. Our Proposed Approach: Closed-Form Geometry & Fréchet Continuous Authentication

To overcome the dichotomy between simplified geometric approximations and uninterpretable deep neural embeddings, our thesis introduces a closed-form geometric framework evaluated via continuous curve morphometry:

| What's Measured | Description & Mathematical Safeguards | Comparison Method Used | Key Difference & Decision Mechanism |
| :--- | :--- | :--- | :--- |
| **Multi-Scale Closed-Form Local & Global Geometric Descriptors**<br><br>*(Chord Deviation, Discrete Menger Curvature, Straightness Ratio, and Convex Hull)* | • **Chord Deviation ($d_\perp$):** Perpendicular distance from each intermediate trajectory point to the stroke baseline chord connecting start $(x_0, y_0)$ and end $(x_N, y_N)$. Safeguarded with an $\epsilon$-threshold against zero-length baselines.<br><br>• **Discrete Menger Curvature ($\kappa$):** Exact circumcircle curvature computed over consecutive point triplets $p_i, p_j, p_k$:<br>$$\kappa(p_i, p_j, p_k) = \frac{4 \cdot \text{Area}(\triangle p_i p_j p_k)}{\|p_i - p_j\| \cdot \|p_j - p_k\| \cdot \|p_k - p_i\|}$$<br>Safeguarded with explicit handling for collinear points ($\kappa = 0$) and division-by-zero clamping for overlapping points.<br><br>• **Straightness Ratio ($S$):** Ratio of net Euclidean displacement to total cumulative path length:<br>$$S = \frac{\sqrt{(x_N - x_0)^2 + (y_N - y_0)^2}}{\sum_{i=1}^{N} \sqrt{(x_i - x_{i-1})^2 + (y_i - y_{i-1})^2}} \in [0, 1]$$<br>• **Convex Hull (Supplementary Global):** Minimum bounding 2D polygon enclosing the trajectory, quantifying gross spatial dispersion and motor overshoot, safeguarded against degenerate collinear hulls. | **Discrete Fréchet Distance ($\delta_F$)** paired with a **Dynamic Per-Action Trust Accumulator** | **True Curve-to-Curve Morphometry with Traceable Attribution:**<br><br>1. **Point-Ordering Preservation:** Unlike standard Hausdorff distance, Euclidean vector comparison, or area summaries (which discard sequence flow), Fréchet distance enforces strict monotonic ordering along the curve ("dog-walking distance").<br><br>2. **Closed-Form Interpretability:** Authentication does not rely on opaque neural weights. Every trust reduction is directly attributable to an exact mathematical distortion (e.g., abnormal local Menger curvature fluctuations or anomalous baseline chord deviations).<br><br>3. **Continuous Per-Action Scoring:** Instead of requiring windowed aggregation over dozens of interactions, every discrete stroke immediately produces an exact Fréchet alignment cost against enrolled profiles, driving a decaying/recovering continuous trust score. |
