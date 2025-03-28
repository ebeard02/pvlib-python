import pandas as pd
from pvlib import pvsystem
from pvlib import location
from pvlib import modelchain
from pvlib.temperature import TEMPERATURE_MODEL_PARAMETERS as PARAMS
from pvlib.bifacial.pvfactors import pvfactors_timeseries
import warnings
import matplotlib.pyplot as plt
from pvlib import temperature
import math

# supressing shapely warnings that occur on import of pvfactors
warnings.filterwarnings(action='ignore', module='pvfactors')

# using Greensboro, NC for this example
lat, lon = 36.084, -79.817
tz = 'Etc/GMT+5'
times = pd.date_range('2021-06-21', '2021-06-22', freq='1h', tz=tz)

# create location object and get clearsky data
site_location = location.Location(lat, lon, tz=tz, name='Greensboro, NC')
cs = site_location.get_clearsky(times)

# create site system characteristics
axis_tilt = 0
axis_azimuth = 180
gcr = 0.35
max_angle = 60
pvrow_height = 3
pvrow_width = 4
bifaciality = 0.75

# import albedo data from excel
albedos_df = pd.read_excel('module_data.xlsx', sheet_name='albedos')

# pvsystem parameters for DC outputs
# pdc0 is based on panel parameters at STC
pdc0 = 320
gamma_pdc = -0.0043

# load temperature parameters and module/inverter specifications
temp_model_parameters = PARAMS['sapm']['open_rack_glass_glass']
cec_modules = pvsystem.retrieve_sam('CECMod')
cec_module = cec_modules['Zytech_Solar_ZT320P']
cec_inverters = pvsystem.retrieve_sam('cecinverter')
cec_inverter = cec_inverters['iPower__SHO_5_2__240V_']

sat_mount = pvsystem.SingleAxisTrackerMount(axis_tilt=axis_tilt,
                                            axis_azimuth=axis_azimuth,
                                            max_angle=max_angle,
                                            backtrack=True,
                                            gcr=gcr)

solar_position = site_location.get_solarposition(times)

orientation = sat_mount.get_orientation(solar_position['apparent_zenith'],
                                        solar_position['azimuth'])

# set up figure for plot
fig1, axis1 = plt.subplots(4,math.ceil(len(albedos_df['Albedo'])/4))
fig2, axis2 = plt.subplots(4,math.ceil(len(albedos_df['Albedo'])/4))
col = 0
row = 0

# output setup
data = []
output_df = pd.DataFrame(data) 

for index, site in albedos_df.iterrows():

    site_name = site['Substance or Surface']
    albedo = site['Albedo']

    # get rear and front side irradiance from pvfactors transposition engine
    # explicity simulate on pvarray with 3 rows, with sensor placed in middle row
    # users may select different values depending on needs
    irrad = pvfactors_timeseries(solar_position['azimuth'],
                                solar_position['apparent_zenith'],
                                orientation['surface_azimuth'],
                                orientation['surface_tilt'],
                                axis_azimuth,
                                times,
                                cs['dni'],
                                cs['dhi'],
                                gcr,
                                pvrow_height,
                                pvrow_width,
                                albedo,
                                n_pvrows=3,
                                index_observed_pvrow=1
                                )

    # turn into pandas DataFrame
    irrad = pd.concat(irrad, axis=1)

    # dc arrays
    array = pvsystem.Array(mount=sat_mount,
                        module_parameters=cec_module,
                        temperature_model_parameters=temp_model_parameters)

    # create system object
    system = pvsystem.PVSystem(arrays=[array], 
                               inverter_parameters=cec_inverter)
    
    # create bifacial effective irradiance using aoi-corrected timeseries values
    irrad['effective_irradiance'] = (
        irrad['total_abs_front'] + (irrad['total_abs_back'] * bifaciality)
    )

    # get cell temperature using the Faiman model for bifacial irradiance
    temp_cell = temperature.faiman(irrad['effective_irradiance'], temp_air=25,
                               wind_speed=1)

    # ModelChain requires the parameter aoi_loss to have a value. pvfactors
    # applies surface reflection models in the calculation of front and back
    # irradiance, so assign aoi_model='no_loss' to avoid double counting
    # reflections.
    bpv_ac = modelchain.ModelChain(system, site_location, aoi_model='no_loss')
    bpv_ac.run_model_from_effective_irradiance(irrad)

    # DC results using pvsystem
    bpv_dc = pvsystem.pvwatts_dc(irrad['effective_irradiance'],
                               temp_cell,
                               pdc0,
                               gamma_pdc=gamma_pdc
                               ).fillna(0)

    # create irradiance for front face only
    # aoi value is set to 'physical' in this case
    irrad['effective_irradiance'] = (
        irrad['total_abs_front']
    )

    # AC results for monofacial panel
    mpv_ac = modelchain.ModelChain(system, site_location, aoi_model='physical')
    mpv_ac.run_model_from_effective_irradiance(irrad)

    # DC results for monofacial panel
    mpv_dc = pvsystem.pvwatts_dc(irrad['effective_irradiance'],
                               temp_cell,
                               pdc0,
                               gamma_pdc=gamma_pdc
                               ).fillna(0)

    # print AC max values
    bpv_max_ac = round(max(bpv_ac.results.ac),2)
    mpv_max_ac = round(max(mpv_ac.results.ac),2)
    perc_diff_ac = round(abs(bpv_max_ac-mpv_max_ac)/bpv_max_ac*100,2)

    temp_df_ac = pd.DataFrame({
                            'Albedo': [albedo],
                            'Max BPV Power AC (W)': [bpv_max_ac],
                            'Max MPV Power AC (W)': [mpv_max_ac],
                            'Percent Difference (%)': [perc_diff_ac]})

    # print DC max values 
    bpv_max_dc = round(max(bpv_dc),2)
    mpv_max_dc = round(max(mpv_dc),2)
    perc_diff_dc = round(abs(mpv_max_dc-bpv_max_dc)/bpv_max_dc*100,2)

    temp_df_dc = pd.DataFrame({
                            'Max BPV Power DC (W)': [bpv_max_dc],
                            'Max MPV Power DC (W)': [mpv_max_dc],
                            'Percent Difference (%)': [perc_diff_dc]})
    
    horizontal_concat = pd.concat([temp_df_ac, temp_df_dc], axis=1)
    output_df = pd.concat([output_df,horizontal_concat])

    # plot results
    if index % 4 == 0 and index != 0:
        col += 1
        row = 0
    
    axis1[row,col].plot(times,bpv_ac.results.ac,'r',times,mpv_ac.results.ac,'b')
    axis1[row,col].set_title(f'{site_name}: {albedo}')
    axis1[row,col].set_ylabel('AC Power (W)')
    axis1[row,col].set_xlabel('Time')

    axis2[row,col].plot(times,bpv_dc,'r',times,mpv_dc,'b')
    axis2[row,col].set_title(f'{site_name}: {albedo}')
    axis2[row,col].set_ylabel('AC Power (W)')
    axis2[row,col].set_xlabel('Time')

    row += 1

print(f'''
      
SIMULATION RESULTS
-------------------------------------------------------------------------------------------------------------------------------------------------

Input Table:
{albedos_df}

Output Table:
{output_df}

-------------------------------------------------------------------------------------------------------------------------------------------------
      ''')


fig1.suptitle("AC Results")
fig1.tight_layout()
fig2.suptitle("DC Results")
fig2.tight_layout()

plt.show()
