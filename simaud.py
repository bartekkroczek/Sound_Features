import numpy as np
import simpleaudio as sa
import time

# calculate note frequencies
A_freq = 440

for A_freq in range(400, 600, 5):
# get timesteps for each sample, T is note duration in seconds
    sample_rate = 44100
    T = 1.25
    t = np.linspace(0, T, int(T * sample_rate), False)

    # generate sine wave notes
    A_note = np.sin(A_freq * t * 2 * np.pi)
    transition_time = 0.05
    fall_down = np.linspace(1, 0, int(transition_time * sample_rate))
    rise_up = np.linspace(0, 1, int(transition_time * sample_rate))
    fall_down = np.hstack((rise_up, ([1] * (len(A_note) - 2* len(fall_down))), fall_down))

    # concatenate notes
    audio = A_note * fall_down
    # normalize to 16-bit range
    audio *= 32767 / np.max(np.abs(audio))
    # convert to 16-bit data
    audio = audio.astype(np.int16)

    # start playback
    play_obj = sa.play_buffer(audio, 1, 2, sample_rate)

    # wait for playback to finish before exiting
    play_obj.wait_done()
    time.sleep(1)