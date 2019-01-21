#!/usr/bin/env python3
"""
Global desc.
"""

import atexit
import csv
import gettext
import os
import random
import shutil
import time
from os.path import join
from typing import List

import yaml
from psychopy import visual, event, logging, gui, core
from pygame import mixer, quit
from scipy.io import wavfile

from Adaptives.NUpNDown import NUpNDown
from misc.helpers import Dict2Obj, show_info, get_sine_wave
from misc.screen_misc import get_frame_rate, get_screen_res

global PART_ID, RES_DIR  # Used in case of error on @atexit, that's why it must be global

RESULTS = [['PART_ID', 'Trial', 'Proc_version', 'Exp', 'Key', 'Corr', 'SOA', 'Reversal', 'Level', 'Rev_count', 'Lat']]


@atexit.register  # decorator, func will be called ALWAYS when experiment will be closed, even with error.
def safe_quit() -> None:
    """
    Save beh results, logs, safety ends all frameworks.
    :return:
    """
    if 'PART_ID' not in globals():  # Nothing initialised yet, so just turn stuff off.
        raise Exception('No PART_ID in  globals(). Nothing to close.')
    fname = PART_ID + "_" + time.strftime("%Y-%m-%d__%H_%M_%S", time.gmtime()) + '_beh.csv'
    with open(join(RES_DIR, 'beh', fname), 'w') as beh_file:
        beh_writer = csv.writer(beh_file)
        beh_writer.writerows(RESULTS)
    logging.flush()
    win.close()
    core.quit()
    quit()


def present_learning_sample(win: visual, label: visual.TextStim, sample: List[mixer.Sound]) -> None:
    """
    Simple func for playing sound with relevant label. Useful for learning.
    :param win: Current experiment window.
    :param label: Sound description.
    :param sample: Sound to present.
    :return:
    """
    label.setText(sample[0])
    label.draw()
    win.callOnFlip(sample[1].play)
    win.flip()
    core.wait(conf.TRAIN_SOUND_TIME / 1000.0)
    sample[1].stop()
    win.flip()
    core.wait(conf.BREAK / 1000.0)


def cmp_vol(soa: int, sound: mixer.Sound, ans_lbs: List[visual.TextStim], feedback: bool) -> [float, bool, str]:
    """
    Single trial presented for participant.

    :param soa: Time between first and second sound. Can be interpreted as difficulty level.
    :param sound: Standard sound, baseline for comparsion.
    :param ans_lbs: List of labels to display in the time of trial.
    :param feedback: Show feedback or no? (usually True on training)
    :return: [Reaction time, answer correctness, key pressed]
    """
    # == Phase 0: Preparation ==
    key = list()
    t = conf.TIME / 1000.0
    soa = soa / 100.0
    for label in ans_lbs:
        label.draw()

    soa = random.choice([-soa, soa])
    standard_first = random.choice([True, False])
    standard_lauder = soa < 0

    if standard_first:
        first_volume, second_volume = conf.VOLUME, conf.VOLUME + soa
    else:
        first_volume, second_volume = conf.VOLUME + soa, conf.VOLUME
    # == Phase 1: Stimuli presentation
    sound.set_volume(first_volume)
    sound.play()
    time.sleep(t)
    sound.stop()
    logging.info("FIRST SOUND VOL: {}".format(sound.get_volume()))
    time.sleep(conf.BREAK / 1000.0)

    sound.set_volume(second_volume)
    sound.play()
    response_clock.reset()  # for rt measure, reset when second sound starts
    timer.reset(t=t)  # reverse timer from TIME to 0.
    event.clearEvents()
    win.flip()
    while timer.getTime() > 0:  # Handling responses when sounds still playing
        key = event.getKeys(keyList=[conf.FIRST_SOUND_KEY, conf.SECOND_SOUND_KEY])
        if key:
            rt = response_clock.getTime()
            win.flip()
            break

    sound.stop()

    logging.info("SECOND SOUND VOL: {}".format(sound.get_volume()), )
    # Phase 2: No reaction while stimuli presented
    if not key:  # no reaction when sound was played, wait some more.
        key = event.waitKeys(maxWait=conf.RTIME / 1000.0, keyList=[conf.FIRST_SOUND_KEY, conf.SECOND_SOUND_KEY])
        rt = response_clock.getTime()

    # Phase 3: Timeout handling
    timeout = (len(key) == 0) if key else True  # Still no reaction => Timeout
    win.flip()  # remove labels from screen

    if not timeout:
        if standard_first and standard_lauder:
            corr = (key[0] == conf.FIRST_SOUND_KEY)
        elif standard_first and (not standard_lauder):
            corr = (key[0] == conf.SECOND_SOUND_KEY)
        elif (not standard_first) and standard_lauder:
            corr = (key[0] == conf.SECOND_SOUND_KEY)
        elif (not standard_first) and (not standard_lauder):
            corr = (key[0] == conf.FIRST_SOUND_KEY)

        if corr:
            feedback_label = corr_feedback_label
        else:
            feedback_label = incorr_feedback_label
    # print("STANDARD FIRST: {} STANDARD LAUDER: {} CORR:{} KEY:{} FIRST VOLUME: {} SECOND VOLUME: {}".format(
    #     standard_first, standard_lauder, corr, key[0], first_volume, second_volume))
    if timeout:  # No reaction
        key = 'noans'
        rt = -1.0
        feedback_label = noans_feedback_label
        corr = -1

    if feedback:
        feedback_label.draw()
        win.flip()
        time.sleep(conf.FEEDB_TIME / 1000.0)

    win.flip()

    return rt, corr, key[0]


