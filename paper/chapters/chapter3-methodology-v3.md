# Chapter 3: Methodology

## Research design

This study uses a quantitative, experimental design that converts each user's 0.5 s mouse strokes into a concave hull profile and compares profiles by Euclidean distance. The analysis uses run 19399f (seed 945).

**Specific objectives:**

1. Acquire mouse movement data from a publicly available dataset;
2. Segment mouse movement streams into short strokes of 0.5 seconds;
3. Capture behavioral mannerisms as closed geometric shapes by constructing a convex hull, refining it into a concave hull, and representing each outline as a fixed set of data points;
4. Measure the dissimilarity between the data points of a user's hull and those of enrolled user profiles using the Euclidean distance; and
5. Evaluate the matching performance using accuracy, FAR, FRR and EER, and determine how well the geometric profiles distinguish users toward continuous authentication.

## Process overview

The method moves from raw pointer records to a single decision in seven stages. Each stage produces the input of the next.

1. **Data selection.** Sessions come from the Balabit dataset, and those marked illegal are excluded. The result is a set of sessions for each user.
2. **Stroke extraction.** One stroke of exactly 0.5 s is taken from each session, which keeps every session's contribution equal in duration.
3. **Grouping.** A user's strokes are split into two sets. The passed sessions form the profile, and all tested sessions form the mixed hull.
4. **Alignment and pooling.** Every stroke is moved to start at (0,0), and the strokes in a set are pooled into one point cloud. Position on the screen no longer matters, so the cloud reflects only how far and in which directions the user moved from the start of each stroke.
5. **Shape construction.** The convex hull gives the outer boundary of the cloud. Because it spans empty regions that no stroke visits, it is refined into a concave hull that follows the cloud more closely. For user29, this refinement keeps 38.1% of the convex area.
6. **Conversion to numbers.** Two outlines may have different numbers of corners, so they cannot be compared corner by corner. Each outline therefore gets the same starting corner and direction, and is resampled to 64 evenly spaced points. With an x and a y value for each point, every outline becomes a vector of 128 numbers.
7. **Comparison and decision.** Matching points on two outlines are compared, and the gaps are summarized as one distance. For identification, the nearest profile is the identified user. For verification, a claim is accepted when the distance is at or below the threshold T, and the resulting decisions give FAR, FRR, EER and accuracy.

## Data and stroke segmentation

