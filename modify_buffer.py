########################################
# Music Signaling Pipeline Prototype
#	Buffer Modification: edit the audio
# 	buffer to introduce signal in 
#	realtime
#
# Author: Ishwarya Ananthabhotla
#########################################

# global buffer in settings file
# global sr

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.style as ms

import IPython.display
from IPython.display import Audio

import librosa
import librosa.display
from scipy import signal
import sklearn.cluster

import global_settings as gs

import time

import pydub

# modify global buffer in place 
#
# \___/
#
def taper_buffer_edges(range_start, range_end, fade_time, high_end=1.0, low_end=0.3):
	fade_samples = int(fade_time * gs.sr)
	# ramp down
	ramp_down = np.array([(-1.0 * (high_end - low_end) / fade_samples) * x + high_end for x in range(fade_samples)])
	gs.audio_buffer[range_start - fade_samples: range_start] *= ramp_down 

	#ramp up 
	ramp_up = np.array([(-1.0 * (low_end - high_end) / fade_samples) * x + low_end for x in range(fade_samples)])
	gs.audio_buffer[range_end: range_end + fade_samples] *= ramp_up

	return 


# modify global buffer in place 
#  ___
# /   \
#
def square_window(sig, high_end=1.0, low_end=0.5):

	fade_samples = int(len(sig) * (1.0 / 8.0))

	# ramp up
	ramp_up = np.array([(-1.0 * (low_end - high_end) / fade_samples) * x + low_end for x in range(fade_samples)])
	sig[:fade_samples] *= ramp_up

	#ramp down
	ramp_down = np.array([(-1.0 * (high_end - low_end) / fade_samples) * x + high_end for x in range(fade_samples)])
	sig[-fade_samples:] *= ramp_down

	return sig

def window(sig):
	return sig * signal.gaussian(len(sig), std=(2.0*len(sig)/ 8.0))


def modify_jazz(level, param_dict, start, dur=4, segment=False):
	# TODO: shift-by
	print "Jazz modification begun.."

	if segment:
		# use pre-computed segment boundaries
		start_bounds = param_dict['bounds'][:,0]
		nearest_bound = start_bounds[np.where(start_bounds >= start)][0]
	else:
		# use pre-computer beat boundaries
		beats = param_dict['beats']
		nearest_beat = beats[np.where(beats >= start)][0:2]
		nearest_bound = nearest_beat[0]

	# pitch shift sample
	if level == 0:
		shift_cut = 1.0 * librosa.effects.pitch_shift(gs.audio_buffer[nearest_bound: nearest_bound + (dur * gs.sr)], gs.sr, n_steps=4)
		gs.audio_buffer[nearest_bound: nearest_bound + (dur * gs.sr)] = window(shift_cut) + gs.audio_buffer[nearest_bound: nearest_bound + (dur * gs.sr)]

	elif level == 1:
		shift_cut = 1.4 * librosa.effects.pitch_shift(gs.audio_buffer[nearest_bound: nearest_bound + (dur * gs.sr)], gs.sr, n_steps=6.5)
		gs.audio_buffer[nearest_bound: nearest_bound + (dur * gs.sr)] = window(shift_cut) + gs.audio_buffer[nearest_bound: nearest_bound + (dur * gs.sr)]
	else:
		# issue sampled alert
		alert = param_dict['alert']
		beat_size = nearest_beat[1] - nearest_beat[0]
		if len(alert) >= beat_size:
			alert_samp = alert[:beat_size]
		else:
			alert_samp = np.concatenate((window(alert),np.zeros((beat_size - len(alert)))))
		gs.audio_buffer[nearest_beat[0]:nearest_beat[1]] = alert_samp

	print "Jazz modification completed.."
	return True


