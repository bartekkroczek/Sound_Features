# import parallel

import numpy as np


class Dict2Obj(object):
    """
    Quite self-explanatory. Syntactic sugar.
    """

    def __init__(self, **entries):
        self.__dict__.update(entries)

    def __getitem__(self, item):
        return self.__dict__[item]


def get_sine_wave(freq: int, sampling_rate: int, wave_length: int, wsf: int = 32768) -> np.array:
    """
    Helper function for sound generation, create sine wave function with given freq.
    :param freq: sine wave frequency
    :param sampling_rate:
    :param wave_length: how long sine wave should take
    :param wsf: WAVE Scaling factor, 16-bit PCM WAVE format operate with values in range [-32768, 32767]
    :return: Sine-wave with given freq.
    """
    sound_time = wave_length / 1000.0
    res = wsf * np.sin(2 * np.pi * np.arange(sampling_rate * sound_time) * freq / sampling_rate)
    return res.astype(np.int16)


def get_white_noise(mean: int, sampling_rate: int, wave_length: int, std: int = 1, wsf: int = 32768) -> np.array:
    """
    Helper function for sound generation, create sine wave function with given freq.
    :param std:
    :param mean:
    :param sampling_rate:
    :param wave_length: how long sine wave should take
    :param wsf: WAVE Scaling factor, 16-bit PCM WAVE format operate with values in range [-32768, 32767]
    :return: Sine-wave with given freq.
    """
    sound_time = wave_length // 1000
    res = wsf * np.random.normal(mean, std, size=sound_time * sampling_rate)
    return res.astype(np.int16)
