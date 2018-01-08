# All of the steps in the pipeline to extract the best representative sample for pitch shifting

# Input: Harmonic component that results from HPSS, sample rate
# Output: Audio Time series of representative sample

import librosa
import math 
import numpy as np
import fmp

################################
# UTILITIES
################################

# window size must be odd
def temporal_smoothing(chroma, window_size):
    m = int((window_size - 1) / 2.0)
    smooth_chroma = []
    for t_col in chroma:
        # zero pad with half window size
        padded_col = list(np.zeros(m)) + list(t_col) + list(np.zeros(m)) 
        new_col = []
        for i in range(m, len(padded_col) - m ):
            x_new = (1.0 / window_size) * np.sum(padded_col[ i-m : i+m+1])
            new_col.append(x_new)
        smooth_chroma.append(new_col)
        
    return np.array(smooth_chroma)

def num_segments_used(p, clip_length):
    if clip_length < p:
        return 1
    else:
        return math.floor(clip_length / p) + 1

################################
# SCORING FUNCTIONS
################################

# score function for length parameter
def l(x):
    if x >= 0 and x <= 1.0:
        return (math.exp((math.log(2))*x)) - 1
    if x > 1.0:
        return 1.0
    else:
        print "Error! Length cannot be negative."

#scoring function for vector dot product
def v(x, vector_dist):
    if len(vector_dist) == 1: # just one segment
        return 1.0
    return float(x - np.min(vector_dist)) / float(np.max(vector_dist) - np.min(vector_dist))

# scoring function for comparable energy    
# def c(x):
#     if x >= 0 and x <= 0.5:
#         return (math.exp((math.log(0.1) / 0.5) * x) )
#     if x > 0.5:
#         return 0.1
#     else:
#         print "Error! Length cannot be negative."
def c(x, monophony_dp):
    if len(monophony_dp) == 1: # just one segment
        return 1.0
    return float(x - np.min(monophony_dp)) / float(np.max(monophony_dp) - np.min(monophony_dp))


################################
# COMPUTE SCORES
################################

def compute_length_score(onset_lines, silent_segment_number):
    # compute length score
    lengths = []
    length_score = []
    for i in range(1, len(onset_lines)):
        time = librosa.frames_to_time(onset_lines[i]) - librosa.frames_to_time(onset_lines[i-1])
        lengths.append(time)
        length_score.append(l(time))

    for m in silent_segment_number:
        length_score[m] = 0

    return length_score

def compute_dp_score(chroma_transpose, onset_lines):
    # compute average vector dot product score
    unit_chroma = []
    for t_col in chroma_transpose:
        norm = np.linalg.norm(t_col)
        try:
            new_col = [float(val) / float(norm) for val in t_col]
        except ZeroDivisionError:
            new_col = np.zeros(len(t_col))
        unit_chroma.append(new_col)
    
    vector_dist = []
    for i in range(1, len(onset_lines)):
        seg_vec_dist = []
        for m in range(onset_lines[i-1] + 1, onset_lines[i]):
            prod = np.dot(unit_chroma[m],unit_chroma[m-1])
            seg_vec_dist.append(prod)
        # onset lines span just one chroma
        if len(seg_vec_dist) == 0:
            seg_vec_dist.append(1.0)
        # integrate dot products for a single score
        vector_dist.append(np.trapz(seg_vec_dist, dx = 1.0 / len(seg_vec_dist)))

    zeros = []
    for i, e in enumerate(vector_dist):
        if e == 0:
            vector_dist[i] = np.max(vector_dist)
            zeros.append(i)

    vector_score = [v(x, vector_dist) for x in vector_dist]
    for z in zeros:
        vector_score[z] = 0

    return vector_score

def compute_energy_score(chroma_transpose, onset_lines, silent_segment_number, tfactor=0.6):
    # compute unit lenght chroma vectors
    unit_chroma = []
    for t_col in chroma_transpose:
        norm = np.linalg.norm(t_col)
        try:
            new_col = [float(val) / float(norm) for val in t_col]
        except ZeroDivisionError:
            new_col = np.zeros(len(t_col))
        unit_chroma.append(new_col)

    # generate template with N overtones for each fundamental frequency: T
    alpha = 0.7
    T = np.zeros((12,12))
    for i in range(12):
        T[i] = fmp.make_chord_template([i], alpha)

    # dot the template with LCS Segment
    monophony_dp = []
    for i in range(1, len(onset_lines)):
        cont_segment = unit_chroma[onset_lines[i-1]:onset_lines[i]]
        f_freq = np.argmax(cont_segment[0])
        segment_energy_score = []
        for col in cont_segment:
            segment_energy_score.append(np.dot(T[f_freq], col))

        #compute integral value and then save
        monophony_dp.append(np.trapz(segment_energy_score, dx = 1.0 / len(segment_energy_score)))


    # zero out scores for silent segments
    monophony_score = [c(x, monophony_dp) for x in monophony_dp]
    for s in silent_segment_number:
        monophony_score[s] = 0 

    return monophony_score


