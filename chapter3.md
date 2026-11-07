# Chapter 3

## RESEARCH METHODOLOGY

This chapter explains the research methods that are used in this study. It outlines the step-by-step procedure that
our study is trying to follow, in the order of the study's objectives: data acquisition and organization, data
preprocessing and segmentation, feature extraction using the convex and concave hull, Euclidean distance measurement,
and performance evaluation.

### Data Acquisition and Organization

In this process, the researchers acquire the publicly available mouse-dynamics dataset online to support the
evaluation of mouse-dynamics-based continuous authentication, which is the Balabit dataset. This dataset contains
mouse movement records that can be used to analyze the movement and behavioral patterns of users based on their
interaction with a certain computer. For the Balabit dataset, each record represents a mouse event, such as a cursor
movement, a click, or a scroll, and includes the record timestamp, client timestamp, button, state, and the x, y
coordinates. This dataset was selected to be the primary data source for this study's experiment, which contains the
mouse movements that will be needed to investigate the identification of users for continuous authentication. The use
of existing datasets allows the study to work with previously collected mouse movements rather than requiring a new
and long data collection process.

The dataset contains 10 users and 1,676 sessions. The researchers organized the sessions into one folder per user, so
that each session belongs to the user whose folder holds it. However, 405 of these sessions were not recorded by the
user whose folder holds them but by another person, as the dataset's labels show. These sessions were excluded, since
they would misrepresent that user's behavior. This leaves 1,271 sessions, from 87 to 191 per user.

### Data Preprocessing and Segmentation

In this process, the researchers segmented the mouse events of the users into short strokes to identify individual
movement patterns for analysis, and then selected the sessions that form each user's profile. The mouse movements were
processed, which separates the continuous cursor movements based on pauses and mouse click events. First, the recorded
mouse movement sessions were loaded from the dataset, wherein the data were cleaned by removing the records with
missing values, scroll events, and invalid cursor coordinates (x or y equal to 65,535, a logging error of the
dataset). The remaining records were arranged according to their client timestamps, and the time values of the
sessions were adjusted to make them start at zero. After that, the mouse movements were divided into individual mouse
strokes, wherein a new stroke is created when the time gap between two consecutive movement points exceeds 0.5 seconds
or when a mouse click event occurs between two movement points.

After segmentation, only the strokes with at least 10 movement points were retained. Based on its recorded mouse
states, each stroke was categorized as a drag if more than half of its movement points were associated with dragging;
otherwise, it was categorized as a move. The segmented strokes were then normalized by moving their starting points to
the origin (0, 0), scaling their coordinates by the diagonal of their bounding box, and redrawing each stroke as 64
points spaced evenly along its path. This removes the differences in screen size and logging rate between users, so
that only the shape of each stroke is compared. Strokes in which the cursor did not move cannot be scaled; these were
excluded from the comparison but still counted toward their session's total number of strokes. The resulting strokes
were organized based on each session and movement type.

**Shape matching using Dynamic Time Warping.** To decide which sessions are used to build each user's profile, the
normalized strokes were compared using Dynamic Time Warping (DTW), which measures the distance between two strokes
while allowing one to be stretched against the other. The stretching was limited to 10 percent of the stroke length
(6 of the 64 points), and only strokes of the same type were compared: move with move, and drag with drag. For each
stroke of a tested session, the smallest DTW distance to any stroke of the same type in a user's library was taken.
The stroke was counted as a match when its average distance per point did not exceed the sensitivity value, so a
lower sensitivity requires two strokes to be closer in shape before they count as a match.

A session was accepted as belonging to the owner of the library when at least 20 percent of its strokes matched;
otherwise it was rejected. Each user's sessions were shuffled once into a fixed order. A legitimate user's library
consists of the first *k* sessions in this order, and the user is tested with their last *k* sessions, which never
appear in the library. An impostor is tested with their first *k* sessions against every legitimate user's library,
and the library that accepts the most of the impostor's sessions is used.

**Selection of the best sensitivity and number of sessions.** The researchers then determined, for each split of
legitimate users and impostors, the best sensitivity and the best number of sessions to use as a profile. The
sensitivity was tested from 0.01, incrementing by 0.01 up to 1.00, and the number of sessions *k* used for the library
and for testing was varied as well. The researchers tested four splits of legitimate users and impostors: one
legitimate user and five impostors (1×5), two legitimate users and three impostors (2×3), three legitimate users and
two impostors (3×2), and five legitimate users and one impostor (5×1). Each setting was scored as the average of the
share of legitimate users accepted and the share of impostors rejected, where a user is accepted when at least half of
their tested sessions pass. The split whose best setting provides enough sessions to build a profile for each user was
used in the next processes, and its tested sessions were prepared for feature extraction.

### Feature Extraction (Convex Hull and Concave Hull)

From the selected sessions, the researchers took the first stroke of each tested session and plotted each stroke from
the origin (0, 0) to illustrate the normalized shapes that are compared (Figure X). The aligned strokes were pooled, or
combined into one group, within their respective users, and the researchers extracted the geometric features of each
user by constructing a convex hull around the pooled points and refining it into a concave hull. Each outline was then
resampled to 64 points spaced evenly along its length, which makes the outlines fair to compare by shape no matter how
big the strokes are.

