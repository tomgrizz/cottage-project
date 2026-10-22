# Almond Lane Cottage

Website for Almond Lane Cottage, a two-bedroom waterfront rental on Big Clear Lake in Arden, Ontario.

Live site: https://tomgrizz.github.io/cottage-project/

## Files

- `index.html` – the whole page (text, rates, booking form)
- `css/style.css` – colours, fonts and layout
- `js/main.js` – photo viewer, booking form, depth map readout
- `images/` – web-sized photos with location data removed
- `tools/build_depth_map.py` – draws the Big Clear Lake depth map into `index.html`

## Common edits

- **Contact email:** replace `your-email@example.com` in `index.html` (3 places).
- **Rates:** edit the table in the `#rates` section of `index.html`.
- **Photos:** add web-sized copies to `images/` and a new `<button class="g">` tile in the `#photos` section.

## Depth map

Run `python tools/build_depth_map.py` after changing the script. It rewrites the block between the
`depth-map:start` and `depth-map:end` markers in `index.html`.

Data sources:

- Depth contours: Ontario Ministry of Natural Resources, Bathymetry Line (1984 survey). Contains information
  licensed under the [Open Government Licence – Ontario](https://www.ontario.ca/page/open-government-licence-ontario).
  Not for navigation.
- Shoreline and islands: © [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors (relation 1146593).
