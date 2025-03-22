import pandas as pd
from pvlib import pvsystem
from pvlib import location
from pvlib import modelchain
from pvlib.temperature import TEMPERATURE_MODEL_PARAMETERS as PARAMS
from pvlib.bifacial.pvfactors import pvfactors_timeseries
import warnings
import matplotlib.pyplot as plt

# supressing shapely warnings that occur on import of pvfactors
warnings.filterwarnings(action='ignore', module='pvfactors')

# create site location and times characteristics
locations = {
    'latitude': [58.4546, -26.3167, -0.0206],
    'longitude': [-134.1739, 31.1333, 109.3414],
    'timezone': ['America/Juneau', 'Africa/Mbabane', 'Asia/Pontianak'],
    'name': ['Juneau, Alaska (USA)', 'Mbabane, Eswatini', 'Pontianak, Indonesia']
}

# create system locations and times as dataframes
locations_df = pd.DataFrame(locations)

# create site system characteristics
axis_tilt = 0
axis_azimuth = 180
gcr = 0.35
max_angle = 60
pvrow_height = 3
pvrow_width = 4
albedo = 0.2
bifaciality = 0.75

# load temperature parameters and module/inverter specifications
temp_model_parameters = PARAMS['sapm']['open_rack_glass_glass']
cec_modules = pvsystem.retrieve_sam('CECMod')
cec_module = cec_modules['Trina_Solar_TSM_300DEG5C_07_II_']
cec_inverters = pvsystem.retrieve_sam('cecinverter')
cec_inverter = cec_inverters['ABB__MICRO_0_25_I_OUTD_US_208__208V_']

sat_mount = pvsystem.SingleAxisTrackerMount(axis_tilt=axis_tilt,
                                            axis_azimuth=axis_azimuth,
                                            max_angle=max_angle,
                                            backtrack=True,
                                            gcr=gcr)

# set up figure for plot
figure, axis = plt.subplots(len(locations_df['name']),1)

for index, site in locations_df.iterrows():

    lat = site['latitude']
    lon = site['longitude']
    tz = site['timezone']
    times = pd.date_range('2021-06-21', '2021-6-22', freq='1min', tz=tz)

    # create a location for site, and get solar position and clearsky data
    site_location = location.Location(lat, lon, tz=tz, name = site['name'])
    solar_position = site_location.get_solarposition(times)
    cs = site_location.get_clearsky(times)

    orientation = sat_mount.get_orientation(solar_position['apparent_zenith'],
                                        solar_position['azimuth'])

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


    # dc arrays
    array = pvsystem.Array(mount=sat_mount,
                        module_parameters=cec_module,
                        temperature_model_parameters=temp_model_parameters)

    # create system object
    system = pvsystem.PVSystem(arrays=[array],
                            inverter_parameters=cec_inverter)
    
    # turn into pandas DataFrame
    irrad = pd.concat(irrad, axis=1)

    # create bifacial effective irradiance using aoi-corrected timeseries values
    irrad['effective_irradiance'] = (
        irrad['total_abs_front'] + (irrad['total_abs_back'] * bifaciality)
    )

    # ModelChain requires the parameter aoi_loss to have a value. pvfactors
    # applies surface reflection models in the calculation of front and back
    # irradiance, so assign aoi_model='no_loss' to avoid double counting
    # reflections.
    mc_bpv = modelchain.ModelChain(system, site_location, aoi_model='no_loss')
    mc_bpv.run_model_from_effective_irradiance(irrad)

    # create irradiance for front face only
    # aoi value is set to 'physical' in this case
    irrad['effective_irradiance'] = (
        irrad['total_abs_front']
    )

    mc_mpv = modelchain.ModelChain(system, site_location, aoi_model='physical' )
    mc_mpv.run_model_from_effective_irradiance(irrad)

    # plot results
    axis[index].plot(times, mc_bpv.results.ac, 'r', times, mc_mpv.results.ac, 'b')
    axis[index].set_title(site_location.name)
    axis[index].set_ylabel('AC Power (W)')
    axis[index].set_xlabel('Time')

plt.tight_layout()
plt.show()
