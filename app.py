from fastapi import FastAPI, Query, Response
from fastapi.middleware.cors import CORSMiddleware
import pdal
import json
import pyarrow as pa
import pyarrow.ipc as ipc
import numpy as np
import pygeos
import json
import geopandas as gpd

from mercantile import bounds  

app = FastAPI()

COPC_PATH = "data_processing/output.copc.laz"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/points")
def get_points(
    minx: float = Query(-180), maxx: float = Query(180),
    miny: float = Query(-90), maxy: float = Query(90),
    minz: float = Query(10), maxz: float = Query(30),
    #zoom: int = Query(10)
    limit: int = Query(1000)
):
    # bbox_volume = (maxx - minx) * (maxy - miny) * (maxz - minz)

    # # Define sampling radius or limit based on zoom or bbox size
    # if zoom <= 5:
    #     sample_radius = 50.0  # meters, very coarse
    # elif zoom <= 10:
    #     sample_radius = 5.0
    # else:
    #     sample_radius = 0.1   # very fine, lots of points

    pipeline_json = {
        "pipeline": [
            {
                "type": "readers.copc",
                "filename": COPC_PATH,
                "bounds": f"([{minx},{maxx}],[{miny},{maxy}],[{minz},{maxz}])" #spatial filtering
            },
            
            {
                "type": "filters.head", "count": limit
            },
            # Attribute level filtering (thresholding)
            # {
            #     "type": "filters.range",
            #     "limits": f"Intensity[1:2]"
            # },

            # For level of detail
            # {
            #     "type": "filters.sample",
            #     "radius": sample_radius
            # }
        ]
    }

    pipeline = pdal.Pipeline(json.dumps(pipeline_json))
    try:
        pipeline.execute()
        arrays = pipeline.arrays
    except RuntimeError as e:
        return Response(content=str(e), status_code=500)

    if not arrays or len(arrays[0]) == 0:
        return Response(status_code=204)  # No points found

    arr = arrays[0]
    # Directly extract numpy arrays from PDAL output
    x = arr["X"].astype(np.float64)
    y = arr["Y"].astype(np.float64)
    z = arr["Z"].astype(np.float64)
    if "Intensity" in arr.dtype.names:
        intensity = arr["Intensity"].astype(np.float32).flatten()
    else:
        intensity = np.zeros_like(x, dtype=np.float32).flatten()
    
    print(x.shape, y.shape, z.shape, intensity.shape)
    print("*******************************")

    # Stack coordinates into (N, 3) array for geometry
    coords_xyz = np.column_stack((x, y, z)).astype(np.float64)
    geometry_array = pygeos.points(coords_xyz)
    coords = pygeos.get_coordinates(geometry_array, include_z=True)
    flat_coords = coords.flatten()

    # Create a FixedSizeListArray of size 3 for XYZ points
    arrow_geom = pa.FixedSizeListArray.from_arrays(
        pa.array(flat_coords, type=pa.float64()),
        list_size=3
    )

    arrow_intensity = pa.array(intensity.tolist(), type=pa.float32())

    # GeoArrow extension metadata for Point[xyz] with EPSG:4326
    geo_metadata = {
        "extension:name": "geoarrow.point",
        "extension:metadata": json.dumps({
            "geometry_type": "Point",
            "coords": "xyz",
            "crs": "EPSG:4326"
        })
    }

    # Apply metadata to geometry field
    geometry_field = pa.field(
        "geometry",
        pa.list_(pa.float64(), list_size=3),
        metadata={f"ARROW:{k}".encode(): v.encode() for k, v in geo_metadata.items()}
    )

    # Create the schema
    schema = pa.schema([
        geometry_field,
        pa.field("intensity", pa.float32())
    ])

    table = pa.Table.from_arrays([arrow_geom, arrow_intensity], schema=schema)
    print("table", table)


    sink = pa.BufferOutputStream()
    with ipc.new_stream(sink, table.schema) as writer:
        writer.write_table(table)
    buffer = sink.getvalue()

    return Response(content=buffer.to_pybytes(), media_type="application/vnd.apache.arrow.stream")
