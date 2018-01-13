############################################
# Music Signaling Pipeline Prototype
#   automatic_sort: slot a genre-unlabeled
#       song into one of the four algorithm 
#       buckets
#
# Author: Ishwarya Ananthabhotla
############################################

import librosa
import numpy as np
import Remixatron as R


class Automatic_Sorting():
    def __init__(self):
        self.genre_dict = {'classical':['classical','rhythmless-instrumental', 'choir', 'avant-garde', 'soundtrack'], 'pop':['pop','country', 'folk', 'latin', 'gospel'], 
        'blues':['blues','rock', 'hip-hop', 'R&B', 'soul', 'strong-rhythmic', 'disco', 'rap'], 'jazz':['jazz','rhythmic-instrumental', 'electronic', 'easy-listening']}

    # see if the selected label remaps to any existing bucket
    def genre_mapping(self, genre_label):
        for category in self.genre_dict.keys():
            if genre_label in self.genre_dict[category]:
                return category

        return ""

    def is_rhythmic(self, track_audio, sr, threshold=0.4, heavy_threshold=0.7, success_percentage=0.5, heavy_percentage=0.25):
        harm, perc = librosa.effects.hpss(track_audio, margin=(1.0, 5.0))

        onset_env = librosa.onset.onset_strength(perc, sr=sr)
        tempo, beats = librosa.beat.beat_track(y=perc, sr=sr)
        times = librosa.frames_to_time(np.arange(len(onset_env)), sr=sr, hop_length=512)

        num_strong_beats = 0
        num_heavy_beats = 0

        for i, b in enumerate(beats):
            # get the corresponding onset env value
            t_b = times[b]
            on_f_b = librosa.time_to_frames([t_b], sr=sr)
            if librosa.util.normalize(onset_env)[on_f_b] >= threshold:
                num_strong_beats += 1
                if librosa.util.normalize(onset_env)[on_f_b] >= heavy_threshold:
                    num_heavy_beats +=1


        if num_strong_beats / float(len(beats)) >= success_percentage:
            # if rhythmic, count number of heavy beats
            if num_heavy_beats / float(len(beats)) >= heavy_percentage:
                # (is_rhythmic, is_strong_rhythmic)
                return (True,True)
            else:
                return (True,False)
        else:
            return (False,False)

    def is_repetitive(self, track_name, sr, tau=0.3):

        jukebox = R.InfiniteJukebox(filename=track_name, async=False)

        count = 0
        for i, b in enumerate(jukebox.beats):
            if b['jump_candidates'] != []:
                count +=1 

        if float(count) / len(jukebox.beats) >= tau:
            return True
        else:
            return False

    def categorize_audio(self, track_name, genre_label):
        cat = self.genre_mapping(genre_label)

        # assign a category ourselves 
        # NOTE: not indicative of genre, but type of modification to perform
        if cat == "":
            track_audio, sr = librosa.load(track_name)
            has_rhythm, has_strong_rhythm = self.is_rhythmic(track_audio, sr)
            if has_rhythm:
                if has_strong_rhythm:
                        return 'blues'
                else:
                    if self.is_repetitive(track_name,sr):  # tighten this up with clustering
                        return 'pop'
                    else:
                        return 'jazz'

                    # remove pop as a category for phase 2 of study
                    # return 'jazz'
            else:
                return 'classical'
        else:
            return cat

    def is_int(self, time_sig):
        try:
            int(time_sig)
            return True
        except ValueError:
            return False

    def estimate_timesig(self, track_name, time_sig):
        # TODO - Implementation
        if time_sig == "" or not self.is_int(time_sig):
            return '4'
        else:
            return time_sig


if __name__ == '__main__':
    # test a few clips

    a = Automatic_Sorting()
    # print a.categorize_audio('tracks/really_short_dvorak.mp3', 'blah')
    # print a.categorize_audio('tracks/really_short_jazz.wav', 'blah')
    # print a.categorize_audio('tracks/really_short_blues.wav', 'blah')
    print a.categorize_audio('tracks/Chaa_Rahi.mp3', 'blah')