import expyriment

exp = expyriment.design.Experiment(name="First Experiment")
expyriment.control.initialize(exp)
expyriment.control.set_develop_mode(True)
block_one = expyriment.design.Block(name="A name for the first block")

trial_one = expyriment.design.Trial()
stim = expyriment.stimuli.TextLine(text="I am a stimulus in Block 1, Trial 1")
stim.preload()
trial_one.add_stimulus(stim)

trial_two = expyriment.design.Trial()
stim = expyriment.stimuli.TextLine(text="I am a stimulus in Block 1, Trial 2")
stim.preload()
trial_two.add_stimulus(stim)

block_one.add_trial(trial_one)
block_one.add_trial(trial_two)
exp.add_block(block_one)

block_two = expyriment.design.Block(name="A name for the second block")

trial_one = expyriment.design.Trial()
stim = expyriment.stimuli.TextLine(text="I am a stimulus in Block 2, Trial 1")
stim.preload()
trial_one.add_stimulus(stim)

trial_two = expyriment.design.Trial()
stim = expyriment.stimuli.TextLine(text="I am a stimulus in Block 2, Trial 2")
stim.preload()
trial_two.add_stimulus(stim)

block_two.add_trial(trial_one)
block_two.add_trial(trial_two)
exp.add_block(block_two)

expyriment.control.start()
exp.data_variable_names = ["Block", "Trial", "Key", "RT"]

for block in exp.blocks:
    for trial in block.trials:
        trial.stimuli[0].present()
        key, rt = exp.keyboard.wait([expyriment.misc.constants.K_LEFT,
                                     expyriment.misc.constants.K_RIGHT])
        exp.data.add([block.name, trial.id, key, rt])

expyriment.control.end()