def modify_classical(level, param_dict, start, dur=4, sig_dur=4, segment=False):
	print "Classical modification begun.."

	# snap to segment or start marker
	if segment:
		# use pre-computed segment boundaries
		start_bounds = param_dict['bounds'][:,0]
		nearest_bound = start_bounds[np.where(start_bounds >= start)][0]
	else:
		# simply use start marker
		nearest_bound = start

	# level 0 - tempo change -- volume envelope needs fixing!!
	if level == 1:
		offset = 0.8
		# in frames, conversion to samples required
		tempo_curve = param_dict['tempo']
		nearest_bound_in_frame = librosa.samples_to_frames([nearest_bound])[0]
		tempo_factor = tempo_curve[nearest_bound_in_frame]

		# change dur to account for tempo factor
		dur = int(np.ceil(dur * (tempo_factor + offset)))

		clip = gs.audio_buffer[nearest_bound : nearest_bound + (dur*gs.sr)]
		shrink = librosa.effects.time_stretch(clip, offset + tempo_factor)
		
		remainder = np.concatenate((square_window(shrink), gs.audio_buffer[nearest_bound + (dur*gs.sr):]))
		
		gs.audio_buffer[nearest_bound : nearest_bound + len(remainder)] = remainder
		
		gs.audio_buffer[-1 * (len(clip) - len(shrink)):] = 0

		taper_buffer_edges(nearest_bound, nearest_bound + len(shrink), 1.0)
		

		# if stretch instead of shrink		
		# gs.audio_buffer = np.concatenate((gs.audio_buffer, np.zeros(len(stretch) - len(clip))))
		# gs.audio_buffer[nearest_bound:] = np.concatenate( (window(stretch), window(gs.audio_buffer[nearest_bound + (dur*gs.sr):])) )

	# level 1 - echo with delay
	elif level == 0:
		offset = int(gs.sr / 2.0)
		echo_amp_curve = param_dict['echo']
		echo_amp = echo_amp_curve[nearest_bound]
		delay_curve = param_dict['delay']
		nearest_bound_in_frame = librosa.samples_to_frames([nearest_bound])[0]
		delay_in_secs = delay_curve[nearest_bound_in_frame]
		delay_in_samps = int(delay_in_secs * gs.sr)
		print delay_in_samps
		delay_in_samps += offset
		print delay_in_samps
		clip = gs.audio_buffer[nearest_bound : nearest_bound + (dur*gs.sr)]
		gs.audio_buffer[nearest_bound + delay_in_samps: nearest_bound + delay_in_samps + (dur*gs.sr)] += ((0.8*echo_amp) * window(clip))

	# level 2 - alert sample
	else:
		# issue sampled alert
		alert = param_dict['alert']
		if len(alert) > sig_dur * gs.sr:
			alert = alert[:sig_dur * gs.sr]
		remainder = np.concatenate((square_window(alert), gs.audio_buffer[nearest_bound + len(alert):]))		
		gs.audio_buffer[nearest_bound:nearest_bound + len(remainder)] = remainder
		taper_buffer_edges(nearest_bound, nearest_bound + len(alert), 1.0, low_end=0.0)

	print "Classical modification completed.."
	return True

def modify_pop(level, param_dict, start, dur=2):
	# write the new start value to the pop song alert flag
	# jukebox thread should change the next beat
	gs.pop_alert = start

	return True


def modify_blues(level, param_dict, start):
	print "Blues modification begun.."

	start_time = time.time()

	N = 4
	beats = param_dict['beats']
	nearest_beat = beats[np.where(beats >= start)][0:N]
	
	if level == 0 or level == 1:
		# 4 beats, equal volume

		if level == 0:
			vol = 1.8
		else:
			vol = 2.0		

		r_sample = []
		overlay = param_dict['overlay']
		for i in range(len(nearest_beat) - 1):
			beat_size = nearest_beat[i+1] - nearest_beat[i]
			if len(overlay) >= beat_size:
				beat_samp = overlay[:beat_size]
			else:
				beat_samp = np.concatenate((window(overlay),np.zeros((beat_size - len(overlay)))))

			r_sample = np.concatenate((r_sample, beat_samp))
		gs.audio_buffer[nearest_beat[0]:nearest_beat[N-1]] = (vol * r_sample) + gs.audio_buffer[nearest_beat[0]:nearest_beat[N-1]]

	else:
		# issue sampled alert
		alert = param_dict['alert']
		beat_size = nearest_beat[1] - nearest_beat[0]
		if len(alert) >= beat_size:
			alert_samp = window(alert[:beat_size])
		else:
			alert_samp = np.concatenate((window(alert),np.zeros((beat_size - len(alert)))))
		gs.audio_buffer[nearest_beat[0]:nearest_beat[1]] = alert_samp #+ gs.audio_buffer[nearest_beat[0]:nearest_beat[1]]

	print "Blues modification ended.."
	return True

if __name__ == "__main__":
	# timing specs on each module here
	pass