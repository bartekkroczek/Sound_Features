# %%
import random

import pandas as pd

from Adaptives.NUpNDown import NUpNDown

# %%
exp = NUpNDown(step_up=1, step_down=1, max_revs=3)
labels = ['Ans', 'SOA', 'PRE:LastJumpDir', 'PRE:SwitchInLast', 'PRE:Rev', 'POST:LastJumpDir2', 'POST:SwitchInLast2',
          'POST:Rev2', 'DIFF:LJD', 'DIFF:Switch', 'Diff:REV']
table = list()
for i in exp:
    c = random.choice([True, False])
    j1, j2, j3 = exp.get_jump_status()
    exp.set_corr(c)
    j4, j5, j6 = exp.get_jump_status()
    table.append([c, i, j1, j2, j3, j4, j5, j6, j1 == j4, j2==j5, j3==j6])


table = pd.DataFrame.from_records(table, columns=labels)
