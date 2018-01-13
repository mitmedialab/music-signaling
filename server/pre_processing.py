#####################################
# Music Signaling Pipeline Prototype
#   Pre-Processing: read ALL tracks 
#   and compute dictionary of 
#   parameters
#
# Author: Ishwarya Ananthabhotla
######################################

import numpy as np
# matplotlib for displaying the output
import matplotlib.pyplot as plt
import matplotlib.style as ms

# and IPython.display for audio output
# import IPython.display
# from IPython.display import Audio

# Librosa for audio
import librosa
# And the display module for visualization
import librosa.display
from scipy import signal
import sklearn.cluster

# from VS pipeline
import extract
import os

# remixatron
import Remixatron as R

# TEST
import time

def preprocess(track_name, genre_tag, time_sig):
    track, sr = librosa.load(track_name)
    track, _ = librosa.effects.trim(track)
    if genre_tag == 'jazz':
        param_dict = feature_extract_jazz(track, sr)
    elif genre_tag == 'blues':
        param_dict = feature_extract_blues(track, sr, time_sig)
    elif genre_tag == 'classical':
        param_dict = feature_extract_classical(track, sr)
    elif genre_tag == 'pop':
        param_dict = feature_extract_pop(track_name, sr)
    else:
        # implement classification for misc
        print "Error: Genre Keyword"
        raise NotImplementedError

    return param_dict


###################################
# PROCESSING FOR TAGGED JAZZ
###################################

def window_signal(sig):
    return sig * signal.gaussian(len(sig), std=(2.0*len(sig)/ 8.0))

def boundaries_to_intervals(boundaries):
    intervals = []
    for i in range(len(boundaries) - 1):
        l = [boundaries[i], boundaries[i+1]]
        intervals.append(l)
    return np.array(intervals)
    

# return dict of features for jazz modifications
def feature_extract_jazz(jazz_track, sr, num_segments=8, seg_thresh=3):
    # segment boundaries
    mfcc = librosa.feature.mfcc(y=jazz_track, sr=sr)
    bounds = librosa.segment.agglomerative(mfcc, num_segments)
    sample_bounds = librosa.frames_to_samples(bounds)
    sample_intervals = boundaries_to_intervals(sample_bounds)
    
    # clean up short segments
    del_list = []
    for i, intr in enumerate(sample_intervals):
        if intr[1] - intr[0] < seg_thresh * sr:
            del_list.append(i)
    sample_intervals = np.delete(sample_intervals, del_list, axis=0)
    
    # corresponding intervals
    #   TODO: determine segment key/ progression
    shift_by = []
    
    # extracted subsample - using VS pipeline
    jazz_harm, jazz_perc = librosa.effects.hpss(jazz_track)
    try:
        rep_samples_audio, num_seg = extract.extract_sample(jazz_harm, sr, 1)
        signal_sample = rep_samples_audio[0][0]
    except:
        print "Could not extract sample from VS Pipeline, using default.."
        mdpt = int(len(jazz_harm)/2)
        signal_sample = jazz_harm[mdpt : mdpt + sr]
    
    # extract beats to overlay VS sample
    onset_env = librosa.onset.onset_strength(jazz_perc, sr=sr,
        aggregate=np.median)
    _, beats = librosa.beat.beat_track(onset_envelope=onset_env,
        sr=sr)
    beat_samples = librosa.frames_to_samples(beats)
    
    return {'bounds':sample_intervals, 'shift': shift_by, 'alert': signal_sample, 'beats': beat_samples}

########################################
# PROCESSING FOR TAGGED BLUES/ RHYTHMIC
########################################

def feature_extract_blues(blues_track, sr, current_timesig, onset_threshold=0.7):
    # get rhythm overlay
    hop_length = 512
    blues_harm, blues_perc = librosa.effects.hpss(blues_track, margin=(1.0, 5.0))
    onset_env = librosa.onset.onset_strength(blues_perc, sr=sr,
        aggregate=np.median)
    _, beats = librosa.beat.beat_track(onset_envelope=onset_env,
        sr=sr)
    
    times = librosa.frames_to_time(np.arange(len(onset_env)),
    sr=sr, hop_length=hop_length)
    
    prev_val = 0

    for i, b in enumerate(beats[:-1]):
        # get the corresponding onset env value
        t_b = times[b]
        on_f_b = librosa.time_to_frames([t_b], sr=sr, hop_length=hop_length)
        if librosa.util.normalize(onset_env)[on_f_b] >= prev_val:        
            prev_val = librosa.util.normalize(onset_env)[on_f_b]
            keep_beat_start = b
            keep_beat_end = beats[i+3]
            alert_start = i

    beat_start = librosa.frames_to_samples([keep_beat_start])[0]
    beat_end = librosa.frames_to_samples([keep_beat_end])[0]

          
    overlay_sample = blues_perc[beat_start:beat_end]
    
    # get beat samples
    beat_samples = librosa.frames_to_samples(beats, hop_length=hop_length)
    
    # get extracted subsample - using VS pipeline
    try:
        rep_samples_audio, num_seg = extract.extract_sample(blues_harm, sr, 1)
        signal_sample = rep_samples_audio[0][0]
    except:
        print "Could not extract sample from VS Pipeline, using default.."
        mdpt = int(len(blues_harm)/2)
        signal_sample = blues_harm[mdpt : mdpt + sr]

   
    return {'overlay': overlay_sample, 'beats': beat_samples, 'alert': signal_sample}

########################################
# PROCESSING FOR TAGGED CLASSICAL
########################################

