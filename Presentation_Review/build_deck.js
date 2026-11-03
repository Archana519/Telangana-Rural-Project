// Builds MTech_Major_Project_Review.pptx  (all numbers traced in PRESENTATION_RESULTS_AUDIT.md)
const pptxgen = require("pptxgenjs");
const sharp = require("sharp");
const path = require("path");

const IMG = path.join(__dirname, "images");
const OUT = path.join(__dirname, "MTech_Major_Project_Review.pptx");

const DARK = "16382E", MID = "2E7D5B", ACC = "D99A00", LIGHT = "F1F5F3", TXT = "1E2B26",
  MUTED = "5B6B64", WARN = "B5483A", BLUE = "3A6EA5", WHITE = "FFFFFF", RULE = "D5DDD9";
const HF = "Cambria", BF = "Calibri";

const pres = new pptxgen();
pres.layout = "LAYOUT_16x9"; // 10 x 5.625 in
pres.author = "Pendyala Archana";
pres.title = "M.Tech Major Project Review - Smart Village Road Network Planning";
pres.theme = { headFontFace: HF, bodyFontFace: BF };

pres.defineSlideMaster({
  title: "CONTENT", background: { color: WHITE },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.5, y: 0.25, w: 9, h: 0.75, fontFace: HF, fontSize: 28, bold: true, color: DARK, valign: "middle", margin: 0 }, text: "" } },
  ],
  slideNumber: { x: 9.1, y: 5.3, w: 0.5, h: 0.25, fontFace: BF, fontSize: 10, color: MUTED },
});
pres.defineSlideMaster({ title: "DARK", background: { color: DARK } });

const state = { n: 0 };
function content(title, notes) {
  const s = pres.addSlide({ masterName: "CONTENT" });
  s.addText(title, { placeholder: "title" });
  s.addNotes(notes);
  return s;
}
async function dims(f) { const m = await sharp(path.join(IMG, f)).metadata(); return m.width / m.height; }
async function pic(s, f, x, y, w, h, name) {
  const ar = await dims(f);
  let pw = w, ph = w / ar;
  if (ph > h) { ph = h; pw = h * ar; }
  s.addImage({ path: path.join(IMG, f), x: x + (w - pw) / 2, y: y + (h - ph) / 2, w: pw, h: ph, altText: name || f });
}
function card(s, x, y, w, h, fill) {
  s.addShape(pres.shapes.RECTANGLE, { x, y, w, h, fill: { color: fill || LIGHT }, line: { color: RULE, width: 0.75 } });
}
function txt(s, t, o) { s.addText(t, Object.assign({ isTextBox: true, fontFace: BF, fontSize: 14, color: TXT, margin: 0, valign: "top" }, o)); }
function bullets(s, items, o) {
  const arr = items.map((t, i) => ({ text: t, options: { bullet: true, breakLine: i < items.length - 1, paraSpaceAfter: 6 } }));
  s.addText(arr, Object.assign({ isTextBox: true, fontFace: BF, fontSize: 14, color: TXT, margin: 0, valign: "top" }, o));
}
function chip(s, t, x, y, w, color) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h: 0.3, fill: { color }, line: { color }, rectRadius: 0.08 });
  s.addText(t, { x, y, w, h: 0.3, align: "center", valign: "middle", fontFace: BF, fontSize: 10, bold: true, color: WHITE, margin: 0, isTextBox: true });
}
function hc(t) { return { text: t, options: { bold: true, color: WHITE, fill: { color: DARK }, fontSize: 10, fontFace: BF, valign: "middle" } }; }
function c(t, o) { return { text: t, options: Object.assign({ fontSize: 10, fontFace: BF, color: TXT, valign: "top" }, o || {}) }; }
function table(s, rows, x, y, w, colW, o) {
  s.addTable(rows, Object.assign({ x, y, w, colW, border: { type: "solid", pt: 0.5, color: RULE }, margin: [0.03, 0.05, 0.03, 0.05], autoPage: false }, o || {}));
}

