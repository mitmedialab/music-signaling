# music-signaling
This a demo version of the SoundSignaling platform.  This project is designed to explore the communicative power of audio -- since so many of us listen to music for hours everyday, what if we could manipulate that music to convey information to us?

In this version, a client example is provided that will monitor your gmail inbox -- when a new email comes in, tracks you have uploaded and that you are listening to will be modified in a stylistically relevant way to let you know.  Follow the steps below to get started.

[Yes, it is a clunky project doing a hefty amount of audio processing with only a CLI.  That's why it's a prototype, be gentle!]

# STUDY PARTICIPANTS: INSTALLATION AND EMAIL CLIENT SETUP

## How to run this platform (Ubuntu/ OS X support only):
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
    
3. Install python dependencies by running the following.  (You may wish to work in a VirtualEnvironment -- you should be able to follow the same instructions once in your virtualenv.) 

```
cd music-signaling/
sudo pip install -r requirements.txt
```
	
4. Grant this application permission to access your email by running the following commands.  It will prompt you to visit a url, where you can provide consent to participate and enter your credentials.  This will result in an access string that you can paste back into the terminal. PLEASE NOTE: Your email will not be modified and its contents or private metadata will not be accessible to the authors of this work (despite the rather aggressive message :p)

```
cd client/
python setup_client.py
```
	
5. Load your personal music collection into the system by simply copying tracks (standard file formats such as mp3, wav, ogg should work) into the 'tracks/' folder. You can access it by typing:

```
cd ../server/tracks
```

### You need to run these steps every time you'd like to use the system.

7. To tell the system what tracks you'd like to listen to, type:

```
cd ..
```

In the 'info.csv' file, enter the metadata of the tracks in the following format, which corresponds to the filename, genre, and the meter. 

```
example1.mp3,classical,4
example2.mp3,pop,3
```
You can use any of the following genre key words:

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

8. Start the server with audio preprocessing, if the metadata in the 'info.csv' file has changed (including the order of the files) since the last time: 

```
$ python main.py -preprocess -start
```
	
If the metadata has not changed, you can use:

```
$ python main.py -start
```
	
When in doubt, always run with the '-preprocessing' flag. Preprocessing takes a duration of roughly 5-10% of the length of the song, though the duration may vary based on your compute power.  Pre-computed data for a given music file is also cached to help speed up the process.
	
9. Start the client in a separate terminal, replacing the 'xxx' with your GMail ID.  To run the client for 5 mins, for example, type:

```
$ python run_client_STUDY.py -id xxx@gmail.com -mins 5
```
	
To run until your playlist is played through, type:

```
$ python run_client_STUDY.py -id xxx@gmail.com 
```
	
You can always CTRL+C on the client terminal to terminate early.  You can also specify additional parameters such as the frequency (in minutes) at which your email is checked or the obviousness level {0,1,2} at which the modification is made:

```
$ python run_client_STUDY.py -id xxx@gmail.com -mins 5 -check_freq 2 -obviousness 0
```
10. Answer the question pertaining to the activity you are currently engaged in while using this system, and then you are ready to start.  Simply leave the application running in the terminal, and go back to doing whatever you were doing!


# STUDY PARTICIPANTS: TIPS AND TRICKS

1. Preprocessing is a slow process, especially if the genre also needs to be determined.  Considering throwing several tracks into the system at a time before you go to bed or while you get a cup of coffee in the morning, and you can shuffle them around or use subsets of them to make playlists throughout the day.
2. Do not panic if some of your songs do not play to the end -- every song is designed to play for at most its original duration with different forms of modifications included.
3. Tune the client parameters to your liking.  You may wish to start with the default parameters, but if you notice after a day that you aren't perceiving the notifications as often, or would like to be notified more frequently, change the '-check_freq' and '-obviousness' values as described above.
4. To find out at what point in time modifications have been made or when an email was detected, you can view the terminal output history.  This is ONLY meant to be a debugging/ dummy-check mechanism -- we encourage you NOT to do this when using the system! Try to use your ears.. and if this does not work well for you, we would love to learn why!


# STUDY PARTICIPANTS: QUICK CHECK/ TROUBLESHOOTING

Alternatively, instead of running step 9, you can do a realtime demo to check that the system is installed correctly. When the server displays 'Please begin the client application', do the following in a separate terminal:

```
$ cd client/
$ python
>>> import client
>>> c = client.Client()
```
after the tracks begin to play, feel free to try different signaling levels, at least a few seconds apart so you can listen to the modifications:

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






