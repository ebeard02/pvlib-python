import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import pvlib
from pvlib import pvsystem
from pvlib.bifacial.pvfactors import pvfactors_timeseries
import warnings

# pvrow_height = 1
# pvrow_width = 4
# pitch = 10
# gcr = pvrow_width / pitch
# axis_azimuth = 180
# albedo = 0.2

# module_parameters = {'pdc0': 5000, 'gamma_pdc': -0.004}
# inverter_parameters = {'pdc0': 5000, 'eta_inv_nom': 0.96}

# system = pvsystem.PVSystem(inverter_parameters=inverter_parameters,
#                            module_parameters=module_parameters,name='Test System')


# pdc = system.pvwatts_dc(g_poa_effective=1000, temp_cell=30)


# def get_underline(system_name):
#     underline = ''
#     for char in list(system_name):
#         underline += '_' 
#     return underline


# print(f'''

# {system.name}
# {get_underline(system.name)}

# Inverter Params:  {system.inverter_parameters}

# DC Power:  {pdc}

#       ''')

# Define location coordinates (example: Dayton, Ohio)
latitude = 39.7589
longitude = -84.1916
tz = 'Etc/GMT+5'

# Define time range for the simulation
times = pd.date_range('2025-03-22', '2025-03-23', freq='1h', tz=tz)

# Create a Location object
location = pvlib.location.Location(latitude, longitude)

# Get solar position data
solar_position = location.get_solarposition(times)

# Define weather data for a typical day (adjust as needed)
weather = pd.DataFrame({
    'dni': [500] * len(times),  # Direct Normal Irradiance (W/m^2)
    'ghi': [600] * len(times),  # Global Horizontal Irradiance (W/m^2)
    'dhi': [100] * len(times),  # Diffuse Horizontal Irradiance (W/m^2)
    'temp_air': [25] * len(times),  # Air temperature (°C)
    'wind_speed': [5] * len(times),  # Wind speed (m/s)
}, index=times)

# Retrieve the module database
module_database = pvsystem.retrieve_sam('cecmod')  # 'cecmod' for the CEC module database
module_name = 'Canadian_Solar_CS5P_220M___2009_'

# Retrieve the inverter database
inverter_database = pvsystem.retrieve_sam('cecinverter')  # 'cecinverter' for CEC inverter database

# List all available inverter names (optional, to confirm the correct name)
inverter_names = inverter_database.columns
inverter_name = 'ABB__MICRO_0_25_I_OUTD_US_240__240V_'

# Create a PVSystem object for bifacial panels
system = pvsystem.PVSystem(
    surface_tilt=30,  # Tilt angle of the panels
    surface_azimuth=180,  # Azimuth (facing south)
    module= module_name,  
    inverter= inverter_name,  
    albedo=0.25,  # Ground reflectance
    module_parameters = module_database[module_name],
    inverter_parameters= inverter_names[inverter_name]


)

# Use a ModelChain to link system and location
mc = pvlib.modelchain.ModelChain(system, location)

# Run the simulation using weather data
mc.run_model(weather)

# Get AC power output
ac_power = mc.results.ac

# Output the results
print(ac_power)