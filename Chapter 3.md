**CHAPTER III**  
**METHODOLOGY**

	This chapter explains the research methods that are used in this study. It outlines the step-by-step procedure that our study is trying to follow.

**Data Acquisition and Organization**   
	In this process, the researchers acquire the publicly available mouse-dynamics dataset online to support the evaluation of mouse-dynamics-based continuous authentication, which is the Balabit dataset. This dataset contains mouse movement records that can be used to analyze the movement and behavioral patterns of users based on their interaction with a certain computer. For the Balabit dataset, each record represents a mouse event, such as a cursor movement, a click, or a scroll, which includes the record timestamp, client timestamp, button, state, and the x, y coordinates. This dataset was selected to be the primary data source for this study’s experiment, which contains the mouse movements that will be needed to investigate the identification of users for continuous authentication. The use of existing datasets allows the study to work with previously collected mouse movements rather than requiring a new and long data collection process.

**Data Preprocessing and Segmentation**  
	In this process, the researchers segmented the mouse event of the users into short strokes to identify individual movement patterns for analysis. The mouse movements were processed, which separates the continuous cursor movements based on pauses and mouse click events. First, the recorded mouse movement sessions were loaded from the dataset, wherein the data were cleaned by removing the records with missing values, scroll events, and invalid cursor coordinates. The remaining records were arranged according to their timestamps and the time values of the sessions were adjusted to make it start at zero. After that, the mouse movements were divided into individual mouse strokes wherein a new stroke is created when the time gap between two consecutive movement points exceeds 0.5 seconds or when a mouse click event occurred immediately before the next movement.  
	After segmentation, the strokes were organized to retain those with at least 10 movement points wherein based on its recorded mouse states, each stroke was categorized as drag if more than half of its movement points were associated with dragging or else it was categorized as a move. Also, the segmented strokes were organized by moving their starting points to the origin (0, 0\) and scaling their coordinates based on their bounding-box diagonal. The resulting strokes were organized based on each session and movement types and will be prepared for the next feature extraction process.

**Feature Extraction (Convex Hull and Concave Hull)**

***Figure***   
	After segmenting the dataset into strokes, the researchers determined the best sensitivity and the best number of sessions that will be used to create a profile for each user. Each legitimate user’s profile, or library, consists of the user’s first sessions. A legitimate user is tested with their last sessions, which never appear in the library, while an impostor is tested with their own first sessions against each legitimate user’s library. Each stroke of a tested session was compared with the library strokes of the same type using Dynamic Time Warping, and the stroke was counted as a match when its average distance per point did not exceed the sensitivity; a lower sensitivity therefore requires a closer match. A session passes, or is accepted as the library’s owner, when at least 20 percent of its strokes match.  
	The sensitivity starts at 0.01, incrementing by 0.01 up to 1.00. The researchers tested four splits of legitimate users and impostors: one legitimate user and five impostors (1×5), two legitimate users and three impostors (2×3), three legitimate users and two impostors (3×2), and five legitimate users and one impostor (5×1). For each split, the setting that best accepts the legitimate users while rejecting the impostors was chosen as its best sensitivity and number of sessions, and the split whose best setting provides enough sessions to build a profile for each user was used in the next steps. 

From these sessions, the researchers registered the first chunk of each session and plotted each chunk from the origin (0,0).

*insert formula*

The aligned chunks were pooled or combined into one group within their respective users, and the researchers extracted the geometric features of the user by constructing a convex hull around the points and refining it into a concave hull. Therefore, each outline was resampled to 64 evenly spaced points equally along its length. That makes them fair to compare by shape no matter how big the strokes are. 

The convex hull was constructed around each user’s pooled stroke points using the **Graham scan** \[\]. The convex hull is the smallest convex polygon that encloses all the points. The process was as follows: 

1. **Select the anchor/Starting point**. The researchers removed duplicate points and selected the point with the lowest y-value as the anchor. If two points are tied, the one farther left was chosen.   
2. **Sort the points/ Polar sort.**  The remaining points were sorted by their angle from the starting point. This shows the radar line within the strokes it scans from left to right. It gives a clear path to walk along.  
3. **Scan the points.** The points were scanned in sorted order; each one was tested against the last corner kept and stacked.   
4. **Form the hull**.  The points that remained became the corners of the convex hull.   
   

References: In “Mathematical feature representation of mouse dynamics for continuous user authentication,	” Journal of Physics: Conference Series, vol.17, no.2, 2021  
	To obtain a shape closer to the user's actual movement pattern, the researchers refined the convex hull into a concave hull using **Delaunay erosion** \[\]. The process was as follows: 

