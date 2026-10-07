here me out, this is my idea:
IGNORE THE NUMBER 1 FOR NOW BUT KEEP IN MIND.
1. Record the "burn-in" of the user
   - the burn in is when the mouse is in idea for n seconds, i noticed that a users trying to locate the cursor position in the screen. why this is matter? well i think when a user try to move the mouse to locate the cursor, there is something unique upon moving the mouse (the direction, speed and pattern movving the mouse whether this is a circular movement or not)

PROCEED HERE

2. Chunk the 1 session into n seconds 
   - in my case i want to use 1 second, for every chunk the start point will be set to (0,0) and the Point B will adjust accordingly. if u can not visualize this ask me for more clarification.
   - the chunks output should look like [chunks](./experiment_earl/temp/chunks.csv) and a cleaner version [vector](./experiment_earl/temp/vectors.csv) (the script used was [build_chunks.py](./experiment_earl/temp/build_chunks.py) and [position_by_time.py](./experiment_earl/temp/position_by_time.py))
3. The session needed are only 3 session randomly selected
   - the datasets provided per user in balabit i think it is more than 20, our adviser guided us to select 3 random sessions that can create a unique profile of a user.
4. The output should be a concave hull
   - Raw data -> chunks point graph -> convex hull -> concave hull


I know this is kinda messy but always ask for my clarification

additionally read this article
https://www.analyticsvidhya.com/blog/2024/03/one-class-svm-for-anomaly-detection/?hl=en-PH