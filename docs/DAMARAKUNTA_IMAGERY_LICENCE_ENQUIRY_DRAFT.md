# Draft enquiry: Esri World Imagery mosaic for Damarakunta (DRAFT for your review; NOT sent; no permission has been granted)

## Status and route
- Route B1 (ask first) approved by you. Nothing is sent by me. No imagery is exported or downloaded while this is open.
- **Contact route: not established by evidence.** I found no verified Esri licensing contact or CBIT GIS-office contact in the material I have seen (WebFetch to some sites is restricted here). Evidence I do have: Esri's terms summary (21 Apr 2025) and support article 000014855 (World Imagery "for Export" is for small volumes). Suggested first step, which you should confirm yourself: ask your project guide whether CBIT holds an ArcGIS/Esri licence and who administers it, then use the contact Esri's own licensing/terms page lists for your account type.

## Facts to state (all from the project files; check them before sending)
- Area: Damarakunta village, Markook Mandal, Siddipet, Telangana; about 18.5 km2 polygon, bounding box 29.2 km2.
- Obtained with 11 map-image export requests (`MapServer/export`) of Esri World Imagery in early October 2026 (tiles dated 4 Oct), stored as a 0.6 m GeoTIFF mosaic (11,296 x 7,171 px, about 243 MB).
- Uses so far: tiled CPU segmentation inference (building class), overlay of public Telangana (TGRAC) road/boundary layers, road/building planning analysis for an M.Tech thesis.
- No imagery has been shared outside the project folder. (Confirm this is true before sending.)

## Factual questions (answerable by licence text or by the licensing contact)
1. **Retention.** Under which licence or terms was World Imagery accessed through the export interface, and may the already-exported 0.6 m mosaic of this one village be retained locally for the duration of the thesis and the examination period?
2. **Processing.** Are image processing and derived analysis (machine-learning inference, building/road extraction, raster alignment) permitted on that mosaic?
3. **Academic use.** May the imagery and its derived products be used in academic research and an M.Tech thesis submitted to CBIT?

## Questions that need an interpretation by Esri or CBIT (we cannot decide these ourselves)
4. **Figures.** May figures that contain the imagery (or crops of it) appear in a thesis and in a conference paper/publication? If so, at what maximum resolution or extent, and with what caption wording?
5. **Derived vectors.** May vector outputs derived from the imagery (building footprint polygons, planned route lines) be redistributed or archived publicly (for example with the paper)? Does your answer differ for model-predicted footprints versus manually digitised reference footprints?
6. **Attribution and conditions.** What exact attribution text, licence conditions and restrictions apply (including any limit on volume, redistribution of the raw tiles, or sharing the model predictions)?

## Draft message (edit freely)
Subject: Licence clarification for academic use of Esri World Imagery (one village, M.Tech thesis, CBIT)

Dear [Name / GIS Office / Esri licensing],

I am an M.Tech student at CBIT working on rural infrastructure planning for one village (Damarakunta, Markook Mandal, Siddipet, Telangana). In early October 2026 I exported Esri World Imagery for the village area through the map export interface (11 requests, about 243 MB as one 0.6 m GeoTIFF). I have not exported more imagery since and will not do so until I hear from you.

Please could you tell me: [paste questions 1-6 above].

I am not asking you to approve anything beyond the use described. I will follow the attribution and conditions you specify.

Thank you,
Ashish Chantibabu Geddam, CBIT M.Tech (roll no. 160125763017)

## What stays labelled until you have an answer
Every output derived from the mosaic carries "imagery licence: UNRESOLVED". Reference-label work (below) and the overlay check use the existing local mosaic only; they do not expand the imagery holding. If the answer is "no", the fallback is B3 (replace the imagery source), which would be a new decision for you.
