import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import pvlib
from pvlib import pvsystem
from pvlib.bifacial.pvfactors import pvfactors_timeseries
import warnings
import math
locations_df = pd.read_excel('module_data.xlsx', sheet_name='locations')
locations_df = locations_df.sort_values(by='longitude',key=abs)
locations_df = locations_df.reset_index(drop=True)
print(locations_df)
    