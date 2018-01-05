# music-signaling
This a demo version of the SoundSignaling platform.  This project is designed to explore the communicative power of audio -- since so many of us listen to music for hours everyday, what if we could manipulate that music to convey information to us?

In this version, a client example is provided that will monitor your gmail inbox -- when a new email comes in, tracks you have uploaded and that you are listening to will be modified in a stylistically relevant way to let you know.  Follow the steps below to get started.

Yes, it is a clunky project using Python for audio processing and only a CLI.  That's why it's a prototype, be gentle!

# STUDY PARTICIPANTS/ DEMO 1

## How to run this platform (Tested for Ubuntu/ OS X):
### You only need to run these steps once.
1. Clone this repository to your local machine.
2. You will need portaudio if you don't have it already:
```	
brew install portaudio	
```
or 

```
sudo apt-get install portaudio19-dev
```
    
3. Install dependencies by running: 

```
cd music-signaling/
pip install -r requirements.txt
```
	
3. Grant this application permission to access your email by running these commands and following the instructions: 

```
cd client/
python setup_client.py
```
You email will not be modified and its contents or private metadata will not be accessible to the authors of this work (despite the rather aggressive message :p)
	
4. Load your personal music collection into the folder labeled 'server/tracks/' (use mp3 or wav, others not tested.)

### You need to run these steps every time you'd like to use the system.

5. Tell the system what tracks you'd like to listen to:

```
cd ..
```

in the 'info.csv' file, enter the metadata of the tracks in the following format:

```
example1.mp3,classical,4
example2.mp3,pop,3
```
which is the filename, genre, and time signature. You can use any of the following genre key words:

```
'classical','rhythmless-instrumental', 'choir', 'avant-garde', 'soundtrack', 'pop', 'country', 'folk', 'latin', 'gospel', 
'blues','rock', 'hip-hop', 'R&B', 'soul', 'strong-rhythmic', 'disco', 'rap', 'jazz','rhythmic-instrumental', 'electronic', 'easy-listening'
```
or you can also leave the parameters blank like this:

```
example1.mp3,,
example2.mp3,pop,
example3.mp3,,3
```

6. Start the server: 

```
$ python main.py -preprocess -start
```
	
OR

```
$ python main.py -start
```
	
if the metadata hasn't changed since the last time. Preprocessing takes a duration of roughly 5-10% of the length of the song.
	
7. Start the client (in a separate terminal):

```
$ python run_client_STUDY.py -id xxx@gmail.com -mins 5
```
	
to run for 5 minutes, OR

```
$ python run_client_STUDY.py -id xxx@gmail.com 
```
	
to run until your playlist is played through. You can always CTRL+C to terminate early.  You can also specify additional parameters such as the frequency at which your email is checked or the obviousness level {0,1,2} at which the modification is made:

```
$ python run_client_STUDY.py -id xxx@gmail.com -start -mins 5 -check_freq 2 -obviousness 0
```
8. Answer the question pertaining to the activity you are currently engaged in while using this system, and then you are ready to start.


# DEMO 2

Alternatively, instead of running step 7, you can do a realtime demo. When the server displays 'Please begin client application', do the following:

```
$ cd client/
$ python
>>> import client
>>> c = client.Client()
```
after the tracks begin to play, feel free to try different signaling levels, at least a few seconds apart so people can listen to the modifications:

```
>>> c.signal(0)
>>> c.signal(1)
>>> c.signal(2)
```
when finished:
```
>>> c.end_server()
>>> c.end_client()
>>> exit()
```





# Development TODOs

## Minor Algorithmic Improvements
1. Bit of popping on tail end of level 1 classical music (time stretching)
2. Make sure we pick up rhythmic element instead of harmonic in blues overlay
3. More careful jump rules on jumping for pop
4. Classical needs fine tuning -- echo and stretch offset parameters
5. Blues -- overlays need volume control
6. Implement time signature detector in Automatic_Sorting using AES paper
7. Jazz key detection for shifting
8. Maintain jukebox ptr rate algorithmically based on number of jump vs/ non-jump beats
9. Phase vocoder for classical is kind of crap, better implementation?

## Minor Technical Improvements
1. Final UI for system use (text file / folder)
2. Switch back to Stereo
3. Pause music option, without restarting play sequence

## Bugs:
3. If modification sent when pop thread is done, it should be stored in queue, not dropped






