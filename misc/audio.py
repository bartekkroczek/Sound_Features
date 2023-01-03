# import parallel
import random
from typing import Dict

import numpy as np
from psychopy import event, visual, core
from pygame import mixer
from scipy.io import wavfile


class Dict2Obj(object):
    """
    Quite self-explanatory. Syntactic sugar.
    """

    def __init__(self, **entries):
        self.__dict__.update(entries)

    def __getitem__(self, item):
        return self.__dict__[item]


def show_info(win: visual, msg: str, insert: Dict[str, str] = {}, font_name: str = 'arial', font_color: str = 'white',
              font_size: int = 20, font_max_width: int = 1000) -> None:
    """
    Clear way to show info messages on screen.
    :param win: psychopy.Window object, main experiment.
    :param msg: Message string to show.
    :param insert: Additional (usually generated in runtime) message, replaced '<--insert-->' in loaded file.
    :param font_name:
    :param font_color:
    :param font_size:
    :param font_max_width:
    :return: None.
    """
    if insert:
        for key, value in insert.items():
            msg.replace(key, value)
    msg = visual.TextStim(win, font=font_name, color=font_color, text=msg, height=font_size, wrapWidth=font_max_width)
    msg.draw()
    win.flip()
    event.waitKeys(keyList=['return', 'space'])
    win.flip()


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