The convex hull, the smallest convex polygon that encloses all the points, was constructed around each user's pooled
stroke points using the Graham scan [ ]. The process was as follows:

1. **Select the anchor point.** Duplicate points were removed, and the point with the lowest y-value was selected as
   the anchor. If two points were tied, the one farther left was chosen.
2. **Sort the points.** The remaining points were sorted by their angle from the anchor, which gives a clear path to
   walk along.
3. **Scan the points.** The points were scanned in sorted order, and each one was tested against the last corners kept
   on the stack.
4. **Form the hull.** The points that remained became the corners of the convex hull.

To obtain a shape closer to the user's actual movement pattern, the researchers refined the convex hull into a
concave hull using Delaunay erosion [ ]. The process was as follows:

1. **Connect the points.** The points were joined into a mesh of triangles (a Delaunay triangulation) that fills the
   convex hull, so the shape can be trimmed one triangle at a time. Long edges usually cross empty spaces that the
   strokes did not reach, while short edges appear where the strokes are close together.
2. **Set the limit.** A limit on the edge length was computed from the shortest and longest triangle edges. The ratio
   *r* controls how tightly the outline follows the points: a value of 0 gives the tightest outline, and a value of 1
   keeps the convex hull. This study used a ratio of 0.15 after comparing ratios of 0.05 and 0.15.
3. **Erode the boundary.** Any boundary edge longer than the limit was removed together with its triangle.
4. **Form the polygon.** When no more triangles could be removed, the outer border of the remaining triangles was
   traced into a single polygon.

### Euclidean Distance Measurement

To measure how the hulls differ from each other, the researchers compared their 64 resampled points using the
Euclidean distance. The Euclidean distance is the straight-line distance between two points, similar to measuring the
gap between them with a ruler. It is not the path taken from one point to another; it only measures how far apart the
points are in space. The distance is obtained using the Pythagorean theorem from the horizontal and vertical
differences of the points and is expressed in pixels, where a smaller value means the points are closer:

$$d = \sqrt{(x_2 - x_1)^2 + (y_2 - y_1)^2}$$

The Euclidean distance is among the statistical treatments commonly used in mouse dynamics [ ]. It was chosen for this
study because its values are directly interpretable in pixels, and it suits hulls whose resampled points start from
the same corner and run in the same direction. The process was as follows:

1. **Pair the points.** Starting from (0, 0), the points of the two hulls were paired in order:
   $A = (\Delta x_i^A, \Delta y_i^A)$ and $B = (\Delta x_i^B, \Delta y_i^B)$, for $i = 0, \dots, 63$.
2. **Measure each gap.** The distance between each pair was computed; a small gap means the outlines are close at that
   point: $g_i = \sqrt{(\Delta x_i^A - \Delta x_i^B)^2 + (\Delta y_i^A - \Delta y_i^B)^2}$.
3. **Combine the gaps.** The 64 gaps were combined into one total distance: $d(A, B) = \sqrt{\sum_{i=0}^{63} g_i^2}$.
4. **Average the gap.** The total distance was divided by 8 ($\sqrt{64}$) to give the average gap per point in pixels:
   $d_{RMS} = d(A, B) / 8$.

This turns all the gaps into one number: the smaller the distance, the closer the match.

### Performance Evaluation

For this process, the researchers evaluated the performance of the mouse-dynamics-based continuous authentication
model by determining whether a legitimate user can be distinguished from the impostors. The evaluation used the
Euclidean distances obtained from comparing each hull against the enrolled users' profiles, and each comparison was
treated as one authentication attempt. If the distance is within the threshold *T*, the attempt is accepted as the
legitimate user; otherwise, it is rejected:

$$\text{decision} = \begin{cases} \text{Accept}, & d_{RMS} \le T \\ \text{Reject}, & d_{RMS} > T \end{cases}$$

The threshold *T* was set by sorting the Euclidean distances of all authentication attempts from smallest to largest
and sliding the decision boundary across them. Each attempt falls into one cell of the confusion matrix, with the
impostor as the positive class:

| | Actual: Impostor | Actual: Legitimate |
|---|---|---|
| **Rejected** | True Positive (TP): impostor rejected | False Positive (FP): legitimate user rejected |
| **Accepted** | False Negative (FN): impostor accepted | True Negative (TN): legitimate user accepted |

The authentication performance was evaluated using the False Acceptance Rate (FAR), False Rejection Rate (FRR), Equal
Error Rate (EER), and accuracy. FAR measures the proportion of impostor attempts that are incorrectly accepted, while
FRR measures the proportion of legitimate attempts that are incorrectly rejected:

$$FAR = \frac{FN}{TP + FN} \qquad FRR = \frac{FP}{FP + TN}$$

The EER is the error rate at the threshold where FAR and FRR are equal, and accuracy measures the proportion of
authentication attempts that are correctly decided:

$$Accuracy = \frac{TP + TN}{TP + TN + FP + FN}$$

These metrics were analyzed to determine how well the geometric profiles distinguish legitimate users from impostors,
and whether they are suitable for continuous authentication based on mouse movement behavior.
