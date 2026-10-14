# `11_ocsvm_anomaly.py`: anomaly test with a One-Class SVM

[← index](README.md) · previous: [10](10_hull_anomaly.md) · next: [12](12_dtw_anomaly.md)

## What it does

Same test and same protocol as [10](10_hull_anomaly.md): leave-one-out genuine sessions, every other user's
sessions as impostors, 30-stroke windows, EER on the worst window. Two things change:

- **What describes a stroke:** six features instead of only the end point.
- **What the profile is:** a **One-Class Support Vector Machine** per user instead of a hull.

Outputs: `runs/<run>/results/ocsvm/{sessions,summary}.csv`, `figures/ocsvm_anomaly.png`.

## Step 1: features per stroke (`chunk_features`)

For a stroke with points $p_1, \dots, p_m$, path length $L$ and duration $T = \max(t_m - t_1,\ 0.001\text{ s})$:

| Feature | Formula | What it captures |
|---|---|---|
| `dx` | $x_m - x_1$ | horizontal direction and distance |
| `dy` | $y_m - y_1$ | vertical direction and distance |
| `path_length` | $\ln(1 + L)$ | how far the hand travelled |
| `straightness` | $\sqrt{\Delta x^2 + \Delta y^2}\,/\,L$ | 1 = straight line, near 0 = curvy or back-and-forth |
| `mean_speed` | $\ln(1 + L / T)$ | how fast the user moves (px/s) |
| `duration` | $T$ | how long the stroke took (s) |