def cmp_freq(soa: int, standard: mixer.Sound, ans_lbs: List[visual.TextStim], feedback: bool) -> [float, bool, str]:
    """
    Single trial presented for participant.

    :param soa: Time between first and second sound. Can be interpreted as difficulty level.
    :param ans_lbs: List of labels to display in the time of trial.
    :param feedback: Show feedback or no? (usually True on training)
    :return: [Reaction time, answer correctness, key pressed]
    """
    # == Phase 0: Preparation ==
    key = list()
    t = conf.TIME / 1000.0
    for label in ans_lbs:
        label.draw()

    standard_freq = conf.STANDARD_FREQ
    comparison_freq = standard_freq + random.choice([-soa, soa])  # comparison lower or higher than standard ?
    logging.info('STANDARD FREQ: {} COMPARISON FREQ: {}'.format(conf.STANDARD_FREQ, comparison_freq))

    comparison = get_sine_wave(freq=comparison_freq, sampling_rate=conf.SAMPLING_RATE, wave_length=5 * conf.TIME,
                               wsf=conf.WSF)
    wavfile.write('comparison.wav', conf.SAMPLING_RATE, comparison)
    comparison = mixer.Sound('comparison.wav')

    standard.set_volume(conf.VOLUME)
    comparison.set_volume(conf.VOLUME)
    standard_first = random.choice([True, False])
    standard_freq_higher = standard_freq > comparison_freq
    if standard_first:
        first_sound, second_sound = standard, comparison
    else:
        first_sound, second_sound = comparison, standard
    logging.info('STANDARD VOLUME: {} COMPARISON VOLUME: {}'.format(standard.get_volume(), comparison.get_volume()))
    # == Phase 1: Stimuli presentation
    first_sound.play()
    time.sleep(t)
    first_sound.stop()

    time.sleep(conf.BREAK / 1000.0)

    second_sound.play()
    response_clock.reset()  # for rt measure, reset when second sound starts
    timer.reset(t=t)  # reverse timer from TIME to 0.
    event.clearEvents()
    win.flip()
    while timer.getTime() > 0:  # Handling responses when sounds still playing
        key = event.getKeys(keyList=[conf.FIRST_SOUND_KEY, conf.SECOND_SOUND_KEY])
        if key:
            rt = response_clock.getTime()
            win.flip()
            break

    second_sound.stop()

    # Phase 2: No reaction while stimuli presented
    if not key:  # no reaction when sound was played, wait some more.
        key = event.waitKeys(maxWait=conf.RTIME / 1000.0, keyList=[conf.FIRST_SOUND_KEY, conf.SECOND_SOUND_KEY])
        rt = response_clock.getTime()

    # Phase 3: Timeout handling
    timeout = (len(key) == 0) if key else True  # Still no reaction => Timeout
    win.flip()  # remove labels from screen

    if not timeout:
        if standard_first and standard_freq_higher:
            corr = (key[0] == conf.FIRST_SOUND_KEY)
        elif standard_first and (not standard_freq_higher):
            corr = (key[0] == conf.SECOND_SOUND_KEY)
        elif (not standard_first) and standard_freq_higher:
            corr = (key[0] == conf.SECOND_SOUND_KEY)
        elif (not standard_first) and (not standard_freq_higher):
            corr = (key[0] == conf.FIRST_SOUND_KEY)

        if corr:
            feedback_label = corr_feedback_label
        else:
            feedback_label = incorr_feedback_label
    # print('STANDARD FREQ:{} COMPARISON FREQ: {}'.format(standard_freq, comparison_freq), end=' ')
    # print("STANDARD FIRST: {} STANDARD FREQ HIGHER: {}".format(standard_first, standard_freq_higher), end=' ')
    # print('KEY: {} CORR: {}'.format(key[0], corr))
    if timeout:  # No reaction
        key = ['noans']
        rt = -1.0
        feedback_label = noans_feedback_label
        corr = -1

    if feedback:
        feedback_label.draw()
        win.flip()
        time.sleep(conf.FEEDB_TIME / 1000.0)

    win.flip()

    return rt, corr, key[0]


