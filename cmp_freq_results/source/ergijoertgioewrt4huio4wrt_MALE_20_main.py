#!/usr/bin/env python3

import wx
import atexit
import csv
import gettext
import os
import random
import shutil
import time
from os.path import join
from typing import List, Tuple, Dict

import yaml
from psychopy import visual, event, logging, gui, core
import simpleaudio as sa
import numpy as np


from Adaptives.NUpNDownMinIters import NUpNDownMinIters
from misc.audio import Dict2Obj
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

RESULTS = [['PART_ID', 'Trial', 'Proc_version', 'Exp', 'Key', 'Corr', 'SOA', 'Reversal', 'Level', 'Rev_count', 'Lat',
            'Standard_first', 'Standard_higher']]


def check_exit(key='f7'):
    stop = event.getKeys(keyList=[key])
    if stop:
        abort_with_error(
            'Experiment finished by user! {} pressed.'.format(key))


def abort_with_error(err):
    logging.critical(err)
    safe_quit()
    core.quit()
    quit()
    raise Exception(err)


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
    msg = visual.TextStim(win, font=font_name, color=font_color,
                          text=msg, height=font_size, wrapWidth=font_max_width)
    msg.draw()
    win.flip()
    key = event.waitKeys(keyList=['return', 'space', 'f7'])
    if key[0] == 'f7':
        abort_with_error(
            'Experiment finished by user! {} pressed.'.format(key))
    win.flip()


# decorator, func will ALWAYS be called when experiment will be closed, even with error.
@atexit.register
def safe_quit() -> None:
    """
    Save beh results, logs, safety ends all frameworks.
    Returns:
        Nothing.
    """
    global RES_DIR
    if 'PART_ID' not in globals():  # Nothing initialised yet, so just turn stuff off.
        raise Exception('No PART_ID in  globals(). Nothing to close.')
    fname = PART_ID + "_" + \
        time.strftime("%Y-%m-%d_%H_%M_%S", time.gmtime()) + '_beh.csv'
    tname = PART_ID + "_" + \
        time.strftime("%Y-%m-%d_%H_%M_%S", time.gmtime()) + '_triggermap.csv'
    with open(join(RES_DIR, 'beh', fname), 'w') as beh_file:
        beh_writer = csv.writer(beh_file)
        beh_writer.writerows(RESULTS)
    TRIGGERS.save_to_file(join(RES_DIR, 'triggermaps', tname))
    logging.flush()
    core.quit()
    quit()


class TrialType(object):
    CMP_DUR = 'cmp_dur'
    CMP_FREQ = 'cmp_freq'
    CMP_VOL = 'cmp_vol'


def prepare_sound(freq, sound_time, sample_rate=44100, transition_time=0.05):
    sample_rate = 44100
    t = np.linspace(0, sound_time, int(sound_time * sample_rate), False)

    # generate sine wave note
    note = np.sin(freq * t * 2 * np.pi)

    # add rise_up and fall_down to sound to avoid noises
    fall_down = np.linspace(1, 0, int(transition_time * sample_rate))
    rise_up = np.linspace(0, 1, int(transition_time * sample_rate))
    transition = np.hstack(
        (rise_up, ([1] * (len(note) - 2 * len(fall_down))), fall_down))
    audio = note * transition

    # normalize to 16-bit range
    audio *= 32767 / np.max(np.abs(audio))
    # convert to 16-bit data
    return audio.astype(np.int16)


def play_sound(audio, sample_rate=44100) -> None:
    # start playback
    play_obj = sa.play_buffer(audio, 1, 2, sample_rate)
    # wait for playback to finish before exiting
    play_obj.wait_done()