1. **Connect the points/ Delaunay triangulation.** The points were joined into a mesh of triangles that filled the convex hull. This made it possible to trim the shape one triangle at a time. Long lines usually crossed empty spaces where the strokes did not reach, while short lines appeared where the strokes were close together.   
2. **Set the limit**. Put a limit on the edge length, which is computed from the shortest and longest triangle edges. The ratio r controlled how tightly the outline followed the points: a value of 0 gave the tightest outline; otherwise, a value of 1 kept the convex hull. This study used a ratio of 0.15  after comparing ratios of 0.05 and 0.15  
3. **Erode the boundary**. Remove any boundary edge along with its triangle.    
4. **Polygon Representation.** No more triangles could be removed; the other border of the remaining triangles was traced into a single polygon. 

**Euclidean Distance Measurement**  
	To measure how hulls differ from each other, the researchers compared their 64 data points from the resample using the **Euclidean Distance.** Euclidean distance is the straight-line distance between two points, similar to measuring the gap between them with a ruler. It's not the actual path taken from one point to another; it only measures how far apart the points are in space. The distance is obtained using the **Pythagorean Theorem** from the horizontal and vertical differences of the points and is expressed in pixels, where a smaller value means the points are closer.    
$\ d\ =\ \sqrt{({{x}_{2}-{x}_{1})}^{2}\ +({{y}_{2}-{y}_{1})}^{2}\ }{\ }$${}$  
Euclidean distance is among the statistical treatments commonly used in mouse dynamics \[\]. It was chosen for this study as it applies to directly interpretable pixels, and it suits the hull used from the resampled points starting from the same corner and running in the same direction. The process is as follows: 

1. **Pair the points**. From (0,0), each hull is matched to each hull.  
   $A\ =\ (\Delta {{x}_{i}^{A},\ \Delta {x}_{i}^{A}),\ B=(\Delta {x}_{i}^{B},\Delta {y}_{i}^{B}),\ i=0,...,63}_{}^{}$  
2. **Measure each gap**. The distance between each pair is computed; a small gap means the outlines are close at that point.  
   ${g}_{i}=\ \sqrt{(\Delta {{x}_{i}^{A}-\Delta {x}_{i}^{B})}^{2}\ +(\Delta {{y}_{i}^{A}-\Delta {y}_{i}^{B})}^{2}}$  
3. **Combine the gaps**. The 64 gaps are combined into one total distance.  
   $d(A,B)\ =\ \sqrt{\sum\limits_{i=0}^{63}{g}_{i}^{2}}$  
4. Average Gap.  The average gap per point is pixels  
   ${d}_{RMS}=\ \frac{d(A,B)}{8}$

	By doing this, all the gaps turned into one number, and the answers became so simple: the smaller the distance, the closer the match. In the end, a user is recognized not by what they click, but by the shape of how they move, because identity is found in the smallest distance. 

**Performance Evaluation**

	For this process, the researchers evaluated the performance of the mouse-dynamic-based continuous authentication model by determining whether a legitimate user can be distinguished from the impostor ones. The evaluation was performed using the Euclidean Distance scores obtained from comparing the probe hull against the enrolled user’s profile and determining whether each authentication attempt is correctly accepted or rejected using the authentication threshold. So if the calculated distance is within the threshold, the user is considered the legitimate user or else the authentication attempt is rejected immediately.  
$decision\ =\ \begin{cases} Accept, & {d}_{RMS}\ \le\ T \\ Reject, & {d}_{RMS}\ >\ T \end{cases}$  
	The threshold T was set by sorting the Euclidean distances of all authentication attempts from smallest to largest and sliding the decision boundary across them. Each attempt falls into one cell of the confusion matrix, with the impostor as the positive class:

| | Actual: Impostor | Actual: Legitimate |
| :---- | :---- | :---- |
| **Rejected** | True Positive (TP): impostor rejected | False Positive (FP): legitimate user rejected |
| **Accepted** | False Negative (FN): impostor accepted | True Negative (TN): legitimate user accepted |

	The authentication performance is evaluated using the False Acceptance Rate (FAR), False Rejection Rate (FRR), Equal Error Rate (EER), and Accuracy. FAR measures the proportion of impostor attempts that are incorrectly accepted, while FRR measures the rate of legitimate users’ attempts that are incorrectly rejected.   
$FAR\ =\ \frac{FN}{TP\ +\ FN}$          $FRR\ =\ \frac{FP}{FP\ +\ TN}$  
EER measures the rate at which FAR and FRR are equal or approximately equal and accuracy measures the proportion of the authentication attempts that are correctly identified.  
$EER\ =\ FAR\ =\ FRR\ \text{at the threshold where}\ FAR\ =\ FRR$          $Accuracy\ =\ \frac{TP\ +\ TN}{TP\ +\ TN\ +\ FP\ +\ FN}$   
	These performance metrics were analyzed to determine whether the model is appropriate for continuous authentication and determining whether it is effective in recognizing legitimate users and detecting unauthorized users. The results were used to evaluate the accurate matching performance of the geometric representations and determine its suitability for continuous authentication on mouse movement behavior.