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
import librosa
import time
import threading
# import multiprocessing
import os
import argparse
import csv
import socket
import collections
import pickle

import global_settings as gs
import pre_processing as pre
import modify_buffer as mb
import automatic_sort as AS

# THREAD 1: Write audio from buffer to stream in chunks
def stream_audio(track_names, genre_tags, param_dict_list, modify_flag, end_stream, connection):
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
        gs.audio_buffer, _ = librosa.effects.trim(gs.audio_buffer)
        gs.song_index = i

        gs.ptr = 0L

        # continue modifier thread
        modify_flag.set()
        print "New song loaded!"        

        # termination signal from other thread
        while gs.ptr < len(gs.audio_buffer) and not end_stream.is_set():

            # convert to string
            out_data = gs.audio_buffer[gs.ptr: gs.ptr + (hop_size_bytes * 16)]
            out_data = out_data.astype(np.float32).tostring()

            # write to stream
            stream.write(out_data)
            gs.ptr += (hop_size_bytes * 16)

            print "ptr: ", gs.ptr

        if not end_stream.is_set() and i != len(track_names)-1:
            # make modifier thread wait while we load new song
            modify_flag.clear()
            gs.new_song = True
            print "Loading new song.."
            # time.sleep(1) # wait for buffer thread to reset
        else:
            print "Cleaning up and closing.."
            break

            
    # stop stream
    stream.stop_stream()
    stream.close()

    p.terminate()

    # termination signal from this thread
    gs.msg_q.append('end:0')
    print "Thank you for listening!"
    return


# THREAD 2: Monitor socket for flags and call modifiers
def modify_buffer(param_dict, current_genre, current_timesig, level, new_song, dur=4, buff_time=2, pop_buff_time=3, msg_length=5):
    # modification settings
    hop_size_bytes = 1024 * 4 # bytes
    done_flag = False
    count = 0
    start_jukebox = False
    msg = ''

    
    if current_genre == 'pop':
        start = gs.ptr + (pop_buff_time * (hop_size_bytes * 16))
    else:
        start = gs.ptr + (buff_time * (hop_size_bytes * 16))                

    if start + (dur * gs.sr) >= len(gs.audio_buffer):
        print "Not enough audio left to modify. Sleeping.."
        return

    if current_genre == 'jazz':
        print "Modification Signaled.."
        done_flag = mb.modify_jazz(level, param_dict, start)
    elif current_genre == 'classical':
        print "Modification Signaled.."
        done_flag = mb.modify_classical(level, param_dict, start)
    elif current_genre == 'blues':
        print "Modification Signaled.."
        done_flag = mb.modify_blues(level, param_dict, start, current_timesig)
    elif current_genre == 'pop':
        if new_song:
            t3 = threading.Thread(target=start_jukebox_process, args=(param_dict, start, current_timesig, ))
            t3.daemon = True          
            t3.start()

        done_flag = mb.modify_pop(level, param_dict, start)

    else:
        raise NotImplementedError 


    return

