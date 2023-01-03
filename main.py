#!/usr/bin/env python3
from __future__ import annotations

import atexit
import csv
import gettext
import os
import random
import shutil
import time
from os.path import join
from typing import List, Tuple

import yaml
from psychopy import visual, event, logging, gui, core
from pygame import mixer, quit
from scipy.io import wavfile

from Adaptives.NUpNDown import NUpNDown
from misc.audio import Dict2Obj, show_info, get_sine_wave, get_white_noise
from procedures_misc.screen_misc import get_frame_rate, get_screen_res
from procedures_misc.triggers import TriggerHandler

global PART_ID, RES_DIR  # Used in case of error on @atexit, that's why it must be global


class TriggerTypes(object):
    STIM_1_START = 'stim_1_start'
    STIM_1_END = 'stim_1_end'
    STIM_2_START = "stim_2_start"
    STIM_2_END = 'stim_2_end'
    ANSWERED = 'answered'

    @classmethod
    def vals(cls):
        return [value for name, value in vars(cls).items() if name.isupper()]


TRIGGERS = TriggerHandler(TriggerTypes.vals(), trigger_params=['corr', 'key'])

RESULTS = [['PART_ID', 'Trial', 'Proc_version', 'Exp', 'Key', 'Corr', 'SOA', 'Reversal', 'Level', 'Rev_count', 'Lat']]


def check_exit(key='f7'):
    stop = event.getKeys(keyList=[key])
    if stop:
        abort_with_error('Experiment finished by user! {} pressed.'.format(key))


def abort_with_error(err):
    logging.critical(err)
    safe_quit()
    core.quit()
    quit()
    raise Exception(err)


@atexit.register  # decorator, func will ALWAYS be called when experiment will be closed, even with error.
def safe_quit() -> None:
    """
    Save beh results, logs, safety ends all frameworks.
    Returns:
        Nothing.
    """
    global RES_DIR
    if 'PART_ID' not in globals():  # Nothing initialised yet, so just turn stuff off.
        raise Exception('No PART_ID in  globals(). Nothing to close.')
    fname = PART_ID + "_" + time.strftime("%Y-%m-%d_%H_%M_%S", time.gmtime()) + '_beh.csv'
    tname = PART_ID + "_" + time.strftime("%Y-%m-%d_%H_%M_%S", time.gmtime()) + '_triggermap.csv'
    with open(join(RES_DIR, 'beh', fname), 'w') as beh_file:
        beh_writer = csv.writer(beh_file)
        beh_writer.writerows(RESULTS)
    TRIGGERS.save_to_file(join(RES_DIR, 'triggermaps', tname))
    logging.flush()
    core.quit()
    quit()


class TrialType(object):
    CMP_FREQ = 'cmp_freq'
    CMP_VOL = 'cmp_vol'


