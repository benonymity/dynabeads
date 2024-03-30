# MyOne Dynabead Research
This stared as a quick and dirty script I threw together to try and replace an $800/year Mathematica subscription. It's current incarnation is as a standalone GUI executable (though it can still be run from the command line) for tracking analysis, though at some point I'll add bulk cropping to it's functionality. Right now the script processes all the `.avi` files in whichever folder you provide. It uses [OpenCV]() to track the center of any centroid it can detect, and has the functionality to save that data as a raw text file with rotation angle around the computed center of rotation, to graph the bead's position over time and the calculated center, or to export the original video with an overlay of the center of the bead to observe/debug any mistracks. It processes as many videos in parallel as the CPU permits, so is generally quite speedy. My M1 Pro can processes 15 videos (each ~1:30 long and ~30 MB in size) each second.

# Usage
I recommend downloading the latest executable for your OS from [releases](https://github.com/benonymity/dynabeads/releases). Since this is a non-ideal executable situation (\*cough* Python \*cough*), the standalone executable has some long startup times. Don't be alarmed if the app takes a minute to start. Once it does finish initializing you should see a simple, self-explanatory GUI, and can analyze away.

# Develop

If you'd like to tinker a bit more, or if the executable simply isn't working for you, you can run the script in your own Python environment.
```sh
git clone https://github.com/benonymity/dynabeads.git
```
(or download and unzip the repo if you don't have `git` installed)
```sh
cd dynabeads/src
```
```sh
pip3 install -r requirements.txt
```
and run 
```sh
python3 gui.py
```
to interact with a GUI, or
```sh
python3 process.py -h
```
to experiment with the command-line version. Enjoy!