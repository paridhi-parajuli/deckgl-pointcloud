import { tableFromIPC } from "apache-arrow";
import { GeoArrowScatterplotLayer } from "@geoarrow/deck.gl-layers";
import { Deck } from "@deck.gl/core";
import { TileLayer } from '@deck.gl/geo-layers';
import { BitmapLayer } from '@deck.gl/layers';

async function fetchArrowTable() {
  const response = await fetch("http://127.0.0.1:8000/points?minx=0&maxx=90&miny=0&maxy=90&minz=0&maxz=4000&limit=100");
  //const response = await fetch("calipso_backscatter_3d.feather");
  
  const buffer = await response.arrayBuffer();
  return tableFromIPC(buffer);
}

async function renderDeck() {
  const table = await fetchArrowTable();

  console.log("table is", table)
  console.log("number of rows", table.numRows)
  console.log("number of rows", table.numCols)
  console.log(table.schema.fields.map(f => f.name));
  const geometryVector = table.getChild('geometry');
  const intensityVector = table.getChild('intensity')
  console.log("Geometry Vector:", geometryVector);
  console.log(geometryVector?.get(0));
  console.log("Geometry Type:", geometryVector?.type?.toString());
  console.log("First item:", geometryVector?.get(0));
  for (let i=0; i < Math.min(5, table.numRows); i++) {
    console.log("Geometry", i, geometryVector?.get(i));
  }
  console.log("Schema:", table.schema.toString());
  

  const baseLayer = new TileLayer({
    id: 'base-map',
    data: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
    minZoom: 0,
    maxZoom: 19,
    tileSize: 256,
    renderSubLayers: props => {
      const { boundingBox: bbox, content: image } = props.tile;
      if (!image) return null;

      return new BitmapLayer(props, {
        data: null,
        image: image,
        bounds: [bbox[0][0], bbox[0][1], bbox[1][0], bbox[1][1]],
      });
    }
  });
  

  const geoArrowLayer = new GeoArrowScatterplotLayer({
    id: "geoarrow-layer",
    data: table,
    getPosition: table.getChild("geometry"),
    getFillColor: (rowIndex) => {
    const i = intensityVector.get(rowIndex);
    const normalized = Math.min(1.0, Math.max(0.0, i / 3));

    const r = Math.round(255 * normalized);
    const g = Math.round(255 * (1 - Math.abs(normalized - 0.5) * 2));
    const b = Math.round(255 * (1 - normalized));

    return [r, g, b, 200]; // RGBA
    },

    radiusMinPixels: 2,

  });

  new Deck({
    parent: document.getElementById("deck-canvas"),
    initialViewState: {
      longitude: 20,
      latitude: 20,
      zoom: 4,
    },
    controller: true,
    layers: [baseLayer,
         geoArrowLayer
        ],
  });
}

renderDeck();
