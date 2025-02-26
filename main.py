import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pvlib import pvsystem
from pvlib.bifacial.pvfactors import pvfactors_timeseries
import warnings

pvrow_height = 1
pvrow_width = 4
pitch = 10
gcr = pvrow_width / pitch
axis_azimuth = 180
albedo = 0.2

module_parameters = {'pdc0': 5000, 'gamma_pdc': -0.004}
inverter_parameters = {'pdc0': 5000, 'eta_inv_nom': 0.96}

system = pvsystem.PVSystem(inverter_parameters=inverter_parameters,
                           module_parameters=module_parameters,name='Test System')


pdc = system.pvwatts_dc(g_poa_effective=1000, temp_cell=30)


def get_underline(system_name):
    underline = ''
    for char in list(system_name):
        underline += '_' 
    return underline


print(f'''

{system.name}
{get_underline(system.name)}

Inverter Params:  {system.inverter_parameters}

DC Power:  {pdc}

      ''')