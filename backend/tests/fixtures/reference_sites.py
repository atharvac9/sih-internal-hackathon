"""
Calibration reference sites for watershed and surface-type scoring.
Coordinates verified on satellite imagery in Pune metropolitan / watershed region.
"""

REFERENCE_SITES = [
    {
        "id": "khadakwasla_reservoir",
        "name": "Khadakwasla Reservoir (open water)",
        "lat": 18.4400,
        "lon": 73.7700,
        "buffer_radius_m": 250,
        "expected_surface_type": "water",
        "expected_min_score": 65,
        "description": "Major perennial freshwater reservoir for Pune; permanent open water.",
    },
    {
        "id": "vetal_hill",
        "name": "Vetal Hill (Vetal Tekdi)",
        "lat": 18.5200,
        "lon": 73.8200,
        "buffer_radius_m": 250,
        "expected_surface_type": "land",
        "expected_min_score": 55,
        "description": "Urban forested hill with dense tree cover and grassland.",
    },
    {
        "id": "sinhagad_forest",
        "name": "Sinhagad Forest Ridge",
        "lat": 18.3667,
        "lon": 73.7558,
        "buffer_radius_m": 250,
        "expected_surface_type": "land",
        "expected_min_score": 60,
        "description": "Protected mountain ridge in the Western Ghats with dense forest cover.",
    },
    {
        "id": "kharadi_it_park",
        "name": "Kharadi IT Park Core",
        "lat": 18.5500,
        "lon": 73.9400,
        "buffer_radius_m": 250,
        "expected_surface_type": "urban",
        "expected_max_score": 50,
        "description": "High-density commercial IT park with concrete, asphalt, and low green cover.",
    },
    {
        "id": "shivajinagar_core",
        "name": "Shivajinagar Dense Urban Core",
        "lat": 18.5300,
        "lon": 73.8500,
        "buffer_radius_m": 250,
        "expected_surface_type": "urban",
        "expected_max_score": 40,
        "description": "Historic dense downtown core with paved surfaces and negligible vegetation.",
    },
    {
        "id": "wagholi_stone_quarry",
        "name": "Wagholi / Marunji Barren Stone Quarry",
        "lat": 18.5850,
        "lon": 73.7350,
        "buffer_radius_m": 250,
        "expected_surface_type": "land",
        "expected_max_score": 40,
        "description": "Excavated open-cast basalt quarry and exposed barren bedrock.",
    },
]