The study uses the public [Balabit Mouse Dynamics Challenge](https://github.com/balabit/Mouse-Dynamics-Challenge) dataset [1], which records mouse pointer timing and position for 10 users. Sessions marked as illegal in its public labels were excluded.

Sessions were taken from the best settings of the earlier simulation. One stroke of exactly 0.5 s was taken from each session.

- **Profile:** the strokes of a user's passed sessions, which represent the enrolled user.
- **Mixed hull:** the strokes of all that user's tested sessions, which serve as the test sample.

## Geometric representation

The user × best sensitivity × best session setting was determined first: sensitivity 0.02 and 25 sessions.

| User | Sessions passed | Sessions registered |
|---|---|---|
| user9 | 23 | 25 |
| user15 | 9 | 25 |
| user20 | 23 | 25 |
| user23 | 11 | 25 |
| user29 | 18 | 25 |

Only the first chunk of each session was registered and then plotted at (0,0).

Each set of strokes becomes one closed outline and then one fixed-length vector of 128 numbers. The steps use user29's profile as the example.

1. **Alignment.** Each stroke is shifted so that it starts at (0,0), which removes screen position.

$$\Delta x_t = x_t - x_0, \qquad \Delta y_t = y_t - y_0$$

2. **Convex hull.** The Graham scan [2] finds the smallest convex polygon around the pooled stroke points. For user29 this area is 782,606 px².

   $$\mathrm{cross}(O,A,B) = (x_A - x_O)(y_B - y_O) - (y_A - y_O)(x_B - x_O)$$

   $$Area = \frac{1}{2}\left|\sum_{k=1}^{n}(x_k y_{k+1} - x_{k+1} y_k)\right|$$

3. **Concave hull.** Delaunay erosion, as described by Davis [3], triangulates the points and removes outer triangles with long edges (ratio 0.15). For user29 the limit is 149.6 px, leaving 53 corners and 298,036 px², or 38.1% of the convex area.

   $$L = l_{min} + r(l_{max} - l_{min})$$

   $$\frac{Area_{concave}}{Area_{convex}} = \frac{298{,}036}{782{,}606} = 38.1\%$$

4. **Fixed start.** Corners are ordered counter-clockwise from the lowest corner, then the leftmost if tied.
5. **Data points.** The outline is resampled to 64 evenly spaced points. For user29, the 4,863 px perimeter gives a step of about 76 px.

$$s_i = \frac{i}{64}P, \qquad i = 0, \dots, 63$$

6. **Feature vector.** The points are stacked into one vector.

$$H = (\Delta x_0, \Delta y_0, \dots, \Delta x_{63}, \Delta y_{63})$$

Sensitivity testing at 32, 64, 128 and 256 points produced identical nearest-profile assignments. No distance differed from its 64-point value by more than 3.0 px, so 64 points were retained.

## Euclidean distance

Hull A and hull B are compared point by point, and the result is reported as a root-mean-square distance per point.

$$g_i = \sqrt{(\Delta x^A_i - \Delta x^B_i)^2 + (\Delta y^A_i - \Delta y^B_i)^2}$$

$$d(A,B) = \sqrt{\sum_{i=0}^{63} g_i^2}, \qquad d_{RMS} = \frac{d(A,B)}{\sqrt{64}}$$

Smaller values mean more similar hulls. For user23 and user29, the distance is 3,353 px, so the per-point distance is 3,353 ÷ 8 = 419 px. The largest gaps, up to about 670 px, occur at points 30–36, where user29's hull reaches further upward.

Each mixed hull is compared with every profile, and the nearest profile is the identified user.

## Evaluation metrics and baseline

The method reached an EER of 20% at about 418 px, using one global threshold T. A claim is accepted when the distance is at or below T. FAR and FRR follow the error-rate concepts in ISO/IEC 19795-1:2021 [4], and EER is the point where they are equal.

$$FAR = \frac{\text{impostor attempts accepted}}{\text{all impostor attempts}}, \qquad FRR = \frac{\text{genuine attempts rejected}}{\text{all genuine attempts}}$$

$$Accuracy = \frac{\text{correct decisions}}{\text{all decisions}}$$

A low threshold rejects more impostors but also more genuine users, and a high threshold does the reverse. The table below shows this trade-off, with FAR rising from 0% to 34.3% as the threshold grows while FRR falls from 20% to 0%. The evaluation used 40 comparisons at 64 points: 5 genuine and 35 impostor. The profile of user16 was removed because it was built from wrongly accepted impostor sessions.

| Threshold (px) | FAR | FRR | Accuracy |
|---|---|---|---|
| 122.1 | 0/35 (0%) | 1/5 (20%) | 97.5% |
| 418.0 (EER) | 7/35 (20%) | 1/5 (20%) | 80.0% |
| 462.4 | 12/35 (34.3%) | 0/5 (0%) | 70.0% |

**Baseline.** Almalki et al. [5] evaluated classifiers on the same Balabit dataset. In its point-and-click authentication scenario, the abstract reports accuracy of 87.6% to 99.3% and AUC of 90.3% to 99.9%. It serves as context only, because its features, classifiers and evaluation units differ from this study's. No claim of better or worse performance is made.

## Limitations

These results are descriptive and do not estimate performance on unseen sessions.

- **Overlap:** mixed hulls include the strokes used to build the profiles, which lowers genuine distances.
- **Small sample:** there are only 5 genuine comparisons, so one user changes FRR by 20 points.
- **Threshold selection:** thresholds were chosen on the same data they were evaluated on.
- **Impostor evidence:** user35 and user7 have one session each, and cross-user comparisons are not real attacks.
- **Size:** hulls are compared in raw pixels, so distances reflect size as well as shape.
- **Outliers:** hull outlines depend on extreme strokes, and hulls from more sessions tend to be larger.
- **Point matching:** points are matched by outline order, so a pair may compare unrelated parts of two shapes.
- **Continuous use:** whole hulls across sessions were compared, so authentication during a session was not tested.

## References

[1] N. Siddiqui, R. Dave, and N. Seliya, "Continuous authentication using mouse movements, machine learning, and Minecraft," arXiv:2110.11080, 2021, doi: 10.48550/arXiv.2110.11080.

[2] Y. Lan and Y. Sun, "Formal verification of Graham's scan algorithm," in *Companion Proc. 2025 ACM SIGPLAN Int. Conf. Systems, Programming, Languages, and Applications: Software for Humanity*, 2025, pp. 34–36, doi: 10.1145/3758316.3763250.

[3] M. Davis, "Concave hulls in JTS," *Lin.ear th.inking*, Jan. 18, 2022. [Online]. Available: https://lin-ear-th-inking.blogspot.com/2022/01/concave-hulls-in-jts.html

[4] *Biometric Performance Testing and Reporting, Part 1: Principles and Framework*, ISO/IEC 19795-1:2021, 2021.

[5] S. Almalki, P. Chatterjee, and K. Roy, "Continuous authentication using mouse clickstream data analysis," arXiv:2312.00802, 2023.
