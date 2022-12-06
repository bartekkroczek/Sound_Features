import os
# import parallel
import time
from datetime import datetime
from typing import Dict, List

import numpy as np
from psychopy import event, visual
from pygame import mixer


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class _LoggingLevels(object):
    INFO = 'info'
    WARNING = 'warning'
    CRITICAL = 'critical'


class TriggerHandler(object):
    """
    Class that handles communication with Biosemi tigger interface.
    """

    def __init__(self, trigger_types: List[str], dummy_mode: bool = True, trigger_time: float = 0.04,
                 trigger_params: List[str] = None) -> None:
        """
        Args:
            trigger_types: List of possible trigger types.
            dummy_mode:  Use EEG or just behave alike.
            trigger_time: Time for delay between start and stop of sending a trigger.
            trigger_params: Additional trigger info to record, like correctness ect.
        """
        self._log: List[str] = list()
        self._creation_time = datetime.now()
        self._logger(f"TriggerHandler constructed with params: dummy_mode={dummy_mode},trigger_time={trigger_time}")
        self.trigger_types = trigger_types
        self._logger(f"Possible triggerTypes registered: {self.trigger_types}")
        self.dummy_mode = dummy_mode
        self._logger(f"Dummy mode: {self.dummy_mode}")
        if not dummy_mode:
            self.PORT = parallel.Parallel()
            self._logger("Connected to EEG (in constructor)")
        else:
            self.PORT = None
        self.trigger_time = trigger_time
        self._logger(f"Trigger time: {trigger_time}")
        self.trigger_params = ['trigger_no', 'trigger_type']
        if trigger_params is None:
            msg = 'No trigger info columns set, so only trigger_type will be recorded.'
            self._logger(msg, level=_LoggingLevels.WARNING)
            print(bcolors.WARNING + msg + bcolors.ENDC)
        else:
            self.trigger_params.extend(trigger_params)
        self._logger(f"Params registered: {self.trigger_params}")
        self._triggers = list()
        self._clear_trigger = 0x00
        self._trigger_counter: int = 1
        self._pos_marker: int = -1
        self._trigger_limit: int = 60
        self._logger(f"Trigger limit set to: {self._trigger_limit}")

    def _logger(self, msg: str, level: str = _LoggingLevels.INFO) -> None:
        time = datetime.now() - self._creation_time
        self._log.append(f"# {str(time).ljust(15)} | {level.ljust(8)} | {msg}" + os.linesep)

    def connect_to_eeg(self):
        if self.PORT is None:
            self.dummy_mode = False
            self.PORT = parallel.Parallel()
            self._logger("Connected to EEG (in connect_to_eeg())")
        else:
            self._logger("Connect to EEG already established.", level=_LoggingLevels.WARNING)
            print(bcolors.WARNING + "Already connected to EEG" + bcolors.ENDC)

    def send_trigger(self, trigger_type: str, info: Dict[(str, str)] = None, with_delay: bool = True):
        """
        Record trigger to send, and save info.
        Args:
            with_delay:
            trigger_type: Type of trigger for an allowed list.
            info: Additional info, also from a list of allowed params.

        Returns:

        """
        self._logger(
            f"send_trigger() run with params trigger_type={trigger_type}, info={info}, with_delay={with_delay}")
        if trigger_type not in self.trigger_types:
            self._logger(f"There's no trigger type called: {trigger_type}.", level=_LoggingLevels.CRITICAL)
            raise AttributeError(f"There's no trigger type called: {trigger_type}.")
        if not self.dummy_mode:
            self.PORT.setData(self._trigger_counter)
            self._logger(f"Value: {self._trigger_counter} sent to EEG.")
        if with_delay:
            time.sleep(self.trigger_time)
        if not self.dummy_mode and with_delay:
            self.PORT.setData(self._clear_trigger)
            self._logger('Clear message sent to EEG.')
        curr_trigger = dict(trigger_no=self._trigger_counter, trigger_type=trigger_type)
        if info is not None:
            unregistered_params: List[str] = list(set(info) - set(self.trigger_params))
            if unregistered_params:
                msg = f"Params: {unregistered_params} are unregistered and won't be saved."
                self._logger(msg, level=_LoggingLevels.WARNING)
                print(bcolors.WARNING + msg + bcolors.ENDC)
            curr_trigger = {**curr_trigger, **info}
        self._trigger_counter += 1
        if self._trigger_counter > self._trigger_limit:
            self._trigger_counter = 1
        self._triggers.append(curr_trigger)
        if self._pos_marker >= 0:
            self._pos_marker += 1

    def send_clear(self):
        if not self.dummy_mode:
            self.PORT.setData(self._clear_trigger)
            self._logger('Clear send to EEG (manually by user).')

    def set_curr_trial_start(self):
        self._pos_marker = 0

    def add_info_to_last_trigger(self, info: Dict[(str, str)], how_many: int = 1) -> None:
        """
        Some trigger info can't be added when trigger is sent, that's why it's possible to add info post factum.
        Args:
            info: Info to add to the last trigger, like correctness.
            how_many: How many of last triggers must be populated, if -1, add until last marker.

        Returns:
            Nothing.
        """
        if how_many == -1 and self._pos_marker == -1:
            msg = f"Cannot add info to curr trial cause no trial was started."
            self._logger(msg, level=_LoggingLevels.WARNING)
            raise AttributeError("No marker set.")
        if how_many == -1:
            how_many = self._pos_marker
            self._pos_marker = -1
        if len(self._triggers) < how_many:
            self._logger("There's no prev trigger to add info to.", level=_LoggingLevels.CRITICAL)
            raise AttributeError("There's no prev trigger to add info to.")
        unregistered_params: List[str] = list(set(info) - set(self.trigger_params))
        if unregistered_params:
            msg = f"Params: {unregistered_params} are unregistered so won't be saved."
            self._logger(msg, level=_LoggingLevels.WARNING)
            print(bcolors.WARNING + msg + bcolors.ENDC)
        for x in range(how_many):
            intersecton = {key: info[key] for key in info if key in self._triggers[-1 - x]}
            if intersecton:
                msg = f"{intersecton.keys()} will be overwritten."
                self._logger(msg, level=_LoggingLevels.CRITICAL)
                print(bcolors.FAIL + msg + bcolors.ENDC)
            self._triggers[-1 - x] = {**self._triggers[-1 - x], **info}

    def _prepare_printable_form(self) -> List[str]:
        res = list()
        res.append(f"{','.join(self.trigger_params)}")
        for trig in self._triggers:
            line: str = ''
            for key in self.trigger_params:
                line += f"{trig.get(key, 'UNKNOWN')},"
            if self.trigger_params:  # remove last underscore
                line = line[:-1]
            res.append(line)
        return res

    def print_trigger_list(self) -> None:
        for line in self._prepare_printable_form():
            print(line)

    def save_to_file(self, file_name: str) -> None:
        with open(file_name, 'w') as beh_file:
            beh_file.writelines([x + os.linesep for x in self._prepare_printable_form()])
            beh_file.writelines(self._log)


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


def present_learning_sample(win: visual, label: visual.TextStim, sample: List[mixer.Sound]) -> None:
    """
   Simple func for playing sound with relevant label. Useful for learning.
    Args:
        win: Current experiment window.
        label: Sound description.
        sample: Sound to present.

    Returns:
        Nothing.
    """
    label.setText(sample[0])
    label.draw()
    win.callOnFlip(sample[1].play)
    win.flip()
    core.wait(conf.TRAIN_SOUND_TIME / 1000.0)
    sample[1].stop()
    win.flip()
    core.wait(conf.BREAK / 1000.0)
