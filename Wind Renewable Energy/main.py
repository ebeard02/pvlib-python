import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import pvlib
from pvlib import pvsystem
from pvlib.bifacial.pvfactors import pvfactors_timeseries
import warnings
import math

col = 0
row = 0

albedos_df = pd.read_excel('module_data.xlsx', sheet_name='albedos')
print(math.ceil(len(albedos_df['Albedo'])/4))
for index, site in albedos_df.iterrows():

   
    if index % 4 == 0 and index != 0:
        col += 1
        row = 0

    print(f'{row},{col}')
    row += 1
    