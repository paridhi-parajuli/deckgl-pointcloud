# works fine
import numpy as np
from pyhdf.SD import SD, SDC
import laspy
from pyproj import CRS
import pdal
import json

# Load HDF
filename = 'CAL_LID_L1-Standard-V4-51.2023-06-30T21-39-53ZD.hdf'
f = SD(filename, SDC.READ)

# Load arrays
lat = f.select('Latitude')[:].flatten()           # (63855,)
lon = f.select('Longitude')[:].flatten()
bsc = f.select('Total_Attenuated_Backscatter_532')[:]  # (63855, 583)
bsc = np.where(bsc > 0, bsc, np.nan)
alt = np.linspace(0, 30.1, 583) * 1000  # in meters (shape: 583,)

# Transpose to (altitude, along-track)
bsc_T = bsc.T  # shape: (583, 63855)

# Build point arrays using broadcasting
n_time = lat.shape[0]
n_alt = alt.shape[0]
N = n_time * n_alt

# Create meshgrids and flatten
ALT = np.repeat(alt, n_time)           # shape: (N,)
LAT = np.tile(lat, n_alt)              # shape: (N,)
LON = np.tile(lon, n_alt)              # shape: (N,)
INT = bsc_T.flatten()                  # shape: (N,)

# Mask invalid (NaN) values efficiently
valid = ~np.isnan(INT)

z = ALT[valid].astype(np.float64)
y = LAT[valid].astype(np.float64)
x = LON[valid].astype(np.float64)
intensity = INT[valid].astype(np.uint16)

print(f"Valid points: {len(x):,}")

# Write directly to LAS
las = laspy.create(point_format=3, file_version="1.2")

# Set offsets and scales (critical for proper rendering)
las.header.offsets = [0.0, 0.0, 0.0]
las.header.scales = [0.000001, 0.000001,0.0001]  # alt in cm, lat/lon in microdeg
crs = CRS.from_epsg(4326)
las.header.add_crs(crs)


las.x = x
las.y = y
las.z = z
las.intensity = intensity
print(x.shape, y.shape, z.shape, intensity.shape)

las.write("output.las")


# Input and output filenames
input_laz = "output.las"
output_copc = "output.copc.laz"

# Define the PDAL pipeline as a Python dictionary
pipeline_dict = {
    "pipeline": [
        {
            "type": "readers.las",
            "filename": input_laz
        },
        {
            "type": "writers.copc",
            "filename": output_copc,
            # Optional COPC writer parameters:
            # "resolution": 10.0,
            # "depth_end": 10,
            #"wkt": "EPSG:4326"
        }
    ]
}

# Convert pipeline to JSON string
pipeline_json = json.dumps(pipeline_dict)

# Create and run the pipeline
pipeline = pdal.Pipeline(pipeline_json)
pipeline.execute()

print(f"Conversion complete: {output_copc}")