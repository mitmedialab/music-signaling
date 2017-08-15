# music-signaling
Python prototype of the music signaling pipeline

# Minor Improvements
1. Bit of popping on tail end of level 1 classical music (time stretching)
2. Make sure we pick up rhythmic element instead of harmonic in blues overlay
3. More careful jump rules on jumping for pop
4. Classical needs fine tuning -- echo and stretch offset parameters
5. Blues -- overlays need volume control
6. Implement time signature detector using AES paper
7. Jazz key detection for shifting


# Major Developments:
1. Automatic sorting of track
2. Minimum latency enforcement 
3. Add more control options to client interface
4. Maintaining pace between jukebox pointer and audio buffer


