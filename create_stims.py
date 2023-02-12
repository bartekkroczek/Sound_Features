from misc.audio import Dict2Obj, get_sine_wave, get_white_noise
from pygame import mixer, quit
from scipy.io import wavfile
import wavio
import numpy as np

# WSF = 32768
# SAMPLING_RATE = 44100
#
# mixer.pre_init(SAMPLING_RATE, -16, 2, 512)
# mixer.init(SAMPLING_RATE, -16, 2, 512)
# mixer.set_num_channels(2)
#
# for freq in range(450, 460):
#     sound = get_sine_wave(freq=freq, sampling_rate=SAMPLING_RATE, wave_length=2000, wsf=WSF)
#     wavfile.write(f'audio_stims/{freq}.wav', SAMPLING_RATE, sound)
    
rate = 22050           # samples per second
T = 3                  # sample duration (seconds)
n = int(rate*T)        # number of samples
t = np.arange(n)/rate  # grid of time values

for f in range(300, 600):
    x = np.sin(2*np.pi * f * t)
    wavio.write(f"audio_stims/{f}.wav", x, rate, sampwidth=3)