def present_learning_sample(win: visual, idx: int, soa: int, standard_freq: float, audio_separator,
                            conf: Dict2Obj) -> None:
    """
   Simple func for playing sound with relevant label. Useful for learning.
    Args:
        audio_separator: Sound to separate relevant tones, white noise preferably.
        idx: No of a curr trial.
        conf:
        standard_freq: Frequency of one of a sounds
        soa: Difference between sounds.
        win: Current experiment window.

    Returns:
        Nothing.
    """

    if soa < 0:
        raise ValueError('Learning phase soa must be positive.')
    label = visual.TextStim(win, color=conf.FONT_COLOR,
                            height=conf.FONT_SIZE, wrapWidth=conf.SCREEN_RES['width'])
    soa = random.choice([-soa, soa])
    freqs = [standard_freq, standard_freq + soa]
    random.shuffle(freqs)
    first_sound_freq, sec_sound_freq = freqs
    msg = _("First tone higher") if first_sound_freq > sec_sound_freq else _("First tone lower")
    sound_time = conf.TRAIN_SOUND_TIME / 1000.
    first_sound = prepare_sound(freq=first_sound_freq, sound_time=sound_time)
    sec_sound = prepare_sound(freq=sec_sound_freq, sound_time=sound_time)
    
    # === Play separator ===
    check_exit()
    play_obj = audio_separator.play()
    play_obj.wait_done()
    core.wait(2 * sound_time)
    check_exit()
    # === First Sound ===
    play_sound(audio=first_sound)
    core.wait(sound_time)
    check_exit()
    # === Secound Sound ===
    play_sound(audio=sec_sound)
    core.wait(sound_time)
    check_exit()
    # === Labels ===
    check_exit()
    core.wait(sound_time / 2)
    check_exit()
    label.setText(msg)
    label.draw()
    win.flip()
    core.wait(3 * sound_time)
    check_exit()
    win.flip()
    core.wait(sound_time)
    msg = _("Learning: Next")
    label.setText(msg)
    label.draw()
    win.flip()
    event.waitKeys(keyList=['space'])
    core.wait(sound_time//2)
    win.flip()


def main():
    global RES_DIR, PART_ID
    # %% === Dialog popup ===
    info = {'PART_ID': '', 'Sex': ["MALE", "FEMALE"],
            'AGE': '20', 'VERSION': ['cmp_dur', 'cmp_freq']}
    dictDlg = gui.DlgFromDict(
        dictionary=info, title="Study Y. Sound Procedures.")
    if not dictDlg.OK:
        raise Exception('Dialog popup exception')
    ver = info['VERSION']
    RES_DIR = ver + '_results'
    PART_ID = f"{info['PART_ID']}_{info['Sex']}_{info['AGE']}"
    fname = PART_ID + "_" + \
        time.strftime("%Y-%m-%d_%H_%M_%S", time.gmtime()) + '.log'
    logging.LogFile(join(RES_DIR, 'log', fname),
                    level=logging.INFO)  # errors logging
    underscore_in_partid = "_" in info['PART_ID']
    if underscore_in_partid:
        msg = 'Underscore "_" is illegal as a participant name.'
        logging.critical(msg)
        app = wx.App()
        wx.MessageBox(msg, 'Error',  wx.OK | wx.ICON_ERROR)
        raise AttributeError('Participant name cannot have underscore in it.')
    curr_id_already_used = info['PART_ID'] in [
        f.split('_')[0] for f in os.listdir(join(f'{ver}_results', 'beh'))]
    if curr_id_already_used:
        msg = f"Current id:{info['PART_ID']} already used, check if you choose right proc ver({ver})."
        logging.critical(msg)
        app = wx.App()
        wx.MessageBox(msg, 'Error',  wx.OK | wx.ICON_ERROR)
        raise AttributeError('Current id already used.')

    # %% == Load config ==
    conf = yaml.load(open(f'{ver}_config.yaml', 'r'), Loader=yaml.SafeLoader)
    conf = Dict2Obj(**conf)
    if conf.USE_EEG:
        TRIGGERS.connect_to_eeg()
    else:
        msg = "EEG DUMMY MODE! No triggers sent to EEG!"
        logging.info(msg)
        app = wx.App()
        wx.MessageBox(msg, 'Error',  wx.OK | wx.ICON_ERROR)
    # %% == I18N
    try:
        localedir = os.path.join(os.path.abspath(
            os.path.dirname(__file__)), 'locale')
        lang = gettext.translation(
            conf['LANG'], localedir, languages=[conf['LANG']])
        _ = lang.gettext  # to suppress No '_' in domain error.
        lang.install()
    except OSError:
        msg = "Language {} not supported, add translation or change lang in config.".format(
            conf['LANG'])
        logging.critical(msg)
        raise OSError(msg)
    # %% == Procedure Init ==
    conf.SCREEN_RES = SCREEN_RES = get_screen_res()
    win = visual.Window(list(SCREEN_RES.values()), fullscr=True,
                        monitor='testMonitor', units='pix', color='black')
    event.Mouse(visible=False, newPos=None, win=win)  # Make mouse invisible
    FRAME_RATE = get_frame_rate(win)
    conf.FRAME_RATE = FRAME_RATE
    logging.info('FRAME RATE: {}'.format(FRAME_RATE))
    logging.info('SCREEN RES: {}'.format(SCREEN_RES.values()))
    shutil.copy2(f'{ver}_config.yaml', join(
        RES_DIR, 'conf', f'{PART_ID}_{ver}_config.yaml'))
    shutil.copy2('main.py', join(RES_DIR, 'source', PART_ID + '_main.py'))

    # %% == Sounds preparation
    white_noise = sa.WaveObject.from_wave_file('white_noise.wav')
    # %% == Labels preparation ==
    answer_label = {'cmp_vol': _('Volume: Answer Label'), 'cmp_freq': _('Freq: Answer Label'),
                    'cmp_dur': _('Dur: Answer Label')}[ver]
    answer_label = visual.TextStim(win, pos=(0, -2 * conf.FONT_SIZE), text=answer_label, font='Arial',
                                   color=conf.FONT_COLOR, height=conf.FONT_SIZE)
    up_arrow = {'cmp_vol': _('Volume: Up arrow'), 'cmp_freq': _("Freq: Up arrow"),
                'cmp_dur': _("Dur: Up arrow")}[ver]
    down_arrow = {'cmp_vol': _('Volume: Down arrow'), 'cmp_freq': _("Freq: Down arrow"),
                  'cmp_dur': _("Dur: Down arrow")}[ver]
    answer2_label = down_arrow + ' ' * 2 * conf.FONT_SIZE + up_arrow
    answer2_label = visual.TextStim(win, pos=(0, -4 * conf.FONT_SIZE), text=answer2_label, font='Arial', wrapWidth=1000,
                                    color=conf.FONT_COLOR, height=conf.FONT_SIZE)
    answer_labels = [answer_label, answer2_label]
    fix_cross = visual.TextStim(win, text='+', color='red', pos=(0, 15))
    fix_cross.setAutoDraw(True)
    # %% == Learning phase ==
    if ver == TrialType.CMP_FREQ:
        show_info(win=win, msg=_('Freq: hello, before learning'))
        core.wait(conf.TRAIN_SOUND_TIME / 1000.0)
        for idx, soa in enumerate(conf.LEARNING_SOAS, start=1):
            present_learning_sample(
                win, idx, soa, conf.STANDARD_FREQ, white_noise, conf=conf)
            check_exit()
        show_info(win=win, msg=_('Freq: hello, after learning'))

    # %% === Training ===
    training = list()
    for train_desc in conf.TRAINING:  # Training trials preparation
        training.append([train_desc['soa']] * train_desc['reps'])
    msg = {'cmp_vol': _('Volume: before training'), 'cmp_freq': _('Freq: before training'),
           'cmp_dur': _("Dur: before training")}[ver]
    show_info(win=win, msg=msg)
    for lab in answer_labels:
        lab.setAutoDraw(True)
    win.flip()
    for idx, level in enumerate(training, 1):
        for soa in level:
            rt, corr, key, sf, sh = run_trial(
                win, ver, soa, conf, white_noise, answer_labels, feedback=True)
            RESULTS.append([PART_ID, idx, ver, 'train', key,
                           int(corr), soa, '-', '-', '-', rt, sf, sh])
            core.wait(conf.BREAK / 1000.0)
            core.wait(random.choice(
                range(*conf.JITTER_RANGE)) / 1000.0)  # jitter
    for lab in answer_labels:
        lab.setAutoDraw(False)
    win.flip()
    # %% == Experiment ==
    msg = {'cmp_vol': _('Volume: before experiment'), 'cmp_freq': _('Freq: before experiment'),
           'cmp_dur': _('Dur: before experiment')}[ver]
    show_info(win=win, msg=msg)
    experiment = NUpNDownMinIters(n_up=conf.N_UP, n_down=conf.N_DOWN, start_val=conf.START_SOA, max_revs=conf.MAX_REVS,
                                  step_up=conf.STEP_UP, step_down=conf.STEP_DOWN, min_iters=conf.MIN_TRIALS)
    old_rev_count_val = -1
    for lab in answer_labels:
        lab.setAutoDraw(True)
    win.flip()
    for idx, soa in enumerate(experiment, idx):
        rt, corr, key, sf, sh = run_trial(
            win, ver, soa, conf, white_noise, answer_labels, feedback=False)
        experiment.set_corr(bool(corr))
        level, reversal, revs_count = map(int, experiment.get_jump_status())

        # Only first occurrence of revs_count should be in conf, otherwise '-'.
        if old_rev_count_val != revs_count:
            old_rev_count_val = revs_count
            rev_count_val = revs_count
        else:
            rev_count_val = '-'

        RESULTS.append([PART_ID, idx, ver, 'exp', key, int(
            corr), soa, reversal, level, rev_count_val, rt, sf, sh])
        if idx == conf.MAX_TRIALS:
            break
        core.wait(conf.BREAK / 1000.0)
        core.wait(random.choice(range(*conf.JITTER_RANGE)) / 1000.0)  # jitter
    # %% == Clear experiment
    msg = {'cmp_vol': _('Volume: end'), 'cmp_freq': _(
        'Freq: end'), 'cmp_dur': _('Dur: end')}[ver]
    for lab in answer_labels:
        lab.setAutoDraw(False)
    win.flip()
    show_info(win, msg=msg)
    win.close()
    core.quit()
    quit()


def run_trial(win: visual.Window, trial_type: TrialType, soa: int, conf: Dict2Obj, fix_sound,
              ans_lbs: List[visual.TextStim], feedback: bool) -> Tuple[float, any, str]:
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
    fadeout_time: int = conf.FADEOUT_TIME
    tw: float = (300 - fadeout_time) / 1000.0  # white noise playing time
    t1: float = (conf.TIME - fadeout_time) / 1000.0  # first sound playing time
    t2: float = (conf.TIME - fadeout_time) / 1000.0  # sec sound playing time
    soa: float = random.choice([-soa, soa])
    timeout: bool = True
    corr: bool = False
    timer: core.CountdownTimer = core.CountdownTimer()
    response_clock: core.Clock = core.Clock()
    first_sound: mixer.Sound = mixer.Sound(
        join("audio_stims", f"{conf.STANDARD_FREQ}.wav"))
    second_sound: mixer.Sound = mixer.Sound(
        join("audio_stims", f"{conf.STANDARD_FREQ}.wav"))
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
    standard_higher = soa < 0  # in freq/loudness/duration
    if trial_type == TrialType.CMP_VOL:
        if standard_first:
            first_volume, second_volume = conf.VOLUME, conf.VOLUME + soa
        else:
            first_volume, second_volume = conf.VOLUME + soa, conf.VOLUME
        msg = f"first vol: {first_volume}, sec vol: {second_volume}"
        first_volume, second_volume = first_volume / 100.0, second_volume / 100.0
        logging.info(msg)
        print(msg, end=' =>')
        first_sound.set_volume(first_volume)
        second_sound.set_volume(second_volume)
    elif trial_type == TrialType.CMP_FREQ:
        standard_freq = conf.STANDARD_FREQ
        comparison_freq = standard_freq + soa
        msg = f'Stadard freq: {standard_freq}, Comparsion_freq: {comparison_freq}'
        logging.info(msg)
        print(msg, end='=>')
        standard = mixer.Sound(join("audio_stims", f'{standard_freq}.wav'))
        comparison = mixer.Sound(join("audio_stims", f'{comparison_freq}.wav'))
        standard.set_volume(conf.VOLUME)
        comparison.set_volume(conf.VOLUME)
        if standard_first:
            first_sound, second_sound = standard, comparison
        else:
            first_sound, second_sound = comparison, standard
    elif trial_type == TrialType.CMP_DUR:
        standard_first = True  # first sound is always this same
        first_sound = mixer.Sound(
            join("audio_stims", f'{conf.STANDARD_FREQ}.wav'))
        second_sound = mixer.Sound(
            join("audio_stims", f'{conf.STANDARD_FREQ}.wav'))
        t1 = (conf.TIME - fadeout_time) / 1000.0
        t2 = (conf.TIME + soa - fadeout_time) / 1000.0
        msg = f"Time1: {t1}, Time2:{t2}. Fadeout: {fadeout_time}"
        logging.info(msg)
        print(msg, end='=>')
    else:
        msg = f'Procedure works only with Volume, duration or frequency. Not with {trial_type}'
        logging.critical(msg)
        raise NotImplementedError(msg)
    logging.info(f'TrialType: {trial_type}')
    msg = f"Standard is f{'first' if standard_first else 'second'} and {'higher' if standard_higher else 'lower'}"
    logging.info(msg)
    # == Phase 1: White noise
    fix_sound.set_volume(conf.VOLUME)  # set to default vol for exp
    fix_sound.play()
    print(tw)
    core.wait(tw)
    fix_sound.fadeout(fadeout_time)
    core.wait(fadeout_time / 1000.)
    core.wait(2 * conf.BREAK / 1000.0)

    # == Phase 2: Stimuli presentation
    first_sound.play()  # start sound
    TRIGGERS.send_trigger(TriggerTypes.STIM_1_START)
    # TODO: Check if fadeout stopped execution and equals time properly (probably not)
    # there's a delay during send_trig function, so must be subtracted here
    time.sleep(t1 - TRIGGERS.trigger_time)
    first_sound.fadeout(fadeout_time)  # stop sound
    core.wait(fadeout_time / 1000.)
    TRIGGERS.send_trigger(TriggerTypes.STIM_1_END)
    time.sleep(conf.BREAK / 1000.0)
    event.clearEvents()

    # make trigger, start of a sound and response timer in sync through win.flip()
    win.callOnFlip(second_sound.play)
    win.callOnFlip(response_clock.reset)
    win.callOnFlip(TRIGGERS.send_trigger, TriggerTypes.STIM_2_START)
    timer.reset(t=t2)  # reverse timer from TIME to 0.
    win.flip()  # sound played, clock reset, trig sent
    check_exit()
    while timer.getTime() > 0:  # Handling responses when sounds still playing
        key = event.getKeys(
            keyList=[conf.FIRST_SOUND_KEY, conf.SECOND_SOUND_KEY])
        if key:
            rt = response_clock.getTime()
            TRIGGERS.send_trigger(TriggerTypes.ANSWERED)
            timeout = False
            win.flip()
            break
    second_sound.fadeout(fadeout_time)
    core.wait(fadeout_time / 1000.)
    TRIGGERS.send_trigger(TriggerTypes.STIM_2_END)

    # Phase 3: No reaction while stimuli presented
    if not key:  # no reaction when sound was played, wait some more.
        key = event.waitKeys(maxWait=conf.RTIME / 1000.0,
                             keyList=[conf.FIRST_SOUND_KEY, conf.SECOND_SOUND_KEY])
        if key:  # check if any reaction, if no - timeout
            rt = response_clock.getTime()
            timeout = False
            TRIGGERS.send_trigger(TriggerTypes.ANSWERED)

    # Phase 4: Timeout handling

    if not timeout:
        if standard_first and standard_higher:
            corr = (key[0] == conf.FIRST_SOUND_KEY)
        elif standard_first and (not standard_higher):
            corr = (key[0] == conf.SECOND_SOUND_KEY)
        elif (not standard_first) and standard_higher:
            corr = (key[0] == conf.SECOND_SOUND_KEY)
        elif (not standard_first) and (not standard_higher):
            corr = (key[0] == conf.FIRST_SOUND_KEY)
        print(f" {corr} {key[0]}")
        if corr:
            feedback_label = corr_feedback_label
        else:
            feedback_label = incorr_feedback_label
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
    return rt, corr, key[0], standard_first, standard_higher


if __name__ == '__main__':
    PART_ID = ''
    main()