`ocsvm_features` chooses which of these are used (all six by default). Similar per-movement features
(straightness, distance, speed, duration, direction) appear in earlier mouse-dynamics work [[1]](#ref-1), [[2]](#ref-2).

**Why these features?** They describe a stroke from several sides with one cheap number each: direction (the
hull's information), size, shape, and timing. Speed and timing are things a hull of end points cannot see.
Straightness separates direct movers from people who curve or correct.

**Why the logarithm on length and speed?** Both are heavily skewed: most strokes are short and slow, a few are
very long or fast, and the values span several orders of magnitude. $\ln(1+x)$ compresses the large values, so
a handful of extreme strokes do not dominate the model's distances. The "+1" keeps $\ln$ defined at 0. The log is the usual transform for positive, right-skewed data
[[3]](#ref-3).

**Optional time resampling (`ocsvm_resample_ms`).** user7/9/20 log a point every ~16 ms and the others every
~110 ms. A path sampled more often looks longer and less straight, even for the same movement. With
`ocsvm_resample_ms > 0`, the path is first read on a fixed time grid: at each grid time, the last logged
position is taken (a "zero-order hold"). The last point is always kept, so `dx`, `dy` and `duration` do not
change. Timestamps are made non-decreasing first ($t_i \leftarrow \max_{j \le i} t_j$), because Balabit's client
clock sometimes steps backward.

## Step 2: scaling (`RobustScaler`)

From scikit-learn [[4]](#ref-4), [[5]](#ref-5).

Each feature $f$ is scaled with the median and the interquartile range of the training strokes:

$$f' = \frac{f - \operatorname{median}(f)}{Q_{75}(f) - Q_{25}(f)}$$

**Why scale at all?** The RBF kernel below uses distances. Without scaling, `dx` in hundreds of pixels would
dominate `straightness` (between 0 and 1).

**Why robust scaling instead of mean and standard deviation?** Mouse data has many outliers (glitch-like jumps,
very long strokes). The median and the IQR are not pulled by them, while the mean and the standard deviation
are.

## Step 3: One-Class SVM (`fit`)

### The idea

During enrollment we only have the **owner's** data. Impostor data is not available when the system is set up,
so this is a **one-class** problem: learn the region where the owner's strokes live, and call anything far from
it anomalous.

### The optimization (Schölkopf et al. [[6]](#ref-6))

The strokes $x_1, \dots, x_N$ are mapped by a kernel into a feature space $\phi(x)$. The SVM finds a boundary
that separates most of the data from the origin with the largest margin:

$$\min_{w,\ \xi,\ \rho}\ \ \frac{1}{2}\|w\|^2 + \frac{1}{\nu N}\sum_{i=1}^{N}\xi_i - \rho
\qquad\text{subject to}\qquad w \cdot \phi(x_i) \ge \rho - \xi_i,\ \ \xi_i \ge 0$$

The **decision function** of a new stroke $x$ is

$$f(x) = \sum_{i} \alpha_i\, K(x_i, x) - \rho$$

- $f(x) > 0$: inside the owner's region;
- $f(x) < 0$: outside.

The **RBF (Gaussian) kernel** measures similarity as

$$K(x, x') = \exp\!\big(-\gamma\, \|x - x'\|^2\big)$$

**Parameters:**

- $\nu$ = `ocsvm_nu` (0.05) is an upper bound on the share of training strokes left outside the region (and a
  lower bound on the share of support vectors). It says "about 5% of the owner's own strokes may be unusual".
- $\gamma$ = `ocsvm_gamma` [[7]](#ref-7). `"scale"` sets $\gamma = 1 / (n_\text{features} \cdot \operatorname{Var}(X))$ from the
  scaled training data. A larger $\gamma$ gives a tighter, more irregular region.
- At most `ocsvm_max_train` (4000) random strokes are used for training. Training time grows roughly with the
  square of $N$ or faster [[8]](#ref-8), and 4000 is the same cap the DTW library uses in [12](12_dtw_anomaly.md), so all
  methods see as much data.

**Why a One-Class SVM?**

- It is the standard one-class method [[6]](#ref-6), [[9]](#ref-9), and it was in Earl's earlier prototype.
- Unlike the hull, its region can be **non-convex and in several pieces**, and it works in any number of
  dimensions, so all six features can be used together.
- $\nu$ gives a direct, interpretable control over how many of the owner's strokes are tolerated as unusual.

## Step 4: window scoring (`score`)

The same sliding window as script 10, but averaging the SVM score instead of a 0/1 "outside" flag:

$$w_j = \frac{1}{W}\sum_{i=j}^{j+W-1} f(x_i)$$

A window is flagged when $w_j <$ `ocsvm_flag_score` (0 = the learned boundary). The session's score is its
**lowest** window, $s = \min_j w_j$.

The EER uses the same method as script 10 with the direction reversed, because a **low** score is anomalous here:

$$\text{FRR}(t) = P(s_\text{genuine} < t), \qquad \text{FAR}(t) = P(s_\text{impostor} \ge t)$$

**Why average the score and not count outside strokes?** The score also says *how far* outside a stroke is. Many
strokes just past the boundary are less suspicious than a few far beyond it.

## Settings used

`ocsvm_features`, `ocsvm_nu`, `ocsvm_gamma`, `ocsvm_max_train`, `ocsvm_resample_ms`, `ocsvm_flag_score`,
plus `anomaly_enroll_sessions` and `anomaly_window` from 10.

## What we learned (6 features, nu 0.05)

- **EER 29.6%** overall, against 43.8% for the hull (FRR 7.7%, FAR 37.4%).
- Best users: user9 (2.6%), user29 (11.5%), user7 (14.0%). Worst: user16 (52.1%).
- With only `dx`, `dy`, the SVM is no better than the hull (~49%): the gain comes from the **extra features**,
  not from the model.
- With `ocsvm_resample_ms: 125`, the EER is still 29.6%, so the fast loggers' good results are not just a
  logging-rate effect.

## References

<a id="ref-1"></a>[1] H. Gamboa and A. Fred, "A behavioral biometric system based on human-computer interaction," in *Proc. SPIE 5404, Biometric Technology for Human Identification*, 2004, pp. 381–392, doi: [10.1117/12.542625](https://doi.org/10.1117/12.542625).

<a id="ref-2"></a>[2] A. A. E. Ahmed and I. Traore, "A new biometric technology based on mouse dynamics," *IEEE Trans. Dependable Secure Comput.*, vol. 4, no. 3, pp. 165–179, Jul.–Sep. 2007, doi: [10.1109/TDSC.2007.70207](https://doi.org/10.1109/TDSC.2007.70207).

<a id="ref-3"></a>[3] G. E. P. Box and D. R. Cox, "An analysis of transformations," *J. Roy. Statist. Soc. Ser. B*, vol. 26, no. 2, pp. 211–243, 1964, doi: [10.1111/j.2517-6161.1964.tb00553.x](https://doi.org/10.1111/j.2517-6161.1964.tb00553.x).

<a id="ref-4"></a>[4] F. Pedregosa *et al.*, "Scikit-learn: Machine learning in Python," *J. Mach. Learn. Res.*, vol. 12, pp. 2825–2830, 2011. [Online]. Available: https://jmlr.org/papers/v12/pedregosa11a.html

<a id="ref-5"></a>[5] scikit-learn developers, "sklearn.preprocessing.RobustScaler," scikit-learn documentation. [Online]. Available: https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.RobustScaler.html

<a id="ref-6"></a>[6] B. Schölkopf, J. C. Platt, J. Shawe-Taylor, A. J. Smola, and R. C. Williamson, "Estimating the support of a high-dimensional distribution," *Neural Comput.*, vol. 13, no. 7, pp. 1443–1471, Jul. 2001, doi: [10.1162/089976601750264965](https://doi.org/10.1162/089976601750264965).

<a id="ref-7"></a>[7] scikit-learn developers, "sklearn.svm.OneClassSVM," scikit-learn documentation. [Online]. Available: https://scikit-learn.org/stable/modules/generated/sklearn.svm.OneClassSVM.html

<a id="ref-8"></a>[8] scikit-learn developers, "Support Vector Machines: Complexity," scikit-learn User Guide, §1.4. [Online]. Available: https://scikit-learn.org/stable/modules/svm.html

<a id="ref-9"></a>[9] scikit-learn developers, "Novelty and outlier detection," scikit-learn User Guide. [Online]. Available: https://scikit-learn.org/stable/modules/outlier_detection.html