def start_jukebox_process(param_dict, start, current_timesig):

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
    beat_multiple = int(current_timesig)

    # compute list of beat samples
    beat_samples = np.array([b['start']*jukebox.sample_rate for b in jukebox.beats], dtype=int)

    # get ordinal beat closest to start, set jkbx ptr to its sample
    nearest_beat_index = np.argwhere(beat_samples >= start)[0][0]
    curr_beat = jukebox.beats[nearest_beat_index]
    beat_buf = curr_beat['buffer']
    jkbx_ptr = 0L  

    jkbx_ptr = int(curr_beat['start'] * gs.sr)

    # GUT
    gs.audio_buffer[jkbx_ptr:] = 0

    # settings that force a jump
    previous_alert = None

    # min beats before we have to jump, 10% of beats in the song
    max_beats_between_jumps = int(round(len(jukebox.beats) * .1))

    beats_since_last_jump = 0

    recent_seg_depth = int(round(jukebox.segments * .25))
    recent_seg_depth = max( recent_seg_depth, 1 )
    recent_segments = collections.deque(maxlen=recent_seg_depth)

    while jkbx_ptr < len(gs.audio_buffer):
        # insert current beat
        if jkbx_ptr + len(beat_buf) > len(gs.audio_buffer):
            # fill balance with silence
            gs.audio_buffer[-1 * (len(gs.audio_buffer) - jkbx_ptr): ] = 0
            # gs.audio_buffer = np.concatenate((gs.audio_buffer, np.zeros(jkbx_ptr + len(beat_buf) - len(gs.audio_buffer))))
            print "Finished Jukebox thread.."
            return

        gs.audio_buffer[jkbx_ptr: jkbx_ptr + len(beat_buf)] = beat_buf
        jkbx_ptr += len(beat_buf)

        # subtlety settings
        # only jump on down beat for level 0
        if gs.pop_subtlety == 0:
            is_jump_beat = (curr_beat['id'] % beat_multiple == 0) or (beats_since_last_jump >= max_beats_between_jumps)
        # jump on any other beat for level 1 and level 2
        else:
            is_jump_beat = (not curr_beat['id'] % beat_multiple == 0) or (beats_since_last_jump >= max_beats_between_jumps)

        # jump next or sequential next?
        # in order to jump : (1) the alert must not have been addressed yet, (2) crossed the latency mark (just for consistency), and (3) must have suitable jump candidates

        if gs.pop_alert != previous_alert and gs.pop_subtlety == 2:
            # CHANGE FOR STUDY PHASE 2:
            print "JUMPING AT --> JUKEBOX PTR: ", jkbx_ptr

            curr_beat = jukebox.beats[curr_beat['next']]

            alert = param_dict['alert']

            if len(curr_beat['buffer']) < gs.sr:
                alert_length = int(np.floor(gs.sr / len(curr_beat['buffer']))) * len(curr_beat['buffer'])
            else:
                alert_length = len(curr_beat['buffer'])            
            
            alert = alert[:alert_length]


            beat_buf = alert

            previous_alert = gs.pop_alert

            beats_since_last_jump += 1

            # sleep only for non-jump beats
            time.sleep(0.35)

        elif gs.pop_alert != previous_alert and curr_beat['jump_candidates'] != [] and is_jump_beat:
            # where is jukebox ptr in relation to buffer pointer?
            print "JUMPING AT --> JUKEBOX PTR: ", jkbx_ptr

            if gs.pop_subtlety == 0:
                filtered_candidates = [c for c in curr_beat['jump_candidates'] if jukebox.beats[c]['segment'] not in recent_segments]
                if filtered_candidates == []: # if we can't maintain this rule, relax it
                    filtered_candidates = curr_beat['jump_candidates']    
            else:
                filtered_candidates = curr_beat['jump_candidates']

            # make the jump
            jump_beat_index = np.random.choice(filtered_candidates)
            curr_beat = jukebox.beats[jump_beat_index]
            # window this signal and taper surrounding
            beat_buf = beat_window(curr_beat['buffer'])
            # taper_buffer_edges(jkbx_ptr, jkbx_ptr + len(beat_buf), 0.25)

            previous_alert = gs.pop_alert

            beats_since_last_jump = 0
        
        else:
            curr_beat = jukebox.beats[curr_beat['next']]
 
            beat_buf = curr_beat['buffer']

            beats_since_last_jump += 1

            # sleep only for non-jump beats
            time.sleep(0.35)

        if curr_beat['segment'] not in recent_segments:
            recent_segments.append(curr_beat['segment'])
        

    print "Finished Jukebox thread.."
    return

# convert between int bytes format and float 32 samples
def convert(in_buffer):
    return (in_buffer.T.astype(np.float32)) /  np.iinfo(np.int16).max