# Compute the chroma, apply temporal smoothing, LCS mask, compute LCS onset lines
# NOTE: weights and padding percentage are built in for now
def extract_sample(sample_harmonic, sample_rate, num_pitches, window_size=15, n_fft=2048, hop_length=512, tfactor=0.6, multi_clip=False):
    # compute chroma and smooth
    C_cqt = librosa.feature.chroma_stft(y=sample_harmonic, sr=sample_rate, n_fft=2048, hop_length=512)
    smooth_ct = temporal_smoothing(C_cqt, window_size)

    # create LCS mask and fine onset lines
    chroma_transpose = smooth_ct.transpose()
    mask = []
    onset_lines  = []
    segment_pitch_list = []
    old_idx = -1
    for i, t_col in enumerate(chroma_transpose):
        idx = np.argmax(t_col)
        new_col = np.zeros(len(t_col))
        new_col[idx] = 1
        mask.append(new_col)
        if idx != old_idx:
            onset_lines.append(i)
            segment_pitch_list.append(idx)
        old_idx = idx

    # needs to be an onset line at the end
    onset_lines.append(len(chroma_transpose) - 1)
        
    mask = np.array(mask)

    # keep track of silent segments
    silent_segment_number = []
    for i in range(1, len(onset_lines)):
        if np.all(chroma_transpose[onset_lines[i-1]:onset_lines[i]] == 0):
            silent_segment_number.append(i-1)
            
    # create silence mask
    silence_mask  = np.zeros(len(chroma_transpose))
    for s in silent_segment_number:
        silence_mask[s] = 1

    length_score = compute_length_score(onset_lines, silent_segment_number)
    dp_score = compute_dp_score(chroma_transpose, onset_lines)
    comp_energy_score = compute_energy_score(chroma_transpose, onset_lines, silent_segment_number)

    # choose the victor
    weight_length = (1.0 / 3.0)
    weight_dp = (1.0 / 3.0)
    weight_en = (1.0 / 3.0)

    total_score = []
    for i in range(len(length_score)):
        composite_score = (weight_length * length_score[i]) + (weight_dp * dp_score[i]) + (weight_en * comp_energy_score[i])
        total_score.append(composite_score)

    # retrieve multiple clips and determine distribution

    # pitches per clip parameter p
    p = 10
    # threshold score for clip selection
    score_thresh = 0.95

    if multi_clip == True:
        num_seg = int(num_segments_used(p, num_pitches))
    else:
        num_seg = 1

    # pick num_seg clips above the threshold
    score_and_id = zip(total_score, range(len(total_score)))
    score_and_id = sorted(score_and_id, key=lambda x: x[0], reverse=True)

    output_samples = []
    for n in range(num_seg):
        if score_and_id[n][0] > score_thresh or n == 0:
            output_samples.append(score_and_id[n])
        else:
            # break and repeatedly use the top scoring segments - assign probability distribution only to these
            num_seg = n # however far we've come
            break

    # retrieve the clips and trim by 20%
    rep_samples_audio = []

    for s in output_samples:
        score, seg_idx = s
        onset_frame_left = onset_lines[seg_idx]
        onset_frame_right = onset_lines[seg_idx + 1]
        print (onset_frame_left, onset_frame_right)
        samp_left = librosa.frames_to_samples(onset_frame_left)[0]
        samp_right = librosa.frames_to_samples(onset_frame_right)[0]
        #rep_sample = dd_harmonic[samp_left:samp_right]
        
        samp_length = samp_right - samp_left
        trim_length = int(0.20 * samp_length)
        if trim_length % 2 != 0:
            trim_length+=1

        new_samp_left = samp_left + (trim_length / 2)
        new_samp_right = samp_right - (trim_length / 2)    
        new_rep_sample = sample_harmonic[new_samp_left:new_samp_right]
        
        rep_samples_audio.append((new_rep_sample, segment_pitch_list[seg_idx]))        

    #return (new_rep_sample, segment_pitch_list[idx])
    return (rep_samples_audio, num_seg)