(async () => {
  // ---------- 1 Title ----------
  {
    const s = pres.addSlide({ masterName: "DARK" });
    s.addNotes("Good morning. My major project is about planning rural road connections for a village using satellite images and GIS data. I studied one village, Damarakunta in Siddipet district. This is a review of work in progress, so I will clearly separate what is finished and verified from what is still pending.");
    txt(s, "M.Tech Major Project Review", { x: 0.5, y: 0.45, w: 5, h: 0.3, fontSize: 14, color: ACC, bold: true });
    txt(s, "GIS-Based Smart Village Infrastructure Planning and Multi-Criteria Rural Road Network Optimization Using Remote Sensing and AI", { x: 0.5, y: 0.95, w: 5.0, h: 2.2, fontFace: HF, fontSize: 24, bold: true, color: WHITE });
    txt(s, [
      { text: "Pendyala Archana", options: { bold: true, breakLine: true } },
      { text: "M.Tech Information Technology: AI and Robotics", options: { breakLine: true } },
      { text: "Chaitanya Bharathi Institute of Technology, Hyderabad", options: { breakLine: true } },
      { text: "Study area: Damarakunta, Markook Mandal, Siddipet, Telangana" },
    ], { x: 0.5, y: 3.5, w: 5.0, h: 1.4, fontSize: 14, color: "DCE8E2", paraSpaceAfter: 4 });
    await pic(s, "map_study_area.jpg", 5.75, 0.8, 3.8, 3.9, "Damarakunta study area on satellite imagery");
    txt(s, "Imagery source and licence: to be confirmed", { x: 5.75, y: 4.75, w: 3.8, h: 0.25, fontSize: 10, color: "B8C9C1" });
  }

  // ---------- 2 Abstract ----------
  {
    const s = content("Abstract", "Rural villages often lack a clear plan for connecting houses and public facilities to the road network. I took Damarakunta village as the study area. I combined a satellite mosaic, a village boundary, existing roads, building candidates, land cover and terrain into one planning grid. A planner then generates alternative low-cost routes and selects them into one shared network. I also test what happens when some buildings are missing from the input. Planning runs are executed and numbers are verified for the primary run. Connectivity checks, field validation and a second village are still pending. The outputs are planning support, not construction designs.");
    txt(s, "Rural road planning needs many spatial datasets together. This project builds a GIS and least-cost-path planner for Damarakunta village (18.466 km²), using satellite imagery, roads, building candidates, land cover and slope. It generates alternative routes, selects a shared network, and tests how missing building data changes the result.", { x: 0.5, y: 1.1, w: 9, h: 1.2, fontSize: 14 });
    card(s, 0.5, 2.5, 4.4, 2.6, "E6F2EC");
    txt(s, "Completed so far", { x: 0.7, y: 2.6, w: 4, h: 0.3, fontSize: 16, bold: true, color: MID, fontFace: HF });
    bullets(s, ["Data integrated on a 10 m grid", "163 house and 4 facility routes generated", "C1 omission and C2 ablation runs executed"], { x: 0.7, y: 3.0, w: 4.0, h: 2.0, fontSize: 14 });
    card(s, 5.1, 2.5, 4.4, 2.6, "FBF1DC");
    txt(s, "Ongoing or pending", { x: 5.3, y: 2.6, w: 4, h: 0.3, fontSize: 16, bold: true, color: "8A6100", fontFace: HF });
    bullets(s, ["Connectivity exception (one house)", "Imagery licence and data-source checks", "Field or expert validation; second village (C3)"], { x: 5.3, y: 3.0, w: 4.0, h: 2.0, fontSize: 14 });
  }

  // ---------- 3 Introduction ----------
  {
    const s = content("Introduction", "Roads decide whether a family can reach a school or a health centre. Satellite images and GIS let us look at a whole village at once. But a good route depends on terrain, land cover, existing roads, facilities and where buildings are. An automated planner can compare many alternatives quickly. The results still need engineers and local field checks before anything is built.");
    const rows = [
      ["1", "Why roads matter", "Access to schools, health care and markets"],
      ["2", "Why satellite and GIS", "One view of a whole village, layers can be combined"],
      ["3", "Why many layers", "Terrain, land cover, roads, facilities and buildings all change a route"],
      ["4", "Why automate", "Compare many alternatives quickly and consistently"],
      ["5", "Why verify", "Outputs are model results; experts and field checks are still needed"],
    ];
    rows.forEach((r, i) => {
      const y = 1.2 + i * 0.78;
      s.addShape(pres.shapes.OVAL, { x: 0.6, y, w: 0.55, h: 0.55, fill: { color: MID }, line: { color: MID } });
      s.addText(r[0], { x: 0.6, y, w: 0.55, h: 0.55, align: "center", valign: "middle", bold: true, color: WHITE, fontSize: 16, fontFace: BF, margin: 0, isTextBox: true });
      txt(s, r[1], { x: 1.4, y: y + 0.02, w: 2.8, h: 0.5, fontSize: 16, bold: true, valign: "middle", color: DARK });
      txt(s, r[2], { x: 4.2, y: y + 0.02, w: 5.3, h: 0.5, fontSize: 14, valign: "middle" });
    });
  }

  // ---------- 4 Problem ----------
  {
    const s = content("Problem statement", "The main problem is how to plan rural road connections when the data come from many sources and are not perfect. Building information may be incomplete. Routes must respect terrain, land cover and existing roads. And if we plan each route alone we can count the same road several times, so we should plan the routes together.");
    card(s, 0.5, 1.15, 9, 1.0, DARK);
    txt(s, "How can alternative rural road connections be generated and combined into a shared network from multi-source GIS data, when building information may be incomplete?", { x: 0.7, y: 1.2, w: 8.6, h: 0.9, fontSize: 16, bold: true, color: WHITE, valign: "middle" });
    const pts = [
      ["Many datasets", "Imagery, roads, facilities, land cover, terrain must be combined"],
      ["Uncertain buildings", "Candidate buildings are model output, not a verified census"],
      ["Many alternatives", "Routes must be compared using terrain, land cover and constraints"],
      ["Shared segments", "Routes that share road should not be costed separately"],
    ];
    pts.forEach((p, i) => {
      const x = 0.5 + (i % 2) * 4.6, y = 2.45 + Math.floor(i / 2) * 1.35;
      card(s, x, y, 4.4, 1.2);
      txt(s, p[0], { x: x + 0.2, y: y + 0.12, w: 4.0, h: 0.35, fontSize: 16, bold: true, color: MID, fontFace: HF });
      txt(s, p[1], { x: x + 0.2, y: y + 0.52, w: 4.0, h: 0.6, fontSize: 14 });
    });
  }

  // ---------- 5 Objectives ----------
  {
    const s = content("Objectives and current status", "I have four objectives. The first two, data preparation and route generation, are done for Damarakunta. The third, shared network selection, has been executed and the numbers for the primary run are verified. The fourth, the effect of building omissions and method choices, is executed, but final consolidation and some checks are pending.");
    const rows = [
      ["Prepare and integrate GIS and remote-sensing data for Damarakunta", "Achieved", MID],
      ["Generate connections from target buildings and priority facilities to the road network", "Achieved (163 houses, 4 facilities routed)", MID],
      ["Select and compare a shared network using route costs and marginal network cost", "Executed; primary run verified", MID],
      ["Evaluate effect of building omissions and planner choices", "Executed; final checks pending", ACC],
    ];
    rows.forEach((r, i) => {
      const y = 1.2 + i * 1.0;
      card(s, 0.5, y, 9, 0.85);
      txt(s, "O" + (i + 1), { x: 0.65, y, w: 0.6, h: 0.85, fontSize: 20, bold: true, color: MID, fontFace: HF, valign: "middle" });
      txt(s, r[0], { x: 1.3, y, w: 5.3, h: 0.85, fontSize: 14, valign: "middle" });
      chip(s, r[1], 6.8, y + 0.28, 2.55, r[2]);
    });
  }

  // ---------- 6 Mini vs Major ----------
  {
    const s = content("Mini-project versus major project", "My mini-project explored image segmentation on the public LoveDA benchmark with a DINOv2 model. Those results belong only to the mini-project. LoveDA is not Damarakunta data. The major project takes the next step: it uses GIS data for one real village and plans roads, and studies how uncertain building data affect the plan.");
    const R = [
      [hc("Aspect"), hc("Mini-project"), hc("Major project")],
      [c("Purpose", { bold: true }), c("Explore remote-sensing image segmentation"), c("Rural infrastructure and road-network planning")],
      [c("Study data", { bold: true }), c("LoveDA benchmark (5,987 images)"), c("Damarakunta village GIS layers and imagery")],
      [c("Methods", { bold: true }), c("StrongDINOv2Seg: DINOv2-base, FPN + ASPP decoder, CE + Dice + Boundary loss"), c("GIS cost grid, least-cost routes, shared-network selection")],
      [c("Output", { bold: true }), c("Segmentation maps; best validation mIoU 53.80%, mDice 68.91% (epoch 4)"), c("Candidate routes, selected network, C1 and C2 results")],
      [c("Research focus", { bold: true }), c("Segmentation performance"), c("Effect of building-data uncertainty; shared-network planning")],
    ];
    table(s, R, 0.5, 1.1, 9, [1.4, 3.8, 3.8]);
    card(s, 0.5, 4.35, 9, 0.75, "FBF1DC");
    txt(s, "Mini-project numbers are LoveDA validation results only (10 epochs, no test set recorded). They are not Damarakunta results.", { x: 0.7, y: 4.4, w: 8.6, h: 0.65, fontSize: 14, valign: "middle", bold: true, color: "6B4A00" });
  }

  // ---------- 7-8 Literature ----------
  const litHdr = [hc("No."), hc("Author, year"), hc("Topic"), hc("Method"), hc("Main finding"), hc("Limitation or gap"), hc("Relevance")];
  const litW = [0.35, 1.0, 1.6, 1.45, 1.75, 1.6, 1.25];
  {
    const s = content("Literature survey (1 of 2): perception", "These papers cover building and road extraction from satellite images. They show good progress on footprints and on road continuity. But they mostly score the map, not what happens to a road plan when a building is missed. That is the gap I look at. Findings here are from abstracts and summaries, not a full reading.");
    table(s, [litHdr,
      [c("1"), c("Ding et al., 2022"), c("Adversarial Shape Learning for Building Extraction in VHR Remote Sensing Images"), c("Adversarial shape learning with a shape regularizer"), c("Improves building footprint geometry"), c("Does not test road-planning effects"), c("Quality of building targets")],
      [c("2"), c("Li et al., 2024"), c("A Review of Building Extraction From Remote Sensing Imagery"), c("Review (optical and SAR)"), c("Maps geometric and semantic challenges"), c("No best model for rural India"), c("Frames the building stage")],
      [c("3"), c("Hu et al., 2023"), c("LGNet: Location-Guided Network for Road Extraction From Satellite Images"), c("Road-location task plus guided decoder"), c("Improves road continuity"), c("Needs vector graph checks"), c("Road connectivity matters")],
      [c("4"), c("Xu et al., 2023"), c("Road Extraction With Satellite Images and Partial Road Maps"), c("Partial-to-Complete network"), c("Completes incomplete road maps"), c("No house connection; no rural India test"), c("Like our incomplete road layer")],
    ], 0.5, 1.1, 9, litW);
    txt(s, "Full citations on the References slide.", { x: 0.5, y: 4.95, w: 6, h: 0.25, fontSize: 10, color: MUTED });
  }
  {
    const s = content("Literature survey (2 of 2): planning and uncertainty", "These papers are about route planning, multi-criteria analysis and uncertainty. Path planning and multi-criteria GIS are mature tools, so I use them as they are and do not claim them as new. The papers do not connect uncertain building input to the final shared road network, which is the focus of my C1 and C2 experiments.");
    table(s, [litHdr,
      [c("5"), c("Zhu et al., 2025"), c("A Multi-Objective Path Planning Framework in Off-Road Environments Based on Deep Reinforcement Learning"), c("Actor-critic DRL on a traversability map"), c("Terrain-aware multi-objective path cost"), c("Single vehicle path, not a network"), c("Terrain-aware cost idea")],
      [c("6"), c("Wang et al., 2024"), c("A Practical Urban Distribution Network Planning Method With Geographic Information System"), c("GIS street graph, shortest paths, optimisation"), c("Path distances beat straight-line distances"), c("Urban power network, not rural roads"), c("Supports path-based network planning")],
      [c("7"), c("Malczewski, 2006"), c("GIS-based multicriteria decision analysis: a survey of the literature"), c("Literature survey"), c("Reviews multi-criteria methods in GIS"), c("General survey; no rural roads"), c("Basis for multi-criteria cost")],
      [c("8"), c("Yang et al., 2025"), c("UGD-DLinkNet: Enhanced Network for Occluded Road Extraction Using Attention and Uncertainty Estimation"), c("Attention, Monte Carlo dropout, distillation"), c("Uses uncertainty for occluded roads"), c("Not propagated into planning"), c("Motivates uncertainty study")],
    ], 0.5, 1.1, 9, litW);
  }
  // ---------- 9 Research gap ----------
  {
    const s = content("Research gap and project questions", "I am not claiming that A star, least-cost path, multi-criteria analysis or facility prioritisation are new. They are established tools. My questions are narrower. C1: how do missing buildings change the plan. C2: does selecting routes together with shared-edge credit reduce duplicated network length compared with independent routing. C3: transfer to other villages, which I have not tested yet.");
    const items = [
      ["C1", "Building-data uncertainty", "How can missing building targets affect road-planning decisions?", "Executed", MID],
      ["C2", "Shared-network planning", "Does generate-and-select with shared-edge credit reduce duplicated network cost compared with independent routing?", "Executed", MID],
      ["C3", "Transfer to other villages", "Future evaluation only. Not an established contribution.", "Pending", WARN],
    ];
    items.forEach((it, i) => {
      const y = 1.2 + i * 1.15;
      card(s, 0.5, y, 9, 1.0);
      txt(s, it[0], { x: 0.65, y, w: 0.8, h: 1.0, fontSize: 26, bold: true, color: it[4], fontFace: HF, valign: "middle" });
      txt(s, it[1], { x: 1.5, y: y + 0.1, w: 5.6, h: 0.35, fontSize: 16, bold: true, color: DARK });
      txt(s, it[2], { x: 1.5, y: y + 0.47, w: 5.8, h: 0.5, fontSize: 14 });
      chip(s, it[3], 8.1, y + 0.35, 1.2, it[4]);
    });
    txt(s, "Not claimed as new: A*, least-cost path, AHP/multi-criteria analysis, DINOv2, FPN, ASPP, facility prioritisation.", { x: 0.5, y: 4.75, w: 9, h: 0.4, fontSize: 12, color: MUTED });
  }

  // ---------- 10 Study area ----------
  {
    const s = content("Study area: Damarakunta village", "The study area is Damarakunta, in Markook Mandal, Siddipet District, Telangana. The boundary layer in my project covers about 18.466 square kilometres. The map shows the boundary, the satellite imagery, existing roads and model-detected building areas. A state-level location map is not yet in my project files, so I have not drawn one.");
    await pic(s, "map_study_area.jpg", 0.5, 1.05, 5.6, 4.1, "Study area overview map");
    card(s, 6.3, 1.1, 3.2, 3.95);
    txt(s, "Location", { x: 6.5, y: 1.2, w: 2.8, h: 0.3, fontSize: 16, bold: true, color: MID, fontFace: HF });
    bullets(s, ["Telangana, India", "Siddipet District", "Markook Mandal", "Damarakunta village"], { x: 6.5, y: 1.55, w: 2.8, h: 1.5, fontSize: 14 });
    txt(s, "18.466 km²", { x: 6.5, y: 3.15, w: 2.8, h: 0.5, fontSize: 28, bold: true, color: DARK, fontFace: HF });
    txt(s, "current project boundary layer (EPSG:32644)", { x: 6.5, y: 3.65, w: 2.8, h: 0.5, fontSize: 12, color: MUTED });
    txt(s, "State and district context map: not in project files yet. Imagery source and licence: to be confirmed.", { x: 6.5, y: 4.2, w: 2.8, h: 0.8, fontSize: 11, color: WARN });
  }

  // ---------- 11-12 Dataset inventory ----------
  const dsHdr = [hc("Dataset"), hc("Source"), hc("Local file"), hc("Resolution / count"), hc("Purpose"), hc("Limitation / status")];
  const dsW = [1.25, 1.35, 2.0, 1.4, 1.4, 1.6];
  {
    const s = content("Dataset inventory (1 of 2)", "These are the main input layers. For each one I list the file, the size, and what is still unverified. The satellite mosaic is the most important open point: its provider details and licence still need confirming. The boundary matches the stored TGRAC response, but that does not prove legal authority. The building candidates are model detections, not a census.");
    table(s, [dsHdr,
      [c("A. Satellite mosaic", { bold: true }), c("Esri imagery export (provenance to confirm)"), c("aligned/damarakunta_esri_highres_mosaic_0p6m.tif"), c("11,296 × 7,171 px, RGB, 0.6 m"), c("Visual review, building and road context"), c("Date and licence: to be confirmed")],
      [c("B. Village boundary", { bold: true }), c("TGRAC boundary service"), c("study_area/damarakunta_boundary.gpkg"), c("EPSG:32644, 18.466 km²"), c("Study area, clipping"), c("Equals stored TGRAC response; legal status not established")],
      [c("C. Road network", { bold: true }), c("TGRAC"), c("reference/tgrac_road_network.gpkg"), c("43 features, 93.5 km"), c("Existing-road goals"), c("44.7% of length outside boundary; completeness unverified")],
      [c("D. Building candidates", { bold: true }), c("Project model output"), c("results/v8_instances/buildings_v8_full.gpkg"), c("278 candidates; 165 footprints; 163 routed"), c("Target buildings"), c("Not a verified census of houses")],
      [c("E. Land cover", { bold: true }), c("ESA WorldCover"), c("aligned/damarakunta_worldcover_10m.tif"), c("10 m, 679 × 432 cells"), c("Land-cover route cost"), c("2021 per project notes; version to confirm")],
    ], 0.5, 1.1, 9, dsW);
    txt(s, "esa-worldcover.org/en/data-access", { x: 0.5, y: 4.95, w: 6, h: 0.25, fontSize: 10, color: MUTED });
  }
  {
    const s = content("Dataset inventory (2 of 2)", "The rest are the elevation data, derived layers, parcels, facilities and the LoveDA benchmark. The slope comes from a roughly 30 metre DEM resampled to 10 metres, so it does not carry true 10 metre detail. Cost values are model units, not rupees. LoveDA is used only in the mini-project and is not Damarakunta data. Parcel counts do not show ownership or legal access.");
    table(s, [dsHdr,
      [c("F. DEM", { bold: true }), c("Copernicus DEM per project plan; project notes also list SRTM"), c("raw/dem/damarakunta_dem_clip.tif"), c("~30 m"), c("Slope for route cost"), c("Exact product: to be confirmed; not true 10 m detail")],
      [c("G. Slope, cost, prohibited mask", { bold: true }), c("Derived by project scripts"), c("aligned/…slope_10m, …cost_surface_10m, …prohibited_mask_10m.tif"), c("10 m, 679 × 432"), c("Terrain difficulty, cost, excluded cells"), c("Model units, not rupees")],
      [c("H. Cadastral parcels", { bold: true }), c("Project parcel layer"), c("reference/damarakunta_cadastral_valid.gpkg"), c("794 parcels"), c("Parcel-crossing counts"), c("No ownership or legal-access claim")],
      [c("I. Facilities", { bold: true }), c("TGRAC facility and school records"), c("reference/damarakunta_priority_facilities.gpkg; school_compounds*.gpkg"), c("4 priority facilities"), c("Service destinations"), c("Completeness and identity unverified")],
      [c("J. LoveDA (mini-project only)", { bold: true }), c("Wang et al.; doi:10.5281/zenodo.5706578"), c("Not in the Damarakunta folders"), c("5,987 images (as reported)"), c("Mini-project segmentation"), c("Not Damarakunta data")],
    ], 0.5, 1.1, 9, dsW);
    txt(s, "DEM: dataspace.copernicus.eu (COP-DEM collection).", { x: 0.5, y: 4.95, w: 6, h: 0.25, fontSize: 10, color: MUTED });
  }

  // ---------- 13 Data preparation ----------
  {
    const s = content("Data preparation and GIS integration", "Before any routing, the data must be made consistent. I check the data and metadata, put every layer in the same coordinate system, clip to the village boundary, prepare targets, roads, facilities, land cover and slope, and then build a 10 metre cost grid with excluded cells. The result is only as good as the input data.");
    const steps = ["Collect input data", "Check quality and metadata", "Align coordinate systems", "Clip to boundary", "Prepare targets, roads, facilities, land cover, slope", "Build cost grid and prohibited mask", "Analysis-ready GIS inputs"];
    const w = 1.18, gap = 0.13;
    steps.forEach((t, i) => {
      const x = 0.5 + i * (w + gap);
      s.addShape(pres.shapes.RECTANGLE, { x, y: 1.2, w, h: 1.45, fill: { color: i === 6 ? MID : LIGHT }, line: { color: RULE, width: 0.75 } });
      s.addText(String(i + 1), { x, y: 1.25, w, h: 0.3, align: "center", fontSize: 14, bold: true, color: i === 6 ? WHITE : MID, fontFace: BF, margin: 0, isTextBox: true });
      s.addText(t, { x: x + 0.05, y: 1.55, w: w - 0.1, h: 1.05, align: "center", valign: "middle", fontSize: 11, color: i === 6 ? WHITE : TXT, fontFace: BF, margin: 0, isTextBox: true });
      if (i < 6) s.addText("›", { x: x + w - 0.02, y: 1.7, w: gap + 0.04, h: 0.4, align: "center", fontSize: 16, bold: true, color: MID, margin: 0, isTextBox: true });
    });
    await pic(s, "fig_slope_cost.png", 0.5, 2.85, 5.6, 2.3, "Slope and cost surface derived from project rasters");
    card(s, 6.3, 2.9, 3.2, 2.2);
    bullets(s, ["Grid: 432 × 679 cells, 10 m, EPSG:32644", "Cost = land cover + slope term", "Cells blocked: water, prohibited, slope above 25°", "Output quality depends on input quality"], { x: 6.45, y: 3.0, w: 2.95, h: 2.0, fontSize: 12 });
  }

  // ---------- 14 Architecture ----------
  {
    const s = content("Proposed system architecture", "The system is a GIS and graph-routing pipeline, not a deep-learning model. Inputs are cleaned and aligned, targets are prepared, a cost surface is built, and a routing graph is made from the grid. Stage A generates candidate routes. Stage B selects them into one shared network. At the end we evaluate connectivity, length and cost, and run the C1 and C2 experiments.");
    const mods = [
      ["1 Input data", "Imagery, boundary, roads, buildings, facilities, land cover, DEM, parcels"],
      ["2 Preprocessing", "CRS alignment, clipping, raster and vector preparation, quality checks"],
      ["3 Target preparation", "Filter buildings, define facilities and road connection points"],
      ["4 Cost surface", "Land-cover and slope cost, prohibited mask, movement-cost grid"],
      ["5 Road graph", "Passable grid cells, movement rules, no routing through blocked cells"],
      ["6 Stage A", "Generate alternative candidate routes per target"],
      ["7 Stage B", "Select routes by marginal cost with shared-edge credit"],
      ["8 Evaluation", "Connectivity, length, cost; C1 omission and C2 ablation; maps"],
    ];
    const w = 2.1, h = 1.45;
    mods.forEach((m, i) => {
      const row = Math.floor(i / 4), col = i % 4;
      const x = 0.5 + col * (w + 0.2), y = 1.15 + row * (h + 0.55);
      const hl = i === 5 || i === 6;
      s.addShape(pres.shapes.RECTANGLE, { x, y, w, h, fill: { color: hl ? MID : LIGHT }, line: { color: hl ? MID : RULE, width: 0.75 } });
      s.addText(m[0], { x: x + 0.1, y: y + 0.08, w: w - 0.2, h: 0.3, fontSize: 14, bold: true, color: hl ? WHITE : DARK, fontFace: HF, margin: 0, isTextBox: true });
      s.addText(m[1], { x: x + 0.1, y: y + 0.42, w: w - 0.2, h: h - 0.5, fontSize: 11, color: hl ? WHITE : TXT, fontFace: BF, margin: 0, valign: "top", isTextBox: true });
      if (col < 3) s.addShape(pres.shapes.RIGHT_ARROW, { x: x + w + 0.02, y: y + h / 2 - 0.1, w: 0.16, h: 0.2, fill: { color: MUTED }, line: { color: MUTED } });
    });
    s.addText("Row 1 continues into row 2", { x: 0.5, y: 3.0, w: 9, h: 0.3, align: "right", fontSize: 10, italic: true, color: MUTED, margin: 0, isTextBox: true });
    txt(s, "Planner: graph and least-cost-path heuristic on an 8-connected 10 m grid. Not globally optimal.", { x: 0.5, y: 4.85, w: 9, h: 0.3, fontSize: 12, color: MUTED });
  }

  // ---------- 15 Execution flow ----------
  {
    const s = content("Step-by-step execution flow", "This is the order in which the work runs, from loading the data to the final report. Each step has an input and an output. Steps one to ten have been run for Damarakunta. Steps eleven and twelve are partly done, because final consolidation and the connectivity checks are still pending.");
    const st = [
      ["Load project data", "files to layers"], ["Check CRS and quality", "validated inputs"], ["Prepare targets", "163 houses, 4 facilities"],
      ["Prepare land cover, slope, mask", "10 m rasters"], ["Generate cost surface", "cost grid"], ["Build routing graph", "grid graph"],
      ["Generate candidate routes", "K = 3 per target"], ["Select shared network", "selected routes"], ["Evaluate feasibility and cost", "length, connectivity"],
      ["Run C1 and C2", "result tables"], ["Export maps and tables", "GIS layers, figures"], ["Final checks and report", "pending"],
    ];
    st.forEach((t, i) => {
      const col = i % 4, row = Math.floor(i / 4);
      const x = 0.5 + col * 2.28, y = 1.15 + row * 1.35;
      const pend = i === 11;
      s.addShape(pres.shapes.RECTANGLE, { x, y, w: 2.1, h: 1.15, fill: { color: pend ? "FBF1DC" : LIGHT }, line: { color: RULE, width: 0.75 } });
      s.addShape(pres.shapes.OVAL, { x: x + 0.08, y: y + 0.08, w: 0.36, h: 0.36, fill: { color: pend ? ACC : MID }, line: { color: pend ? ACC : MID } });
      s.addText(String(i + 1), { x: x + 0.08, y: y + 0.08, w: 0.36, h: 0.36, align: "center", valign: "middle", fontSize: 12, bold: true, color: WHITE, margin: 0, isTextBox: true });
      s.addText(t[0], { x: x + 0.5, y: y + 0.05, w: 1.55, h: 0.55, fontSize: 12, bold: true, color: DARK, valign: "middle", margin: 0, fontFace: BF, isTextBox: true });
      s.addText("Output: " + t[1], { x: x + 0.12, y: y + 0.68, w: 1.9, h: 0.4, fontSize: 11, color: MUTED, margin: 0, valign: "top", fontFace: BF, isTextBox: true });
    });
  }

  // ---------- 16 Tools ----------
  {
    const s = content("Implementation and tools", "Everything runs in Python in a project virtual environment. The versions shown come from the installed packages in that environment. Data are stored as GeoPackage and GeoTIFF. The planner is one Python script, and I recorded its file hash in every run so that I know the planner was not changed between runs.");
    const L = [["Language", "Python 3.10"], ["Raster and vector", "rasterio 1.4.4, geopandas 1.1.4, shapely 2.1.2, pyogrio 0.13.0, pyproj 3.7.1, fiona 1.10.1"], ["Numerics and graphs", "numpy 2.2.6, scipy 1.15.3, networkx 3.4.2, pandas 2.3.3"], ["Imaging and plots", "scikit-image 0.25.2, OpenCV-python 5.0.0.93, matplotlib 3.10.9"], ["Data formats", "GeoPackage (.gpkg), GeoTIFF (.tif), CSV, JSON"], ["Planner", "plan_network_v2.py (heap-based search, SHA-256 d00ea920…ef70a4)"]];
    L.forEach((r, i) => {
      const y = 1.15 + i * 0.66;
      card(s, 0.5, y, 9, 0.56);
      txt(s, r[0], { x: 0.7, y, w: 2.3, h: 0.56, fontSize: 14, bold: true, color: MID, valign: "middle" });
      txt(s, r[1], { x: 3.0, y, w: 6.3, h: 0.56, fontSize: 13, valign: "middle" });
    });
  }

  // ---------- 17 Outputs ----------
  {
    const s = content("Actual project outputs", "These are real exports from my project folders. Top left: building areas and existing roads in the main settlement. Top right: proposed network on the village map. Bottom left: connectivity audit, where cyan marks route geometry and white dots are road endpoints. Bottom right: slope and cost surface. Context imagery in some maps is coarse, and imagery licence is still being confirmed.");
    const cells = [
      ["map_buildings_roads.jpg", "Building candidates and existing roads"],
      ["map_proposed_network.jpg", "Planner output (model result, not verified roads)"],
      ["map_connectivity_audit.jpg", "Connectivity audit: endpoints and bridge candidates"],
      ["fig_slope_cost.png", "Slope and cost surface (rendered from project rasters)"],
    ];
    for (let i = 0; i < 4; i++) {
      const x = 0.5 + (i % 2) * 4.6, y = 1.1 + Math.floor(i / 2) * 2.05;
      await pic(s, cells[i][0], x, y, 4.4, 1.7, cells[i][1]);
      txt(s, cells[i][1], { x, y: y + 1.73, w: 4.4, h: 0.25, fontSize: 10, color: MUTED });
    }
  }

  // ---------- 18 C1 ----------
  {
    const s = content("C1: Building-data uncertainty", "The question is: what happens to the road plan if some buildings are missing from the input? I removed buildings in controlled steps and re-ran the planner. The baseline routes 163 houses with 5,138 metres of unique network. Removing the smallest 25 percent leaves 122 houses and 3,891 metres. The network shrinks because fewer houses are served. So the comparable number is length per served house, which stays near 32 metres, and goes up to about 36 metres when merged buildings are removed. These omissions are synthetic tests. They do not measure real building-detection error.");
    s.addChart(pres.charts.BAR, [{ name: "Unique network length (m)", labels: ["Baseline (163)", "Omit 10% smallest (146)", "Omit 25% smallest (122)", "Omit merged (101)"], values: [5137.7, 4717.5, 3890.6, 3627.9] }], {
      x: 0.5, y: 1.1, w: 5.2, h: 3.5, barDir: "col", chartColors: [MID], showTitle: true, title: "Unique network length (m); targets routed in brackets", titleFontSize: 11, titleColor: TXT,
      showValue: true, dataLabelPosition: "outEnd", dataLabelFontSize: 10, dataLabelColor: TXT, dataLabelFormatCode: "#,##0", showLegend: false,
      catAxisLabelFontSize: 9, valAxisLabelFontSize: 9, catAxisLabelColor: MUTED, valAxisLabelColor: MUTED, valGridLine: { color: RULE, size: 0.5 }, catGridLine: { style: "none" }, valAxisMinVal: 0,
      showValAxisTitle: true, valAxisTitle: "metres", valAxisTitleFontSize: 9, valAxisTitleColor: MUTED, catAxisLabelFontFace: BF, valAxisLabelFontFace: BF,
    });
    txt(s, "Config: S2, K=3, 2 passes, slope limit 25°, building penalty ×4. Source: c1_scenario_comparison.csv", { x: 0.5, y: 4.65, w: 5.2, h: 0.45, fontSize: 10, color: MUTED });
    bullets(s, ["Question: how does omitting targets change the plan?", "Fewer targets means a shorter network, no failed routes", "Length per served house: 31.5 m baseline, 31.9 / 32.3 / 35.9 m for omissions", "Synthetic omissions, not measured detection error"], { x: 5.9, y: 1.2, w: 3.6, h: 3.8, fontSize: 13 });
  }

  // ---------- 19 C2 ----------
  {
    const s = content("C2: Shared-network planning", "Independent routing plans each house separately and counts each road each time. Shared-network planning gives credit when a new route can use road that is already selected. The measure is marginal unique network cost, the extra network a new route needs. On the same 163 houses, the independent routes need 6,755 metres of unique network, the shared plan needs 5,138 metres, a reduction of about 24 percent. This is a heuristic and is not claimed to be globally optimal. These lengths are model grid lengths, not construction costs.");
    s.addChart(pres.charts.BAR, [{ name: "Unique network length (m)", labels: ["Independent least-cost routes", "Shared-network plan (K=3, 2 passes)"], values: [6755.4, 5137.7] }], {
      x: 0.5, y: 1.1, w: 4.0, h: 3.4, barDir: "col", chartColors: [BLUE, MID], showTitle: true, title: "Unique network length, 163 houses (m)", titleFontSize: 11, titleColor: TXT,
      showValue: true, dataLabelPosition: "outEnd", dataLabelFontSize: 10, dataLabelColor: TXT, dataLabelFormatCode: "#,##0.0", showLegend: false, valAxisMinVal: 0,
      catAxisLabelFontSize: 9, valAxisLabelFontSize: 9, catAxisLabelColor: MUTED, valAxisLabelColor: MUTED, valGridLine: { color: RULE, size: 0.5 }, catGridLine: { style: "none" },
      showValAxisTitle: true, valAxisTitle: "metres", valAxisTitleFontSize: 9, valAxisTitleColor: MUTED, catAxisLabelFontFace: BF, valAxisLabelFontFace: BF,
    });
    txt(s, "Config: S2, slope 25°, cost C0. Source: evaluation_summary.json", { x: 0.5, y: 4.55, w: 4.0, h: 0.4, fontSize: 10, color: MUTED });
    await pic(s, "map_independent_vs_network_inset.jpg", 4.7, 1.1, 4.8, 2.6, "Independent versus shared-network routes, inset A");
    bullets(s, ["Reduction 1,617.7 m (23.9%), heuristic, 0 failed routes", "Ablation: K1/P0 5,148.0 m vs K3/P2 5,137.7 m (0.2% gap)", "Connectivity: 162 of 163 houses reach main road component"], { x: 4.7, y: 3.8, w: 4.8, h: 1.4, fontSize: 12 });
  }

  // ---------- 20 Results table ----------
  {
    const s = content("Actual numerical results", "Every number here was read from the saved output files. The status column is honest. Primary-run C1 and C2 numbers are verified from the CSV and JSON files. The no-building-penalty P3 row is provisional because the P3 baseline reproduction run is still pending. The 5,231.5 metre figure is the roads-only reference baseline, not the main planner, and it gives 22.6 percent. The main planner gives 23.9 percent.");
    const V = { text: "Verified", options: { fontSize: 10, bold: true, color: MID, fontFace: BF } };
    const P = { text: "Provisional", options: { fontSize: 10, bold: true, color: "8A6100", fontFace: BF } };
    table(s, [
      [hc("Experiment"), hc("Configuration"), hc("Baseline"), hc("Method"), hc("Change"), hc("N"), hc("Source file"), hc("Status")],
      [c("C2 shared vs independent"), c("S2, K3 P2, slope 25°, C0"), c("6,755.4 m"), c("5,137.7 m"), c("−1,617.7 m (−23.9%)"), c("163"), c("evaluation_summary.json"), V],
      [c("C2 vs roads-only reference"), c("same run; reference baseline"), c("6,755.4 m"), c("5,231.5 m"), c("−1,523.8 m (−22.6%)"), c("163"), c("evaluation_summary.json"), V],
      [c("C2 ablation K1 P0 vs K3 P2"), c("5 runs, same inputs"), c("5,148.0 m"), c("5,137.7 m"), c("−10.3 m (−0.2%)"), c("163"), c("c2_ablation_summary.csv"), V],
      [c("C1 omit 25% smallest"), c("primary, building penalty ×4"), c("5,137.7 m"), c("3,890.6 m"), c("−24.3%; 122 routed"), c("163 → 122"), c("c1_scenario_comparison.csv"), V],
      [c("C1 omit merged candidates"), c("primary, building penalty ×4"), c("5,137.7 m"), c("3,627.9 m"), c("−29.4%; 101 routed"), c("163 → 101"), c("c1_scenario_comparison.csv"), V],
      [c("C1 omit merged candidates"), c("P3, no building penalty"), c("4,761.7 m"), c("3,425.7 m"), c("−28.1%; 101 routed"), c("163 → 101"), c("P3 comparison csv"), P],
    ], 0.5, 1.1, 9, [1.6, 1.5, 0.85, 0.85, 1.25, 0.7, 1.55, 0.7]);
    txt(s, "Lengths are unique network length in metres on the 10 m grid. Costs are model units, not rupees. Earlier prototype runs (e.g. 1,506.1 m, 9 clusters) are superseded and not shown as results.", { x: 0.5, y: 4.55, w: 9, h: 0.6, fontSize: 11, color: MUTED });
  }

  // ---------- 21 Status ----------
  {
    const s = content("Current project status", "This table is the honest status. The core planner experiments are executed. The boundary check passed for the stored boundary. The connectivity investigation is ongoing: one house, C0002, attaches to a small road component that is separate from the main road cells, and I need to check if the road leaves and re-enters the boundary. Transfer to other villages is not established.");
    const OK = (t) => c(t, { bold: true, color: MID }), WIP = (t) => c(t, { bold: true, color: "8A6100" }), NO = (t) => c(t, { bold: true, color: WARN });
    table(s, [
      [hc("Component"), hc("Status"), hc("Evidence"), hc("Next action")],
      [c("Core GIS and route planning"), OK("Executed"), c("163/163 houses and 4/4 facilities routed, 0 failed"), c("Final result consolidation")],
      [c("C1 omission experiments"), OK("Executed, primary verified"), c("c1_scenario_comparison.csv; 49 report checks pass"), c("P3 baseline reproduction")],
      [c("C2 shared-network ablation"), OK("Executed, verified"), c("c2_ablation_summary.csv; control identical"), c("Optional geometry comparison")],
      [c("Boundary comparison"), OK("Passed"), c("Saved copy equals stored TGRAC response"), c("Record query date")],
      [c("Connectivity investigation"), WIP("Ongoing"), c("12 road components; house C0002 attaches to a 5-cell component"), c("Check boundary exit and re-entry")],
      [c("Connector visual review"), WIP("Pending"), c("Route connectors need visual review"), c("Complete review")],
      [c("C3 transfer to other villages"), NO("Not established"), c("No second village run"), c("Needs approval and data")],
      [c("Report, maps, citation audit"), WIP("Pending"), c("Maps partly final"), c("Finish audit")],
    ], 0.5, 1.1, 9, [2.1, 1.6, 3.2, 2.1]);
  }

  // ---------- 22 Limitations ----------
  {
    const s = content("Limitations and future work", "These are the things I know are not finished or are not supported by evidence. The imagery licence, the completeness of roads and facilities, and the disconnected road component need checking. Final numbers need confirmation. Nothing here has been checked in the field, so I do not claim the roads are ready to build.");
    const L = ["Confirm satellite mosaic source, date and licence", "Check road and facility completeness and currency", "Investigate disconnected road components", "Finish visual review of route connectors", "Confirm final C1 and C2 numbers and settings", "Finish report, literature and citation audit", "Second-village transfer (C3) only if data and time allow", "Field or expert validation before any real-world claim"];
    L.forEach((t, i) => {
      const x = 0.5 + (i % 2) * 4.6, y = 1.15 + Math.floor(i / 2) * 0.98;
      card(s, x, y, 4.4, 0.85);
      txt(s, String(i + 1), { x: x + 0.12, y, w: 0.4, h: 0.85, fontSize: 18, bold: true, color: ACC, valign: "middle", fontFace: HF });
      txt(s, t, { x: x + 0.55, y, w: 3.75, h: 0.85, fontSize: 13, valign: "middle" });
    });
  }

  // ---------- 23 Conclusion ----------
  {
    const s = content("Conclusion", "To conclude. I integrated imagery, boundary, roads, building candidates, land cover and terrain for Damarakunta. I implemented a graph-based planner that generates and selects shared routes. My C1 and C2 experiments investigate building uncertainty and shared networks. The primary-run numbers are verified. Connectivity, licence checks, validation and transfer are still to do. I do not claim the routes are ready to build or optimal.");
    const L = [["Data integrated", "Imagery, boundary, roads, buildings, land cover, slope on a 10 m grid"], ["System built", "GIS cost grid with generate-and-select route planner"], ["Experiments run", "C1 omissions, C2 shared-network ablation"], ["Confirmed", "Primary-run results: 163 houses, 5,137.7 m shared vs 6,755.4 m independent"], ["Still to do", "Connectivity checks, licence checks, validation, transfer (C3)"]];
    L.forEach((r, i) => {
      const y = 1.15 + i * 0.78;
      card(s, 0.5, y, 9, 0.68, i === 4 ? "FBF1DC" : LIGHT);
      txt(s, r[0], { x: 0.7, y, w: 2.2, h: 0.68, fontSize: 15, bold: true, color: i === 4 ? "8A6100" : MID, valign: "middle", fontFace: HF });
      txt(s, r[1], { x: 2.9, y, w: 6.4, h: 0.68, fontSize: 13, valign: "middle" });
    });
  }

  // ---------- 24 References ----------
  {
    const s = content("References", "These are the references I used on the slides. The IEEE items were checked against their DOI records in my literature verification file. Full-text reading is still pending for some. The dataset links are the official pages.");
    const refs = [
      "[1] L. Ding et al., \"Adversarial Shape Learning for Building Extraction in VHR Remote Sensing Images,\" IEEE Trans. Image Process., 2022, doi:10.1109/TIP.2021.3134455.",
      "[2] Q. Li et al., \"A Review of Building Extraction From Remote Sensing Imagery,\" IEEE Trans. Geosci. Remote Sens., 2024, doi:10.1109/TGRS.2024.3369723.",
      "[3] J. Hu et al., \"LGNet: Location-Guided Network for Road Extraction From Satellite Images,\" IEEE TGRS, 2023, doi:10.1109/TGRS.2023.3305031.",
      "[4] Q. Xu et al., \"Road Extraction With Satellite Images and Partial Road Maps,\" IEEE TGRS, 2023, doi:10.1109/TGRS.2023.3261332.",
      "[5] L. Zhu et al., \"A Multi-Objective Path Planning Framework in Off-Road Environments Based on Deep Reinforcement Learning,\" IEEE Trans. Intell. Transp. Syst., 2025, doi:10.1109/TITS.2025.3589586.",
      "[6] Z. Wang et al., \"A Practical Urban Distribution Network Planning Method With Geographic Information System,\" IEEE Trans. Power Syst., 2024, doi:10.1109/TPWRS.2024.3384534.",
      "[7] J. Malczewski, \"GIS-based multicriteria decision analysis: a survey of the literature,\" Int. J. Geogr. Inf. Sci., 2006, doi:10.1080/13658810600661508.",
      "[8] P. Yang et al., \"UGD-DLinkNet: An Enhanced Network for Occluded Road Extraction Using Attention Mechanisms and Uncertainty Estimation,\" IEEE JSTARS, 2025, doi:10.1109/JSTARS.2025.3608007.",
      "[9] J. Wang et al., \"LoveDA: A Remote Sensing Land-Cover Dataset for Domain Adaptive Semantic Segmentation,\" NeurIPS Datasets and Benchmarks, 2021, arXiv:2110.08733; data doi:10.5281/zenodo.5706578.",
      "[10] ESA WorldCover, esa-worldcover.org/en/data-access.   [11] Copernicus DEM, dataspace.copernicus.eu (COP-DEM).",
    ];
    txt(s, refs.map((t, i) => ({ text: t, options: { breakLine: i < refs.length - 1, paraSpaceAfter: 4 } })), { x: 0.5, y: 1.1, w: 9, h: 4.1, fontSize: 10 });
  }

  // ---------- 25 Thank you ----------
  {
    const s = pres.addSlide({ masterName: "DARK" });
    s.addNotes("Thank you. I am happy to take questions. If asked, remember: results are planning support only, the primary-run numbers are verified, and field validation and transfer to other villages are future work.");
    txt(s, "Thank you", { x: 0.5, y: 1.6, w: 9, h: 1.0, fontFace: HF, fontSize: 44, bold: true, color: WHITE, align: "center" });
    txt(s, "Questions and suggestions are welcome", { x: 0.5, y: 2.7, w: 9, h: 0.5, fontSize: 20, color: "DCE8E2", align: "center" });
    txt(s, "Pendyala Archana | M.Tech IT (AI and Robotics) | CBIT Hyderabad", { x: 0.5, y: 4.4, w: 9, h: 0.4, fontSize: 14, color: ACC, align: "center" });
  }

  await pres.writeFile({ fileName: OUT });
  console.log("written", OUT);
})();