def moving_average_filter(data, N):
    out = []
    c = int(N / 2.0)
    for i, n in enumerate(data):
        if i < c or i > len(data) - c:
            out.append(n)
        else:
            out.append(np.mean(data[i-c:i+c]))
            
    return np.array(out)

def normalized_tempo(tempo_curve, t_min=0.0, t_max=1.0):
    # d_max = np.max(tempo_curve)
    # d_min = np.min(tempo_curve)  
    d_max = 240.0  # bpm
    d_min = 0.0    # bpm
    normalized_tempo_curve = []
    for val in tempo_curve:
        normalized_tempo_curve.append( t_min + ((t_max - t_min) / (d_max - d_min)) * (val - d_min) )
    return np.array(normalized_tempo_curve)

def delay(tempo, d_min=0.5, d_max=1.0):
    delay_curve = []
    # t_max = np.max(tempo)    
    # t_min = np.min(tempo)
    t_max = 240.0 # bpm
    t_min = 0.0   # bpm
    for val in tempo:
        delay_curve.append( d_max + ((d_min - d_max) / (t_max - t_min)) * (val - t_min) ) 
    return np.array(delay_curve)

def echo_amplitude(amplitude, e_min=0.6, e_max=1.4):
    a_max = np.max(amplitude)
    a_min = np.min(amplitude)    
    echo_curve = []
    for val in amplitude:
        echo_curve.append( e_min + ((e_max - e_min) / (a_max - a_min)) * (val - a_min) )
    return np.array(echo_curve)

# number of segments should be proportional to track length and relevant to genre
def feature_extract_classical(classical_track, sr, low_proc=True, num_segments=10, seg_thresh=2, smooth_coeff=811):
    # SEGMENTATION
    # segments

    mfcc = librosa.feature.mfcc(y=classical_track, sr=sr)
    bounds = librosa.segment.agglomerative(mfcc, num_segments)
    sample_bounds = librosa.frames_to_samples(bounds)
    sample_intervals = boundaries_to_intervals(sample_bounds)
    
    # clean up short segments
    del_list = []
    for i, intr in enumerate(sample_intervals):
        if intr[1] - intr[0] < seg_thresh * sr:
            del_list.append(i)
    sample_intervals = np.delete(sample_intervals, del_list, axis=0)
    
    # TEMPO CHANGE
    # tempo curve
    onset_env = librosa.onset.onset_strength(classical_track, sr=sr)
    dtempo = librosa.beat.tempo(onset_envelope=onset_env, sr=sr,
                            aggregate=None)

    if not low_proc:
        tempo_curve = moving_average_filter(dtempo, smooth_coeff)
        normalized_tempo_curve = normalized_tempo(tempo_curve)
    
        # ECHO
        # echo amplitude
        lpf_amplitude = moving_average_filter(np.abs(classical_track), sr) # 1 sec - long filter
        echo_ampl_curve = echo_amplitude(lpf_amplitude)
        
        # delay curve
        delay_curve = delay(tempo_curve)
    else:
        normalized_tempo_curve = normalized_tempo(dtempo)
        echo_ampl_curve = None
        delay_curve = delay(dtempo)
        
    # EXTRACTED SAMPLE
    classical_harm = librosa.effects.harmonic(classical_track)
    try:
        rep_samples_audio, num_seg = extract.extract_sample(classical_harm, sr, 1)
        signal_sample = rep_samples_audio[0][0]
    except:
        print "Could not extract sample from VS Pipeline, using default.."
        mdpt = int(len(classical_harm)/2)
        signal_sample = classical_harm[mdpt : mdpt + sr]
    
    return {'bounds':sample_intervals, 'tempo': normalized_tempo_curve, 'echo':echo_ampl_curve, 'delay': delay_curve, 'alert':signal_sample}


########################################
# PROCESSING FOR TAGGED POP
########################################
    
def feature_extract_pop(track_name, sr, num_segments=8, num_clusters=3, seg_thresh=3):

    # return the jukebox object computed by the remixatron

    jukebox = R.InfiniteJukebox(filename=track_name, async=False)

    # CHANGES FOR STUDY PHASE 2
    # EXTRACTED SAMPLE
    pop_track, _ = librosa.load(track_name)
    try:
        rep_samples_audio, num_seg = extract.extract_sample(pop_track, sr, 1)
        signal_sample = rep_samples_audio[0][0]
    except:
        print "Could not extract sample from VS Pipeline, using default.."
        mdpt = int(len(pop_track)/2)
        signal_sample = pop_track[mdpt : mdpt + sr]

    # NOTE: this is a feature in the infinite jukebox implementation; but it comes across as a modification 

    for i in range(len(jukebox.beats)):
        if i == len(jukebox.beats) - 1:
            jukebox.beats[i]['next'] = None
        elif jukebox.beats[i]['next'] != jukebox.beats[i]['id'] + 1:
            jukebox.beats[i]['next'] = jukebox.beats[i]['id'] + 1
        else:
            pass

    return {'jukebox': jukebox, 'alert':signal_sample}


if __name__ == "__main__":
    pass
    
    # POP TEST
    # param_dict = param_dict_list[0]
    # print param_dict['bounds']
    # print param_dict['label']
    # print param_dict['beats']

    # JAZZ TEST
    # param_dict = param_dict_list[0]
    # print param_dict['bounds']
    # print param_dict['shift']
    # print param_dict['beats']

    # CLASSICAL TEST
    # param_dict = param_dict_list[0]
    # print param_dict['tempo']
    # print param_dict['echo']
    # print param_dict['delay']

    # BLUES TEST
    # param_dict = param_dict_list[0]
    # print param_dict['overlay']
    # print param_dict['beats']
    