event.globalKeys.add(key='q', func=safe_quit)  # 'q' terminate procedure in any time
# %% === Dialog popup ===
info = {'PART_ID': '', 'Sex': ["MALE", "FEMALE"], 'AGE': '20'}
dictDlg = gui.DlgFromDict(dictionary=info, title="Psychophysical Force experiment. Sounds version.")
if not dictDlg.OK:
    logging.critical('Dialog popup terminated')
    raise Exception('Dialog popup exception')

# %% == Load config ==
conf = yaml.load(open('config.yaml', 'r'))
conf = Dict2Obj(**conf)

# %% == I18N
try:
    localedir = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'locale')
    lang = gettext.translation(conf['LANG'], localedir, languages=[conf['LANG']])
    _ = lang.gettext  # to suppress No '_' in domain error.
    lang.install()
except OSError:
    msg = "Language {} not supported, add translation or change lang in config.".format(conf['LANG'])
    # logging.critical(msg)
    raise OSError(msg)

# %% == Config validation ==
trial = {'Volume': cmp_vol, 'Freq': cmp_freq}[conf.VER]
# %% == Procedure Init ==
PART_ID = info['PART_ID'] + info['Sex'] + info['AGE']
RES_DIR = conf['VER'] + '_results'

response_clock = core.Clock()
timer = core.CountdownTimer()

mixer.pre_init(conf.SAMPLING_RATE, -16, 2, 512)
mixer.init(conf.SAMPLING_RATE, -16, 2, 512)

conf.SCREEN_RES = SCREEN_RES = get_screen_res()
win = visual.Window(list(SCREEN_RES.values()), fullscr=True, monitor='testMonitor', units='pix', color='black')
event.Mouse(visible=False, newPos=None, win=win)  # Make mouse invisible
FRAME_RATE = get_frame_rate(win)
conf.FRAME_RATE = FRAME_RATE
logging.info('FRAME RATE: {}'.format(FRAME_RATE))
logging.info('SCREEN RES: {}'.format(SCREEN_RES.values()))
logging.LogFile(join(RES_DIR, 'log', PART_ID + '.log'), level=logging.INFO)  # errors logging
shutil.copy2('config.yaml', join(RES_DIR, 'conf', PART_ID + '_config.yaml'))
shutil.copy2('main.py', join(RES_DIR, 'source', PART_ID + '_main.py'))

# %% == Sounds preparation
standard = get_sine_wave(freq=conf.STANDARD_FREQ, sampling_rate=conf.SAMPLING_RATE, wave_length=5 * conf.TIME,
                         wsf=conf.WSF)

wavfile.write('standard.wav', conf.SAMPLING_RATE, standard)

standard = mixer.Sound('standard.wav')
mixer.set_num_channels(2)

