# music-signaling
Python prototype of the music signaling pipeline

# Minor Algorithmic Improvements
1. Bit of popping on tail end of level 1 classical music (time stretching)
2. Make sure we pick up rhythmic element instead of harmonic in blues overlay
3. More careful jump rules on jumping for pop
4. Classical needs fine tuning -- echo and stretch offset parameters
5. Blues -- overlays need volume control
6. Implement time signature detector in Automatic_Sorting using AES paper
7. Jazz key detection for shifting
8. Maintain jukebox ptr rate algorithmically based on number of jump vs/ non-jump beats
9. Phase vocoder for classical is kind of crap, better implementation?

# Minor Technical Improvements
1. Final UI for system use (text file / folder)
2. Operate on Stereo data instead of mono


# Major Developments:
1. (TEST) Dependency installation scripts
2. Log critical data for study


# QA:
1. Does it work on Windows/OS-X?

# Bugs:
3. If modification sent when pop thread is done, it should be stored in queue, not dropped


** Currently working on this.