def present_learning_sample(win: visual, idx: int, soa: int, standard_freq: float, audio_separator: mixer.Sound,
                            conf: Dict2Obj) -> None:
    """
   Simple func for playing sound with relevant label. Useful for learning.
    Args:
        audio_separator:
        idx:
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
    msg = f"PARA NR {idx}."
    label.setText(msg)
    label.draw()
    win.flip()

    soa = random.choice([-soa, soa])
    freqs = [standard_freq, standard_freq + soa]
    random.shuffle(freqs)
    first_sound_freq, sec_sound_freq = freqs
    msg = "Pierwszy dzwi\u0119k był wy\u017Cszy." if first_sound_freq > sec_sound_freq else "Pierwszy dzwi\u0119k był ni\u017Cszy."

    first_sound = get_sine_wave(freq=first_sound_freq, sampling_rate=conf.SAMPLING_RATE, wave_length=5 * conf.TIME,
                                wsf=conf.WSF)
    wavfile.write('learning_first_sound.wav', conf.SAMPLING_RATE, first_sound)
    first_sound = mixer.Sound('learning_first_sound.wav')
    sec_sound = get_sine_wave(freq=sec_sound_freq, sampling_rate=conf.SAMPLING_RATE, wave_length=5 * conf.TIME,
                              wsf=conf.WSF)
    wavfile.write('learning_sec_sound.wav', conf.SAMPLING_RATE, sec_sound)
    sec_sound = mixer.Sound('learning_sec_sound.wav')

    core.wait(conf.TRAIN_SOUND_TIME / 1000.0)
    audio_separator.play()
    core.wait(conf.TRAIN_SOUND_TIME / 1000.0)
    audio_separator.stop()
    core.wait(conf.TRAIN_SOUND_TIME / 1000.0)
    first_sound.play()
    core.wait(conf.TRAIN_SOUND_TIME / 1000.0)
    first_sound.stop()
    core.wait(2 * conf.TRAIN_SOUND_TIME / 1000.0)
    sec_sound.play()
    core.wait(conf.TRAIN_SOUND_TIME / 1000.0)
    sec_sound.stop()
    label.setText(msg)
    label.draw()
    win.flip()
    core.wait(2)


def main():
    global RES_DIR, PART_ID
    # %% === Dialog popup ===
    info = {'PART_ID': '', 'Sex': ["MALE", "FEMALE"], 'AGE': '20'}
    dictDlg = gui.DlgFromDict(dictionary=info, title="Psychophysical Force experiment. Sounds version.")
    if not dictDlg.OK:
        logging.critical('Dialog popup terminated')
        raise Exception('Dialog popup exception')
    # %% == Load config ==
    conf = yaml.load(open('config.yaml', 'r'), Loader=yaml.SafeLoader)
    conf = Dict2Obj(**conf)
    if conf.USE_EEG:
        TRIGGERS.connect_to_eeg()
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
    # %% == Procedure Init ==
    PART_ID = info['PART_ID'] + info['Sex'] + info['AGE']
    RES_DIR = conf['VER'] + '_results'
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
    white_noise = get_white_noise(conf.WHITE_NOISE_LOUDNESS, conf.SAMPLING_RATE, wave_length=5 * conf.TIME,
                                  wsf=conf.WSF)
    wavfile.write('white_noise.wav', conf.SAMPLING_RATE, white_noise)
    white_noise = mixer.Sound('white_noise.wav')
    mixer.set_num_channels(2)
    # %% == Labels preparation ==
    answer_label = {'cmp_vol': _('Volume: Answer Label'), 'cmp_freq': _('Freq: Answer Label')}[conf.VER]
    answer_label = visual.TextStim(win, pos=(0, -2 * conf.FONT_SIZE), text=answer_label, font='Arial',
                                   color=conf.FONT_COLOR, height=conf.FONT_SIZE)
    up_arrow = {'cmp_vol': _('Volume: Up arrow'), 'cmp_freq': _("Freq: Up arrow")}[conf.VER]
    down_arrow = {'cmp_vol': _('Volume: Down arrow'), 'cmp_freq': _("Freq: Down arrow")}[conf.VER]
    answer2_label = down_arrow + ' ' * 2 * conf.FONT_SIZE + up_arrow
    answer2_label = visual.TextStim(win, pos=(0, -4 * conf.FONT_SIZE), text=answer2_label, font='Arial', wrapWidth=1000,
                                    color=conf.FONT_COLOR, height=conf.FONT_SIZE)
    answer_labels = [answer_label, answer2_label]
    fix_cross = visual.TextStim(win, text='+', color='red', pos=(0, 15))
    fix_cross.setAutoDraw(True)
    # %% == Learning phase ==
    if conf.VER == 'cmp_freq':
        msg = {'cmp_vol': _('Volume: hello, before learning'), 'cmp_freq': _('Freq: hello, before learning')}[conf.VER]
        show_info(win=win, msg=msg)

        for idx, soa in enumerate(conf.LEARNING_SOAS, start=1):
            present_learning_sample(win, idx, soa, conf.STANDARD_FREQ, white_noise, conf=conf)
            check_exit()

    # %% === Training ===
    training = list()
    for train_desc in conf.TRAINING:  # Training trials preparation
        training.append([train_desc['soa']] * train_desc['reps'])
    msg = {'cmp_vol': _('Volume: before training'), 'cmp_freq': _('Freq: before training')}[conf.VER]
    show_info(win=win, msg=msg)
    for idx, level in enumerate(training, 1):
        for soa in level:
            rt, corr, key = run_trial(win, conf.VER, soa, conf, white_noise, answer_labels, feedback=True)
            RESULTS.append([PART_ID, idx, conf.VER, 'train', key, int(corr), soa, '-', '-', '-', rt])
            core.wait(conf.BREAK / 1000.0)
    # %% == Experiment ==
    msg = {'cmp_vol': _('Volume: before experiment'), 'cmp_freq': _('Freq: before experiment')}[conf.VER]
    show_info(win=win, msg=msg)
    experiment = NUpNDown(start_val=conf.START_SOA, max_revs=conf.MAX_REVS, step_up=conf.STEP_UP,
                          step_down=conf.STEP_DOWN)
    old_rev_count_val = -1
    for idx, soa in enumerate(experiment, idx):
        rt, corr, key = run_trial(win, conf.VER, soa, conf, white_noise, answer_labels, feedback=False)
        experiment.set_corr(bool(corr))
        level, reversal, revs_count = map(int, experiment.get_jump_status())

        if old_rev_count_val != revs_count:  # Only first occurrence of revs_count should be in conf, otherwise '-'.
            old_rev_count_val = revs_count
            rev_count_val = revs_count
        else:
            rev_count_val = '-'

        RESULTS.append([PART_ID, idx, conf.VER, 'exp', key, int(corr), soa, reversal, level, rev_count_val, rt])
        if idx == conf.MAX_TRIALS:
            break
        core.wait(conf.BREAK / 1000.0)
    # %% == Clear experiment
    msg = {'cmp_vol': _('Volume: end'), 'cmp_freq': _('Freq: end')}[conf.VER]
    show_info(win, msg=msg)
    win.close()
    core.quit()
    quit()


def run_trial(win: visual.Window, trial_type: TrialType, soa: int, conf: Dict2Obj, fix_sound: mixer.Sound,
              ans_lbs: List[visual.TextStim], feedback: bool) -> Tuple[float, bool | int, str]:
    """
        Single trial presented for participant.
    Args:
        win: Main procedure window.
        trial_type: Sound will differ in loudness or in frequency.
        soa: difference between stimuli.
        conf: Dict with global params defined by user.
        fix_sound: sound at the beginning of a trial, white noise usually.
        ans_lbs: labels for key mapping.
        feedback: show info about correctness or not.
    Returns:
        List containing [Reaction time, answer correctness, key pressed]
    """
    # == Phase 0: Preparation ==
    global _
    key: list = list()
    t: float = conf.TIME / 1000.0
    soa: float = random.choice([-soa, soa])
    trig_time: float = TRIGGERS.get_trigger_time()
    timeout: bool = True
    corr: bool = False
    timer: core.CountdownTimer = core.CountdownTimer()
    response_clock: core.Clock = core.Clock()
    first_sound: mixer.Sound = mixer.Sound("standard.wav")
    second_sound: mixer.Sound = mixer.Sound("standard.wav")
    TRIGGERS.set_curr_trial_start()
    corr_feedback_label = _('Corr ans')
    corr_feedback_label = visual.TextStim(win, text=corr_feedback_label, font='Arial', color=conf.FONT_COLOR,
                                          height=conf.FONT_SIZE)
    incorr_feedback_label = _('Incorr ans')
    incorr_feedback_label = visual.TextStim(win, text=incorr_feedback_label, font='Arial', color=conf.FONT_COLOR,
                                            height=conf.FONT_SIZE)
    noans_feedback_label = _('No ans')
    noans_feedback_label = visual.TextStim(win, text=noans_feedback_label, font='Arial', color=conf.FONT_COLOR,
                                           height=conf.FONT_SIZE)
    standard_first = random.choice([True, False])
    standard_higher = soa < 0  # in freq or in loudness
    if trial_type == TrialType.CMP_VOL:
        if standard_first:
            first_volume, second_volume = conf.VOLUME, conf.VOLUME + soa
        else:
            first_volume, second_volume = conf.VOLUME + soa, conf.VOLUME
        first_sound.set_volume(first_volume)
        second_sound.set_volume(second_volume)
    elif trial_type == TrialType.CMP_FREQ:
        standard_freq = conf.STANDARD_FREQ
        comparison_freq = standard_freq + soa
        print(f'Stadard freq: {standard_freq}, Comparsion_freq: {comparison_freq}')
        comparison = get_sine_wave(freq=comparison_freq, sampling_rate=conf.SAMPLING_RATE, wave_length=5 * conf.TIME,
                                   wsf=conf.WSF)
        wavfile.write('comparison.wav', conf.SAMPLING_RATE, comparison)
        standard = mixer.Sound('standard.wav')
        comparison = mixer.Sound('comparison.wav')
        standard.set_volume(conf.VOLUME)
        comparison.set_volume(conf.VOLUME)
        if standard_first:
            first_sound, second_sound = standard, comparison
        else:
            first_sound, second_sound = comparison, standard
    else:
        raise NotImplementedError('Procedure works only with cmp_vol and cmp_freq.')
    logging.info(f'TrialType: {trial_type}')
    logging.info(f'Standard stimuli is f{"first" if standard_first else "second"} and '
                 f'{"higher" if standard_higher else "lower"} ')
    # print(f"FIRST VOL: {first_volume}, SEC VOL: {second_volume}")
    # print(f"conf vol: {conf.VOLUME}, soa: {soa}")
    # print(f"FIRST VOL: {first_sound.get_volume()} SEC VOL: {second_sound.get_volume()}")
    for label in ans_lbs:
        label.draw()
    # == Phase 1: White noise
    fix_sound.set_volume(conf.VOLUME)  # set to default vol for exp
    fix_sound.play()
    time.sleep(t)
    fix_sound.stop()
    time.sleep(conf.BREAK / 1000.0)

    # == Phase 2: Stimuli presentation
    first_sound.play()  # start sound
    TRIGGERS.send_trigger(TriggerTypes.STIM_1_START)
    time.sleep(t - TRIGGERS.trigger_time)  # there's a delay during send_trig function, so must be subtracted here
    first_sound.stop()  # stop sound
    TRIGGERS.send_trigger(TriggerTypes.STIM_1_END)
    time.sleep(conf.BREAK / 1000.0)
    event.clearEvents()

    # make trigger, start of a sound and response timer in sync through win.flip()
    win.callOnFlip(second_sound.play)
    win.callOnFlip(response_clock.reset)
    win.callOnFlip(TRIGGERS.send_trigger, TriggerTypes.STIM_2_START, with_delay=False)
    timer.reset(t=t)  # reverse timer from TIME to 0.
    win.flip()  # sound played, clock reset, trig sent
    time.sleep(trig_time)  # nobody will react as fast, so procedure can be frozen for a while
    TRIGGERS.send_clear()
    while timer.getTime() > 0:  # Handling responses when sounds still playing
        key = event.getKeys(keyList=[conf.FIRST_SOUND_KEY, conf.SECOND_SOUND_KEY])
        if key:
            rt = response_clock.getTime()
            TRIGGERS.send_trigger(TriggerTypes.ANSWERED)
            timeout = False
            win.flip()
            break
    second_sound.stop()
    TRIGGERS.send_trigger(TriggerTypes.STIM_2_END)

    # Phase 3: No reaction while stimuli presented

    if not key:  # no reaction when sound was played, wait some more.
        key = event.waitKeys(maxWait=conf.RTIME / 1000.0, keyList=[conf.FIRST_SOUND_KEY, conf.SECOND_SOUND_KEY])
        if key:  # check if any reaction, if no - timeout
            rt = response_clock.getTime()
            timeout = False
            TRIGGERS.send_trigger(TriggerTypes.ANSWERED)

    # Phase 4: Timeout handling
    win.flip()  # remove labels from screen

    if not timeout:
        if standard_first and standard_higher:
            corr = (key[0] == conf.FIRST_SOUND_KEY)
        elif standard_first and (not standard_higher):
            corr = (key[0] == conf.SECOND_SOUND_KEY)
        elif (not standard_first) and standard_higher:
            corr = (key[0] == conf.SECOND_SOUND_KEY)
        elif (not standard_first) and (not standard_higher):
            corr = (key[0] == conf.FIRST_SOUND_KEY)

        if corr:
            feedback_label = corr_feedback_label
        else:
            feedback_label = incorr_feedback_label
    # print("STANDARD FIRST: {} STANDARD LAUDER: {} CORR:{} KEY:{} FIRST VOLUME: {} SECOND VOLUME: {}".format(
    #     standard_first, standard_lauder, corr, key[0], first_volume, second_volume))
    else:  # No reaction
        key = ['noans']
        rt = -1.0
        feedback_label = noans_feedback_label
        corr = False
    TRIGGERS.add_info_to_last_trigger(dict(corr=corr, key=key[0]), how_many=-1)

    if feedback:
        feedback_label.draw()
        win.flip()
        time.sleep(conf.FEEDB_TIME / 1000.0)

    win.flip()
    check_exit()
    return rt, corr, key[0]


if __name__ == '__main__':
    PART_ID = ''
    event.globalKeys.clear()
    event.globalKeys.add(key='q', func=safe_quit)  # 'q' terminate procedure in any time
    SCREEN_RES = get_screen_res()
    main()