# %% == Labels preparation ==
answer_label = {'Volume': _('Volume: Answer Label'), 'Freq': _('Freq: Answer Label')}[conf.VER]
answer_label = visual.TextStim(win, pos=(0, -2 * conf.FONT_SIZE), text=answer_label, font='Arial',
                               color=conf.FONT_COLOR, height=conf.FONT_SIZE)
up_arrow = {'Volume': _('Volume: Up arrow'), 'Freq': _("Freq: Up arrow")}[conf.VER]
down_arrow = {'Volume': _('Volume: Down arrow'), 'Freq': _("Freq: Down arrow")}[conf.VER]
answer2_label = down_arrow + ' ' * 2 * conf.FONT_SIZE + up_arrow
answer2_label = visual.TextStim(win, pos=(0, -4 * conf.FONT_SIZE), text=answer2_label, font='Arial', wrapWidth=1000,
                                color=conf.FONT_COLOR, height=conf.FONT_SIZE)
answer_labels = [answer_label, answer2_label]

corr_feedback_label = _('Corr ans')
corr_feedback_label = visual.TextStim(win, text=corr_feedback_label, font='Arial', color=conf.FONT_COLOR,
                                      height=conf.FONT_SIZE)

incorr_feedback_label = _('Incorr ans')
incorr_feedback_label = visual.TextStim(win, text=incorr_feedback_label, font='Arial', color=conf.FONT_COLOR,
                                        height=conf.FONT_SIZE)

noans_feedback_label = _('No ans')
noans_feedback_label = visual.TextStim(win, text=noans_feedback_label, font='Arial', color=conf.FONT_COLOR,
                                       height=conf.FONT_SIZE)

# %% == Learning phase ==
# msg = {'Volume': _('Volume: hello, before learning'),'Freq': _('Freq: hello, before learning')}[conf.VER]
# show_info(win=win, msg=msg)
#
# sounds_presentation = [(_('LOW FREQUENCY'), low_freq)] * conf.LEARNING + [
#     (_('HIGH FREQUENCY'), high_freq)] * conf.LEARNING
# random.shuffle(sounds_presentation)
#
# label = visual.TextStim(win, color=conf.FONT_COLOR, height=conf.FONT_SIZE, wrapWidth=conf.SCREEN_RES['width'])
#
# for sample in sounds_presentation:
#     break
#     present_learning_sample(win, label, sample)

# %% === Training ===
training = list()
for train_desc in conf.TRAINING:  # Training trials preparation
    training.append([train_desc['soa']] * train_desc['reps'])

msg = {'Volume': _('Volume: before training'), 'Freq': _('Freq: before training')}[conf.VER]
show_info(win=win, msg=msg)

for idx, level in enumerate(training, 1):
    for soa in level:
        rt, corr, key = trial(soa, standard, ans_lbs=answer_labels, feedback=True)
        RESULTS.append([PART_ID, idx, conf.VER, 0, key, int(corr), soa, '-', '-', '-', rt])
        core.wait(conf.BREAK / 1000.0)

# %% == Experiment ==
msg = {'Volume': _('Volume: before experiment'), 'Freq': _('Freq: before experiment')}[conf.VER]
show_info(win=win, msg=msg)

experiment = NUpNDown(start_val=conf.START_SOA, max_revs=conf.MAX_REVS, step_up=conf.STEP_UP, step_down=conf.STEP_DOWN)

old_rev_count_val = -1
for idx, soa in enumerate(experiment, idx):
    rt, corr, key = trial(soa, standard, ans_lbs=answer_labels, feedback=False)
    experiment.set_corr(bool(corr))
    level, reversal, revs_count = map(int, experiment.get_jump_status())

    if old_rev_count_val != revs_count:  # Only first occurrence of revs_count should be in conf, otherwise '-'.
        old_rev_count_val = revs_count
        rev_count_val = revs_count
    else:
        rev_count_val = '-'
   
    RESULTS.append([PART_ID, idx, conf.VER, 1, key, int(corr), soa, reversal, level, rev_count_val, rt])
    if idx == conf.MAX_TRIALS:
        break
    core.wait(conf.BREAK / 1000.0)
   

# %% == Clear experiment
msg = {'Volume': _('Volume: end'), 'Freq': _('Freq: end')}[conf.VER]
show_info(win, msg=msg)
