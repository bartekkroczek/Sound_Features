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


def present_learning_sample(win: visual, soa: int, standard_freq: float, conf: Dict2Obj) -> None:
    """
   Simple func for playing sound with relevant label. Useful for learning.
    Args:
        conf:
        standard_freq:
        soa:
        win: Current experiment window.

    Returns:
        Nothing.
    """
    if soa < 0:
        raise ValueError('Learning phase soa must be positive.')
    label = visual.TextStim(win, color=conf.FONT_COLOR, height=conf.FONT_SIZE, wrapWidth=conf.SCREEN_RES['width'])

    soa = random.choice([-soa, soa])
    freqs = [standard_freq, standard_freq + soa]
    random.shuffle(freqs)
    first_sound_freq, sec_sound_freq = freqs
    msg = "Pierwszy dzwi\u0119k wy\u017Cszy" if first_sound_freq > sec_sound_freq else "Pierwszy dzwi\u0119k ni\u017Cszy"

    first_sound = get_sine_wave(freq=first_sound_freq, sampling_rate=conf.SAMPLING_RATE, wave_length=5 * conf.TIME,
                                wsf=conf.WSF)
    wavfile.write('learning_first_sound.wav', conf.SAMPLING_RATE, first_sound)
    first_sound = mixer.Sound('learning_first_sound.wav')
    sec_sound = get_sine_wave(freq=sec_sound_freq, sampling_rate=conf.SAMPLING_RATE, wave_length=5 * conf.TIME,
                              wsf=conf.WSF)
    wavfile.write('learning_sec_sound.wav', conf.SAMPLING_RATE, sec_sound)
    sec_sound = mixer.Sound('learning_sec_sound.wav')

    label.setText(msg)
    label.draw()
    win.flip()
    core.wait(conf.TRAIN_SOUND_TIME / 1000.0)
    first_sound.play()
    core.wait(conf.TRAIN_SOUND_TIME / 1000.0)
    first_sound.stop()
    core.wait(2 * conf.TRAIN_SOUND_TIME / 1000.0)
    sec_sound.play()
    core.wait(conf.TRAIN_SOUND_TIME / 1000.0)
    sec_sound.stop()
    win.flip()
    core.wait(2)
