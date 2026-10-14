"""Evidence-based environmental context; not a life-cycle calculator."""

ENERGY_CONTEXT = {
    "primary_aluminium_gj_per_tonne": 186.0,
    "recycled_aluminium_gj_per_tonne": 8.3,
    "region": "Global primary / average of reported recycled datasets",
    "year": "2019 energy inventory and reported comparison",
    "source": "https://international-aluminium.org/landing/aluminium-recycling-saves-95-of-the-energy-needed-for-primary-aluminium-production/",
    "boundary_note": (
        "Production stages, sourcing, geography and underlying inventories differ; "
        "these illustrative published values are not a component-level LCA."
    ),
}

PATHWAYS = [
    {
        "material": "Aluminium alloys",
        "inspection_priority": "Separate pores from inclusions and preparation artifacts; assess by application.",
        "circular_design": "Track alloy identity, avoid contamination, and prioritise viable repair/reuse before scrap.",
        "caution": "Remelting energy depends on alloy, scrap quality and electricity mix.",
    },
    {
        "material": "Carbon and stainless steels",
        "inspection_priority": "Consider inclusions, etching artifacts and manufacturing route.",
        "circular_design": "Record grade, surface coatings and traceability for high-quality recovery.",
        "caution": "Steel environmental footprints depend on product, process route and allocation.",
    },
    {
        "material": "Titanium alloys",
        "inspection_priority": "Confirm indications by a qualified method where safety-critical.",
        "circular_design": "Keep clean segregation of alloys and turnings; evaluate approved repairs.",
        "caution": "Cross-material carbon comparisons need harmonised functional units.",
    },
    {
        "material": "Fibre-reinforced composites",
        "inspection_priority": "Optical images alone cannot locate all internal voids or delaminations.",
        "circular_design": "Design for service life and repair; document end-of-life route early.",
        "caution": "Recycling routes differ markedly from metals and can downcycle fibres.",
    },
]

SOURCES = [
    {
        "name": "ASTM E1245-03(2023) overview (scope and non-acceptance caveat)",
        "url": "https://store.astm.org/e1245-03r23.html",
    },
    {
        "name": "scikit-image: label image regions (algorithm context)",
        "url": "https://scikit-image.org/docs/stable/auto_examples/segmentation/plot_label.html",
    },
    {
        "name": "International Aluminium Institute: recycling energy data",
        "url": ENERGY_CONTEXT["source"],
    },
    {
        "name": "World Steel Association: life-cycle inventory methodology and datasets",
        "url": "https://worldsteel.org/wider-sustainability/life-cycle-thinking/life-cycle-inventory-data-and-eco-profiles/",
    },
]
