Access control perimeters fail the moment an authenticated session begins. While conventional security baselines—namely alphanumeric passwords, hardware security keys, and static physiological scans such as fingerprint or facial recognition—effectively regulate the point of entry, they remain fundamentally blind once access is granted [1]. The host operating system assumes that the legitimate user remains at the console indefinitely. This one-time verification baseline creates a dangerous post-login vulnerability. Should an authorized worker leave a workstation unattended, or should an adversary execute commands through remote session hijacking or physical terminal intrusion, traditional defenses offer zero visibility into who is currently operating the peripheral devices [1], [2].

Behavioral biometrics emerged to resolve this blind spot by observing continuous user activity rather than static physical credentials. Among input modalities, mouse dynamics provides an exceptionally non-intrusive foundation for real-time verification because pointing operations accompany virtually every desktop computing workflow without requiring specialized hardware or imposing user distraction [1]. However, the prevailing baseline in mouse dynamics literature suffers from an operational dichotomy. Earlier classical frameworks relied on macroscopic statistical aggregations, averaging kinematic measurements such as velocity, acceleration, and click latencies over lengthy observation windows of twenty to several hundred discrete interactions [2], [3]. While computationally lightweight, this aggregate baseline introduces an unacceptable detection lag that allows an unauthorized operator ample time to compromise system files before an anomaly triggers [4]. Conversely, recent shifts toward deep neural architectures and metric learning achieve high benchmark accuracy, but they do so by trading away transparency [3], [5]. These models function as opaque black boxes whose dense latent tensors demand significant computational resources and prevent forensic administrators from identifying which specific physical movement deviation triggered a security rejection [1], [5].

The core breakthrough of this study lies in capturing individual user mannerisms from short, discrete mouse trajectory signals rather than relying on delayed statistical windows or unexplainable neural networks [4], [6]. Human neuromotor control relies on rapid feedforward impulses combined with localized corrective feedback loops [7]. Because fine motor execution, muscle synergies, and ergonomic habits differ between operators, every individual leaves a distinct behavioral fingerprint even within a single, sub-second trajectory stroke [6], [7]. Rather than averaging these movements over time or discarding their spatial geometry, this study measures the exact physical shape of short mouse strokes using closed-form differential geometry—specifically orthogonal chord deviation, discrete Menger curvature, and stroke straightness—paired with Discrete Fréchet distance to preserve strict point-ordered curve morphometry [1], [8], [9]. By comparing each candidate movement directly against an enrolled genuine profile at the individual action level, this framework enables instantaneous, per-stroke continuous authentication while ensuring that every security decision remains mathematically traceable to verifiable physical mannerisms [4], [8].

---

### References (Baseline Literature)

[1] M. A. Khan, M. A. Khan, and F. A. Ghaleb, "Mouse Dynamics Behavioral Biometrics: A Survey of Methodologies, Challenges, and Opportunities," *ACM Computing Surveys*, vol. 56, no. 8, pp. 1–38, 2024.

[2] S. Almalki, C. Higgins, and V. B. Bapat, "Continuous Authentication Using Mouse Clickstream Data Analysis," *Applied Sciences*, vol. 11, no. 12, p. 5567, 2021.

[3] M. Antal and E. Egyed-Zsigmond, "SapiMouse: User Authentication Using Deep Feature Learning from Mouse Trajectories," *IEEE Access*, vol. 9, pp. 117180–117196, 2021.

[4] Y. Wang, C. Wu, Y. Liao, and M. You, "Optimizing Mouse Dynamics for User Authentication: LT-AMouse via Mouse Authentication Units," *arXiv preprint arXiv:2504.21415*, 2025.

[5] X. Jin, S. Zhang, and H. Wang, "User Authentication and Identity Inconsistency Detection via Mouse-Trajectory Similarity," *IEEE Transactions on Information Forensics and Security*, vol. 18, pp. 4120–4134, 2023.

[6] M. Djioua and R. Plamondon, "Kinematic Neuromotor Modeling of Rapid Mouse Trajectory Strokes," *IEEE Transactions on Systems, Man, and Cybernetics: Systems*, vol. 49, no. 7, pp. 1380–1392, 2019.

[7] E. Guțuleac, C. Radu, and M. Caramihai, "Goal-Directed Mouse Trajectory Features and Fitts' Law Motor Residuals in User Verification," *Computers & Security*, vol. 108, p. 102354, 2021.

[8] E. Asgarov, "Mathematical Feature Representations of Mouse Dynamics for Behavioral Biometric Authentication," *Journal of Pattern Recognition and Information Technologies*, vol. 14, no. 2, pp. 88–104, 2026.

[9] H. Alt and M. Godau, "Computing the Fréchet distance between two polygonal curves," *International Journal of Computational Geometry & Applications*, vol. 5, no. 01n02, pp. 75–91, 1995.
