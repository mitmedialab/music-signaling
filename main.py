########################################
# Music Signaling Pipeline Prototype
#   Main: music stream and signal proc
#   threads
#
# Author: Ishwarya Ananthabhotla
#########################################

import pyaudio
import pygame
import wave
import sys
import numpy as np
import util
import librosa
import time
import threading
import os
import argparse

import global_settings as gs
import pre_processing as pre
import modify_buffer as mb

# THREAD 1: Write audio from buffer to stream in chunks
def stream_audio(source_file_path, genre_tags, param_dict_list):
    # instantiate PyAudio 
    p = pyaudio.PyAudio()

    # open stream 
    stream = p.open(format=pyaudio.paFloat32,
                    channels=1,
                    rate=gs.sr,
                    output=True)

    hop_size_bytes = 1024 * 4 # bytes

    for i, track in enumerate(os.listdir(source_file_path)):
        gs.audio_buffer, gs.sr = librosa.load(source_file_path + track)
        gs.song_index = i

        gs.ptr = 0L        

        while gs.ptr < len(gs.audio_buffer):
            # convert to string
            out_data = gs.audio_buffer[gs.ptr: gs.ptr + (hop_size_bytes * 16)]
            out_data = out_data.astype(np.float32).tostring()

            # write to stream
            stream.write(out_data)
            gs.ptr += (hop_size_bytes * 16)

            print "ptr: ", gs.ptr

            
    # stop stream (4)
    stream.stop_stream()
    stream.close()

    p.terminate()


# THREAD 2: Monitor socket for flags and call modifiers
def modify_buffer(param_dict_list, genre_tags, dur=2, buff_time=3):
    param_dict = param_dict_list[gs.song_index]
    current_genre = genre_tags[gs.song_index]

    hop_size_bytes = 1024 * 4 # bytes

    done_flag = False
    count = 0

    start_jukebox = False

    # for pop use
    original_audio = gs.audio_buffer.copy()

    while count < 3:
        time.sleep(20) # test - replace with socket
        level = 2 # test - replace with socket

        print "Modification Signaled.."
        start = gs.ptr + (buff_time * (hop_size_bytes * 16))

        if start + (dur * gs.sr) >= len(gs.audio_buffer):
            print "Not enough audio to modify. Sleeping.."
            continue

        if current_genre == 'jazz':
            done_flag = mb.modify_jazz(level, param_dict, start)
        elif current_genre == 'classical':
            done_flag = mb.modify_classical(level, param_dict, start)
        elif current_genre == 'blues':
            done_flag = mb.modify_blues(level, param_dict, start)
        elif current_genre == 'pop':
            if not start_jukebox:
                start_jukebox = True
                t3 = threading.Thread(target=start_jukebox_process, args=(param_dict, start, ))
                t3.daemon = True
                t3.start()

            done_flag = mb.modify_pop(level, param_dict, start, original_audio)
        else:
            raise NotImplementedError 

        while done_flag == False:
            pass

        done_flag = False
        count +=1

def start_jukebox_process(param_dict, start):
    print "Starting Jukebox thread.."

    jukebox = param_dict['jukebox']

    # compute list of beat samples
    beat_samples = np.array([b['start']*jukebox.sample_rate for b in jukebox.beats], dtype=int)

    # get ordinal beat closest to start, set jkbx ptr to its sample
    nearest_beat_index = np.argwhere(beat_samples >= start)[0][0]
    curr_beat = jukebox.beats[nearest_beat_index]
    jkbx_ptr = 0L
    jkbx_ptr = int(curr_beat['start'] * gs.sr)

    # settings that force a jump
    previous_alert = None

    while jkbx_ptr < len(gs.audio_buffer):
        # insert current beat

        if jkbx_ptr + len(curr_beat['buffer']) > len(gs.audio_buffer):
            # fill balance with silence
            gs.audio_buffer[-1 * (len(gs.audio_buffer) - jkbx_ptr): ] = 0
            print "Finished Jukebox thread.."
            return

        gs.audio_buffer[jkbx_ptr: jkbx_ptr + len(curr_beat['buffer'])] = curr_beat['buffer']
        jkbx_ptr += len(curr_beat['buffer'])

        # jump next or sequential next?
        # in order to jump : (1) the alert must not have been addressed yet, (2) crossed the latency mark (just for consistency), and (3) must have suitable jump candidates
        if gs.pop_alert != previous_alert and curr_beat['jump_candidates'] != []:
            # make the jump
            jump_beat_index = np.random.choice(curr_beat['jump_candidates'])
            curr_beat = jukebox.beats[jump_beat_index]
            previous_alert = gs.pop_alert
        else:
            curr_beat = jukebox.beats[curr_beat['next']]
        time.sleep(0.3)

    print "Finished Jukebox thread.."
    return

# convert between int bytes format and float 32 samples
def convert(in_buffer):
    return (in_buffer.T.astype(np.float32)) /  np.iinfo(np.int16).max



if __name__ == "__main__":

    # command line arg parser
    parser = argparse.ArgumentParser()
    parser.add_argument('-preprocess', action='store_true')
    parser.add_argument('-start', action='store_true')
    args = parser.parse_args()


    # initialize global variables 
    gs.init()

    genre_tags = ['pop']
    source_file_path = 'tracks/'

    # preprocess
    if args.preprocess:
        print "Pre-processing.."
        param_dict_list = pre.preprocess(source_file_path, genre_tags)
        np.array(param_dict_list).dump("prep.dat")
        print "Finished Pre-processing."

    # realtime playback and modification
    if args.start:
        param_dict_list = np.load("prep.dat")
        t1 = threading.Thread(target=stream_audio, args=(source_file_path,genre_tags,param_dict_list, ))
        t1.daemon = True

        t2 = threading.Thread(target=modify_buffer, args=(param_dict_list, genre_tags, ))
        t2.daemon = True

        t1.start()

        print "Waiting for stream to load.."
        while gs.song_index == None:
            pass
        print "Stream Started."

        t2.start()

        while True:
            pass
