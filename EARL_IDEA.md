# List of new ideas that i want to work on:

1. Data we are using are the datasets provided by [balabit](./experiment_earl/datasets/balabit/) and [sapimouse](./experiment_earl/datasets/sapimouse/). But for now lets focus on balabit datasets and only use this balabit datasets.
2. I want a script that identify the shapes or mouse movement (via user cursor recorded) from the session and chunk them.
   - For example: Somewhere in the session got a unique shape or any kind of lines recorded, and save that into a set or export it into a file under the user's folder name *(conserve that trajectories[x, y, timestamp])*. Why do i need this? Somewhere in the next step, I want this to compare to another user's profile whether this can be matched and mark as **Legitimate user** or doesn't matched and mark as **Impostor user**. But still all lines and shapes recorded in the session still needed and included in the threshold.
3. I want a script that gets a **Random User** from the dataset (depends on user's configuration on how many **Legitimate User** can be included and how many **Impostor User** can also be included).
4. I want a script that gets the session **Randomly** from the datasets of the choosen **Random User** (Legitimate user and Impostor user) and save this on a new folder under [./experiment_earl/temp/legitimate/< user >/< session name >](./experiment_earl/temp/legitimate/) and [./experiment_earl/temp/impostor/< user >/< session name >](./experiment_earl/temp/impostor/).
5. I want a script that try to match the shapes and lines from the session we extracted [using the script from #2] of the Random selected user from the folder [./experiment_earl/temp/](./experiment_earl/temp/)
6. I want u to calculate the threshold using the formula: matched_detected/total_impostor_user. matched_detected = the result we get from the script in #5. total_number_impostor_user = how many selected as **Impostor user**
7. The result of #6 should be displayed as Bar Graph where the vertical label is *matched_detected* and the horizontal label is *total_number_impostor_user*. 
8. This experimental will be shown as heatmap where the closer to 0, the better! Meaning it is almost unique. The vertical line label in the heatmap is *number of session* and the horizontal line label in the heatmap is *number of legitimate user*. With a saturation point from 0.0, 0.1, 0.2, 0.3, ..., 1.0.



NOTE: I want u to ask and get a clarification on every complex idea