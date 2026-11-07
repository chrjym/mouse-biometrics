# Chapter 3

## RESEARCH METHODOLOGY

This chapter explains the research methods that are used in this study. It outlines the step-by-step procedure that
our study is trying to follow.

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
that each session belongs to the user whose folder holds it. The 405 sessions that the dataset's public labels mark as
illegal were excluded, since these were recorded by another person inside a user's folder and would misrepresent that
user's behavior. This leaves 1,271 sessions, from 87 to 191 per user.

### Data Preprocessing and Segmentation

In this process, the researchers segmented the mouse events of the users into short strokes to identify individual
movement patterns for analysis. The mouse movements were processed, which separates the continuous cursor movements
based on pauses and mouse click events. First, the recorded mouse movement sessions were loaded from the dataset,
wherein the data were cleaned by removing the records with missing values, scroll events, and invalid cursor
coordinates (x or y equal to 65,535, a logging error of the dataset). The remaining records were arranged according to
their client timestamps, and the time values of the sessions were adjusted to make them start at zero. After that, the
mouse movements were divided into individual mouse strokes, wherein a new stroke is created when the time gap between
two consecutive movement points exceeds 0.5 seconds or when a mouse click event occurs between two movement points.

After segmentation, only the strokes with at least 10 movement points were retained. Based on its recorded mouse
states, each stroke was categorized as a drag if more than half of its movement points were associated with dragging;
otherwise, it was categorized as a move. The segmented strokes were then normalized by moving their starting points to
the origin (0, 0), scaling their coordinates by the diagonal of their bounding box, and redrawing each stroke as 64
points spaced evenly along its path. This removes the differences in screen size and logging rate between users, so
that only the shape of each stroke is compared. Strokes in which the cursor did not move cannot be scaled; these were
excluded from the comparison but still counted toward their session's total number of strokes. The resulting strokes
were organized based on each session and movement type and prepared for the shape-matching process.

### Shape Matching using Dynamic Time Warping

The normalized strokes were compared using Dynamic Time Warping (DTW), which measures the distance between two strokes
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

### Selection of the Best Sensitivity and Number of Sessions

After segmenting the dataset into strokes, the researchers determined, for each split of legitimate users and
impostors, the best sensitivity and the best number of sessions to use as a profile. The sensitivity was tested from
0.01, incrementing by 0.01 up to 1.00, and the number of sessions *k* used for the library and for testing was varied
as well. The researchers tested four splits of legitimate users and impostors: one legitimate user and five impostors
(1×5), two legitimate users and three impostors (2×3), three legitimate users and two impostors (3×2), and five
legitimate users and one impostor (5×1). Each setting was scored as the average of the share of legitimate users
accepted and the share of impostors rejected, where a user is accepted when at least half of their tested sessions
pass.

For the random draw with seed 945, the 1×5 and 3×2 splits reached their best setting at a sensitivity of 0.05 with one
session, the 2×3 split at a sensitivity of 0.04 with two sessions, and the 5×1 split at a sensitivity of 0.02 with 25
sessions. In the 5×1 split at this setting, 3 of the 5 legitimate users were accepted (67 percent of their sessions
passed), while 48 percent of the impostor's sessions were also accepted. These best values were chosen on the same
runs that they score, so they are likely optimistic, and the one-session settings rest on very few tested sessions.

From these sessions, the researchers took the first stroke of each session and plotted each stroke from the origin
(0, 0) to illustrate the normalized shapes that are compared (Figure X).
