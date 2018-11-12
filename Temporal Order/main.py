# from Adaptives.NUpNDown import NUpNDown
# from misc.screen_misc import get_screen_res, get_frame_rate
import pyaudio
import numpy as np
import time
import pygame
import wave
# audio_out = pyaudio.PyAudio()
volume = 0.5  # range [0.0, 1.0]
fs = 44100  # sampling rate, Hz, must be integer
duration = 4.0  # in seconds, may be float
f1 = 700.0  # sine frequency, Hz, may be float
f2 = 800.0
# generate samples, note conversion to float32 array
pygame.mixer.pre_init(fs, -16, 2, 4096)
pygame.mixer.init(fs, -16, 2, 4096)
pygame.init()
s1 = (np.sin(2 * np.pi * np.arange(fs * duration) * f1 / fs)).astype(np.float32)
s2 = (np.sin(2 * np.pi * np.arange(fs * duration) * f2 / fs)).astype(np.float32)
print(s1, s1)
from scipy.io import wavfile
wavfile.write('s1.wav', fs, s1)
wavfile.write('s2.wav', fs, s2)
s1 = pygame.mixer.Sound(s1)
s2 = pygame.mixer.Sound(s2)
pygame.mixer.set_num_channels(2)
s1.play()
time.sleep(2)
s2.play()
time.sleep(2)
#
# # for paFloat32 sample values must be in range [-1.0, 1.0]
# stream1 = audio_out.open(format=pyaudio.paFloat32,
#                         channels=1,
#                         rate=fs,
#                         output=True)
#
# stream2 = audio_out.open(format=pyaudio.paFloat32,
#                          channels=1,
#                          rate=fs,
#                          output=True)
# # play. May repeat with different volume values (if done interactively)
# stream1.write(s1)
# # time.sleep(1)
# stream2.write(s2)
# stream2.stop_stream()
# stream2.close()
# stream1.stop_stream()
# stream1.close()
#
# audio_out.terminate()
#