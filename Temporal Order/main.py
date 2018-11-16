from Adaptives.NUpNDown import NUpNDown
from misc.screen_misc import get_frame_rate, get_screen_res
import numpy as np
import time
import pygame
from scipy.io import wavfile
import codecs
import yaml
import atexit
from psychopy import visual, event, logging, gui, core


class Dict2Obj:
    def __init__(self, **entries):
        self.VOLUME = None
        self.SAMPLING_RATE = None
        self.WSF = None
        self.__dict__.update(entries)


@atexit.register
def save_beh_results():
    with open(join('results', PART_ID + '_beh.csv'), 'w') as beh_file:
        beh_writer = csv.writer(beh_file)
        beh_writer.writerows(RESULTS)
    logging.flush()


def read_text_from_file(file_name, insert=''):
    """
    Method that read message from text file, and optionally add some
    dynamically generated info.
    :param file_name: Name of file to read
    :param insert:
    :return: message
    """
    if not isinstance(file_name, str):
        logging.error('Problem with file reading, filename must be a string')
        raise TypeError('file_name must be a string')
    msg = list()
    with codecs.open(file_name, encoding='utf-8', mode='r') as data_file:
        for line in data_file:
            if not line.startswith('#'):  # if not commented line
                if line.startswith('<--insert-->'):
                    if insert:
                        msg.append(insert)
                else:
                    msg.append(line)
    return ''.join(msg)


def check_exit(key='f7'):
    stop = event.getKeys(keyList=[key])
    if stop:
        abort_with_error('Experiment finished by user! {} pressed.'.format(key))


def show_info(win, file_name, insert=''):
    """
    Clear way to show info message into screen.
    :param win:
    :return:
    """
    msg = read_text_from_file(file_name, insert=insert)
    msg = visual.TextStim(win, color=STIM_COLOR, text=msg, height=STIM_SIZE - 10, wrapWidth=SCREEN_RES['width'])
    msg.draw()
    win.flip()
    key = event.waitKeys(keyList=['f7', 'return', 'space', 'left', 'right'] + KEYS)
    if key == ['f7']:
        abort_with_error('Experiment finished by user on info screen! F7 pressed.')
    win.flip()


def abort_with_error(err):
    logging.critical(err)
    raise Exception(err)

# Preparation
conf = yaml.load(open('config.yaml', 'r'))
conf = Dict2Obj(**conf)

s1 = (conf.WSF * np.sin(2 * np.pi * np.arange(conf.SAMPLING_RATE * duration) * f1 / conf.SAMPLING_RATE)).astype(np.int16)
s2 = (conf.WSF * np.sin(2 * np.pi * np.arange(conf.SAMPLING_RATE * duration) * f2 / conf.SAMPLING_RATE)).astype(np.int16)

wavfile.write('s1.wav', conf.SAMPLING_RATE, s1)
wavfile.write('s2.wav', conf.SAMPLING_RATE, s2)

pygame.mixer.pre_init(conf.SAMPLING_RATE, -16, 2, 512)
pygame.mixer.init(conf.SAMPLING_RATE, -16, 2, 512)
pygame.init()

s1 = pygame.mixer.Sound('s1.wav')
s2 = pygame.mixer.Sound(s2)
s1.set_volume(conf.VOLUME)
s2.set_volume(conf.VOLUME)
pygame.mixer.set_num_channels(2)
s1.play()
time.sleep(2)
s2.play()
time.sleep(4)
