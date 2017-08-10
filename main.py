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
import csv

import global_settings as gs
import pre_processing as pre
import modify_buffer as mb

# THREAD 1: Write audio from buffer to stream in chunks
def stream_audio(track_names, genre_tags, param_dict_list, modify_flag, finished_flag):
    # instantiate PyAudio 
    p = pyaudio.PyAudio()

    # open stream 
    stream = p.open(format=pyaudio.paFloat32,
                    channels=1,
                    rate=gs.sr,
                    output=True)

    hop_size_bytes = 1024 * 4 # bytes

    for i, track in enumerate(track_names):
        
        gs.audio_buffer, gs.sr = librosa.load(track)
        gs.song_index = i

        gs.ptr = 0L

        # continue modifier thread
        modify_flag.set()
        print "New song loaded!"        

        while gs.ptr < len(gs.audio_buffer):
            # convert to string
            out_data = gs.audio_buffer[gs.ptr: gs.ptr + (hop_size_bytes * 16)]
            out_data = out_data.astype(np.float32).tostring()

            # write to stream
            stream.write(out_data)
            gs.ptr += (hop_size_bytes * 16)

            print "ptr: ", gs.ptr

        # make modifier thread wait while we load new song
        modify_flag.clear()
        print "Loading new song.."
        time.sleep(1) # wait for buffer thread to reset

            
    # stop stream
    stream.stop_stream()
    stream.close()

    p.terminate()

    finished_flag.set()
    print "Finished playlist. Thank you for listening!"


# THREAD 2: Monitor socket for flags and call modifiers
def modify_buffer(param_dict_list, genre_tags, modify_flag, finished_flag, dur=4, buff_time=3):

    # settings
    hop_size_bytes = 1024 * 4 # bytes
    done_flag = False
    count = 0
    start_jukebox = False

    while not finished_flag.isSet() and count < 50: # test - replace with socket
        # make a modification every N seconds if we can
        time.sleep(10) # test - replace with socket
        level = 1 # test - replace with socket

        if modify_flag.isSet():

            param_dict = param_dict_list[gs.song_index]
            current_genre = genre_tags[gs.song_index]

            print "Modification Signaled.."
            start = gs.ptr + (buff_time * (hop_size_bytes * 16))

            if start + (dur * gs.sr) >= len(gs.audio_buffer):
                print "Not enough audio left to modify. Sleeping.."
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
                done_flag = mb.modify_pop(level, param_dict, start)
            else:
                raise NotImplementedError 

            count +=1t



def start_jukebox_process(param_dict, start):

    ######################################################
    # weak trapezoidal taper window for each beat
    def beat_window(sig, high_end=1.0, low_end=0.5):
        fade_samples = int(len(sig) * (1.0 / 8.0))

        # ramp up
        ramp_up = np.array([(-1.0 * (low_end - high_end) / fade_samples) * x + low_end for x in range(fade_samples)])
        sig[:fade_samples] *= ramp_up

        #ramp down
        ramp_down = np.array([(-1.0 * (high_end - low_end) / fade_samples) * x + high_end for x in range(fade_samples)])
        sig[-fade_samples:] *= ramp_down

        return sig


    def taper_buffer_edges(range_start, range_end, fade_time, high_end=1.0, low_end=0.5):
        fade_samples = int(fade_time * gs.sr)
        # ramp down
        ramp_down = np.array([(-1.0 * (high_end - low_end) / fade_samples) * x + high_end for x in range(fade_samples)])
        gs.audio_buffer[range_start - fade_samples: range_start] *= ramp_down 

        #ramp up 
        ramp_up = np.array([(-1.0 * (low_end - high_end) / fade_samples) * x + low_end for x in range(fade_samples)])
        gs.audio_buffer[range_end: range_end + fade_samples] *= ramp_up

        return 
    #######################################################

    print "Starting Jukebox thread.."

    jukebox = param_dict['jukebox']

    # compute list of beat samples
    beat_samples = np.array([b['start']*jukebox.sample_rate for b in jukebox.beats], dtype=int)

    # get ordinal beat closest to start, set jkbx ptr to its sample
    nearest_beat_index = np.argwhere(beat_samples >= start)[0][0]
    curr_beat = jukebox.beats[nearest_beat_index]
    beat_buf = curr_beat['buffer']
    jkbx_ptr = 0L
    jkbx_ptr = int(curr_beat['start'] * gs.sr)

    # settings that force a jump
    previous_alert = None

    while jkbx_ptr < len(gs.audio_buffer):
        # insert current beat

        if jkbx_ptr + len(beat_buf) > len(gs.audio_buffer):
            # fill balance with silence
            gs.audio_buffer[-1 * (len(gs.audio_buffer) - jkbx_ptr): ] = 0
            print "Finished Jukebox thread.."
            return

        gs.audio_buffer[jkbx_ptr: jkbx_ptr + len(beat_buf)] = beat_buf
        jkbx_ptr += len(beat_buf)

        # jump next or sequential next?
        # in order to jump : (1) the alert must not have been addressed yet, (2) crossed the latency mark (just for consistency), and (3) must have suitable jump candidates
        if gs.pop_alert != previous_alert and curr_beat['jump_candidates'] != []:
            # make the jump
            jump_beat_index = np.random.choice(curr_beat['jump_candidates'])
            curr_beat = jukebox.beats[jump_beat_index]
            # window this signal and taper surrounding
            beat_buf = beat_window(curr_beat['buffer'])
            # taper_buffer_edges(jkbx_ptr, jkbx_ptr + len(beat_buf), 0.25)

            previous_alert = gs.pop_alert
        else:
            curr_beat = jukebox.beats[curr_beat['next']]
            beat_buf = curr_beat['buffer']

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

    # read tracks and genre tags in from csv\
    track_names = []
    genre_tags = []

    source_file_path = 'tracks/'

    ifile = open('info.csv', 'rb')
    reader = csv.reader(ifile)
    for row in reader:
        track_names.append(source_file_path + row[0])
        genre_tags.append(row[1])

    print track_names
    print genre_tags


    # preprocess
    if args.preprocess:
        print "Pre-processing.."
        param_dict_list = pre.preprocess(track_names, genre_tags)
        np.array(param_dict_list).dump("prep.dat")
        print "Finished Pre-processing."

    # realtime playback and modification
    if args.start:
        param_dict_list = np.load("prep.dat")
        modify_flag = threading.Event()
        finished_flag = threading.Event()

        t1 = threading.Thread(target=stream_audio, args=(track_names,genre_tags,param_dict_list,modify_flag, finished_flag, ))
        t1.daemon = True

        t2 = threading.Thread(target=modify_buffer, args=(param_dict_list, genre_tags,modify_flag, finished_flag, ))
        t2.daemon = True

        t1.start()

        t2.start()

        t1.join()
        t2.join()