def start_server(host='localhost', port=8089):
    # server settings
    serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    serversocket.bind((host, port))
    serversocket.listen(1) # become a server socket, maximum 5 connections
    print "Please begin client application: "
    connection, address = serversocket.accept()
    connection.settimeout(2)
    return connection, serversocket

def preprocess(source_file_path='tracks/', list_file='info.csv'):
    # read tracks, genre tags, time signatures in from csv
    track_names = []
    genre_tags = []
    time_sigs = []

    ifile = open(list_file, 'rb')
    reader = csv.reader(ifile)

    for row in reader:
        track_names.append(source_file_path + row[0])
        genre_tags.append(row[1])
        time_sigs.append(row[2])

    print "Metadata Read In: "
    print "----------------------"
    print track_names
    print genre_tags
    print time_sigs
    print "----------------------"

    print "Pre-processing.."
    # check for missing genre tags and time sigs
    a = AS.Automatic_Sorting()
    for i in range(len(track_names)):
        genre_tags[i] = a.categorize_audio(track_names[i], genre_tags[i])

    for i, ts in enumerate(time_sigs):
        if ts == "":
            time_sigs[i] = a.estimate_timesig(track_names[i])

    print "Final Estimated Metadata: "
    print "----------------------"
    print track_names
    print genre_tags
    print time_sigs
    print "----------------------"

    param_dict_list = pre.preprocess(track_names, genre_tags, time_sigs)
    np.array(param_dict_list).dump("prep.dat")

    pickle.dump((track_names, genre_tags, time_sigs), open('meta.pkl', 'wb'))
    print "Finished Pre-processing."




if __name__ == "__main__":

    # command line arg parser
    parser = argparse.ArgumentParser()
    parser.add_argument('-preprocess', action='store_true')
    parser.add_argument('-start', action='store_true')
    args = parser.parse_args()


    # initialize global variables 
    gs.init()

    # preprocess
    if args.preprocess:
        preprocess(source_file_path='tracks/', list_file='info.csv')

    # realtime playback and modification
    if args.start:
        param_dict_list = np.load("prep.dat")
        track_names, genre_tags, time_sigs = pickle.load(open('meta.pkl', 'rb'))

        # initialize server/ client
        try:
            connection, socket = start_server()
        except:
            print "Could not connect. Aborting.."
            sys.exit(0)

        
        modify_flag = threading.Event()
        end_stream = threading.Event()
        
        t1 = threading.Thread(target=stream_audio, args=(track_names,genre_tags,param_dict_list,modify_flag, end_stream, connection, ))
        t1.daemon = True

        t1.start()
        time.sleep(5)
        
        msg_length=5

        gs.new_song = True

        # terminate monitor thread if stream thread finishes
        while t1.is_alive():
            try:
                msg = connection.recv(msg_length) 
                gs.msg_q.appendleft(msg)
            except:
                pass

           
            # and we are allowed to modify
            if modify_flag.is_set():
                # if there is a msg
                if len(gs.msg_q) > 0:
                    msg = gs.msg_q.pop()
                    if len(msg) == msg_length:
                        header, level = msg.split(':')
                        if header == 'end':
                            # trigger the end of stream thread
                            end_stream.set()
                            break
                        elif header == 'msg':
                            level = int(level)

                            try:
                                is_alive = mod_thread.isAlive()
                            except NameError:
                                is_alive = False

                            if not is_alive:
                                mod_thread = threading.Thread(target=modify_buffer, args=(param_dict_list[gs.song_index], genre_tags[gs.song_index],time_sigs[gs.song_index],level,gs.new_song, ))
                                mod_thread.daemon = True
                                mod_thread.start()
                                gs.new_song = False
                        else:
                            print "Message Error."
                    else:
                            print "Message Error." 

                    
            # we are not allowed to modify, during song load
            else:
                gs.new_song = True
                time.sleep(5)

        connection.close()
        socket.shutdown(1)
        socket.close()

        


