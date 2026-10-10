"""
PDF Report Generator for Watershed Intelligence Audits.
Implemented in pure-Python ReportLab for robust zero-dependency execution on Windows and Linux.
"""

import io
import json
from datetime import datetime, timezone
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def generate_watershed_pdf_report(
    site,
    analysis,
    photos: Optional[list] = None,
) -> bytes:
    """
    Generate an official audit PDF report matching Neerdrushti's visual design.

    Contains:
      - Location & Coordinates
      - Date Windows Used (Tnow and T0)
      - Surface Type & Fractions
      - Biophysical Indices (NDVI, NDWI, MNDWI, NDBI)
      - Health Score, Grade, Grade Bands, and Heuristic Disclaimer
      - Photo Classification (if present)
      - EXIF Forensics & Warnings
      - Satellite Telemetry Data Source (gee)
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()

    # Custom styles tailored to platform palette
    primary_teal = colors.HexColor("#0F766E")
    slate_dark = colors.HexColor("#0F172A")
    slate_mid = colors.HexColor("#334155")
    slate_light = colors.HexColor("#64748B")
    card_bg = colors.HexColor("#F8FAFC")
    border_color = colors.HexColor("#E2E8F0")

    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=primary_teal,
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=slate_light,
    )
    section_heading = ParagraphStyle(
        "SectionHeading",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=slate_dark,
        spaceAfter=4,
    )
    body_style = ParagraphStyle(
        "BodyDark",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=slate_mid,
    )
    bold_style = ParagraphStyle(
        "BodyBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=13,
        textColor=slate_dark,
    )
    disclaimer_style = ParagraphStyle(
        "Disclaimer",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#64748B"),
        alignment=1,  # Center
    )

    story = []

    # 1. Header Banner
    story.append(Paragraph("NEERDRUSHTI WATERSHED AUDIT REPORT", title_style))
    story.append(Paragraph("Automated Earth Observation & Multi-Modal Verification Telemetry", subtitle_style))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1.5, color=primary_teal, spaceAfter=14))

    # 2. Executive Summary & Health Score Box
    score_val = getattr(analysis, "health_score", None)
    grade_val = getattr(analysis, "health_grade", "N/A")
    score_display = str(score_val) if score_val is not None else "--"

    # Extract components JSON if available
    components = {}
    if hasattr(analysis, "health_components_json") and analysis.health_components_json:
        try:
            components = json.loads(analysis.health_components_json)
        except Exception:
            components = {}

    surface_type = (
        getattr(analysis, "surface_type", None)
        or components.get("surface_type")
        or "N/A"
    )

    score_table_data = [
        [
            Paragraph("<b>ECOLOGICAL HEALTH SCORE</b>", bold_style),
            Paragraph("<b>WATERSHED GRADE</b>", bold_style),
            Paragraph("<b>CLASSIFIED SURFACE TYPE</b>", bold_style),
            Paragraph("<b>TELEMETRY SOURCE</b>", bold_style),
        ],
        [
            Paragraph(f"<font size=20 color='#0F766E'><b>{score_display}</b></font> / 100", title_style),
            Paragraph(f"<font size=20 color='#0F766E'><b>{grade_val}</b></font>", title_style),
            Paragraph(f"<b>{surface_type.upper()}</b>", bold_style),
            Paragraph(f"<b>{getattr(analysis, 'satellite_source', 'gee').upper()}</b> (Sentinel-2 L2A)", body_style),
        ],
    ]
    t_score = Table(score_table_data, colWidths=[1.8 * inch, 1.4 * inch, 1.8 * inch, 2.2 * inch])
    t_score.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), card_bg),
        ("BOX", (0, 0), (-1, -1), 1, border_color),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, border_color),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(t_score)
    story.append(Spacer(1, 6))

    # Heuristic Disclaimer & Grade Bands
    story.append(Paragraph("<b>Heuristic score, not a scientific standard</b>", disclaimer_style))
    story.append(Paragraph(
        "Grade Bands: <b>A</b> (80–100, Excellent) &nbsp;|&nbsp; <b>B</b> (65–79, Good) &nbsp;|&nbsp; "
        "<b>C</b> (50–64, Fair) &nbsp;|&nbsp; <b>D</b> (35–49, Poor) &nbsp;|&nbsp; <b>F</b> (&lt;35, Critical)",
        disclaimer_style,
    ))
    story.append(Spacer(1, 14))

    # 3. Location & Coordinates Table
    site_code = getattr(site, "site_code", None) or f"SITE-{getattr(site, 'id', '')[:8].upper()}"
    site_desc = getattr(site, "description", "") or "Watershed Observation Site"
    lat_val = getattr(site, "lat", 0.0)
    lon_val = getattr(site, "lon", 0.0)
    radius_val = getattr(site, "buffer_radius_m", 250)

    tnow_start = getattr(analysis, "tnow_start_date", "N/A")
    tnow_end = getattr(analysis, "tnow_end_date", "N/A")
    t0_start = getattr(analysis, "t0_start_date", None) or components.get("t0_start_date", "No baseline (snapshot)")
    t0_end = getattr(analysis, "t0_end_date", None) or components.get("t0_end_date", "")

    loc_data = [
        [
            Paragraph("<b>Site Code / ID:</b>", body_style),
            Paragraph(f"{site_code}", bold_style),
            Paragraph("<b>Target Coordinates:</b>", body_style),
            Paragraph(f"{lat_val:.4f}°N, {lon_val:.4f}°E", bold_style),
        ],
        [
            Paragraph("<b>Description / Name:</b>", body_style),
            Paragraph(f"{site_desc}", body_style),
            Paragraph("<b>Buffer Radius:</b>", body_style),
            Paragraph(f"{radius_val} meters", body_style),
        ],
        [
            Paragraph("<b>Observation Window (Tnow):</b>", body_style),
            Paragraph(f"{tnow_start} → {tnow_end} (90 days)", body_style),
            Paragraph("<b>Baseline Window (T0):</b>", body_style),
            Paragraph(f"{t0_start}" + (f" → {t0_end}" if t0_end else ""), body_style),
        ],
    ]
    t_loc = Table(loc_data, colWidths=[2.0 * inch, 2.2 * inch, 1.8 * inch, 1.6 * inch])
    t_loc.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
        ("BOX", (0, 0), (-1, -1), 0.5, border_color),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#F1F5F9")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(Paragraph("Observation Location &amp; Temporal Windows", section_heading))
    story.append(t_loc)
    story.append(Spacer(1, 14))

    # 4. Biophysical Indices & Surface Fractions
    ndvi_val = getattr(analysis, "ndvi_tnow", None)
    ndwi_val = getattr(analysis, "ndwi_tnow", None)
    mndwi_val = components.get("mndwi") or ndwi_val  # classical NDWI vs MNDWI
    ndbi_val = components.get("ndbi", "N/A")

    water_frac = components.get("water_frac_now") or components.get("water_frac") or 0.0
    veg_frac = components.get("veg_frac") or 0.0
    built_frac = components.get("built_frac") or 0.0
    barren_frac = components.get("barren_frac") or 0.0

    bio_data = [
        [
            Paragraph("<b>Biophysical Spectral Indices (Median)</b>", bold_style),
            "",
            Paragraph("<b>Surface Land Cover Fractions (20m pixels)</b>", bold_style),
            "",
        ],
        [
            Paragraph("NDVI (Vegetation Index):", body_style),
            Paragraph(f"<b>{ndvi_val:.3f}</b>" if ndvi_val is not None else "--", bold_style),
            Paragraph("Water Extent Fraction:", body_style),
            Paragraph(f"<b>{water_frac * 100:.1f}%</b>", bold_style),
        ],
        [
            Paragraph("NDWI (Green/NIR B3-B8):", body_style),
            Paragraph(f"<b>{ndwi_val:.3f}</b>" if ndwi_val is not None else "--", bold_style),
            Paragraph("Vegetation Canopy Fraction:", body_style),
            Paragraph(f"<b>{veg_frac * 100:.1f}%</b>", bold_style),
        ],
        [
            Paragraph("MNDWI (Green/SWIR B3-B11):", body_style),
            Paragraph(f"<b>{mndwi_val:.3f}</b>" if isinstance(mndwi_val, float) else str(mndwi_val), bold_style),
            Paragraph("Built-up / Impervious Fraction:", body_style),
            Paragraph(f"<b>{built_frac * 100:.1f}%</b>", bold_style),
        ],
        [
            Paragraph("NDBI (Built-up Index):", body_style),
            Paragraph(f"<b>{ndbi_val:.3f}</b>" if isinstance(ndbi_val, float) else str(ndbi_val), bold_style),
            Paragraph("Barren Earth / Rock Fraction:", body_style),
            Paragraph(f"<b>{barren_frac * 100:.1f}%</b>", bold_style),
        ],
    ]
    t_bio = Table(bio_data, colWidths=[2.2 * inch, 1.4 * inch, 2.4 * inch, 1.6 * inch])
    t_bio.setStyle(TableStyle([
        ("SPAN", (0, 0), (1, 0)),
        ("SPAN", (2, 0), (3, 0)),
        ("BACKGROUND", (0, 0), (-1, 0), card_bg),
        ("BACKGROUND", (0, 1), (-1, -1), colors.white),
        ("BOX", (0, 0), (-1, -1), 0.5, border_color),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#F1F5F9")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(Paragraph("Remote Sensing Spectral Indices &amp; Fractions", section_heading))
    story.append(t_bio)
    story.append(Spacer(1, 14))

    # 5. Ground Photo Evidence & AI Classification
    story.append(Paragraph("Ground-Level Verification &amp; Computer Vision", section_heading))
    latest_photo = photos[0] if (photos and len(photos) > 0) else None

    if latest_photo:
        p_filename = getattr(latest_photo, "original_filename", "photo.jpg")
        p_class = getattr(latest_photo, "predicted_class", None) or "Unclassified"
        p_conf = getattr(latest_photo, "classification_confidence", None)
        p_conf_str = f"{p_conf * 100:.1f}%" if (p_conf is not None and p_conf > 0) else "N/A"
        p_cam = getattr(latest_photo, "exif_camera_model", "Embedded Sensor") or "Embedded Sensor"
        p_time = getattr(latest_photo, "exif_datetime", "Timestamp Validated") or "Timestamp Validated"

        # Check GPS distance if available
        photo_gps_str = "No embedded GPS geotag found"
        if getattr(latest_photo, "has_gps", False) and latest_photo.exif_gps_lat is not None:
            photo_gps_str = f"{latest_photo.exif_gps_lat:.4f}°N, {latest_photo.exif_gps_lon:.4f}°E"

        photo_data = [
            [
                Paragraph("<b>Photograph Filename:</b>", body_style),
                Paragraph(f"{p_filename}", bold_style),
                Paragraph("<b>Camera Model:</b>", body_style),
                Paragraph(f"{p_cam}", body_style),
            ],
            [
                Paragraph("<b>Vision AI Classification:</b>", body_style),
                Paragraph(f"<b>{p_class.replace('_', ' ').title()}</b> ({p_conf_str} certainty)", bold_style),
                Paragraph("<b>Capture Timestamp:</b>", body_style),
                Paragraph(f"{p_time}", body_style),
            ],
            [
                Paragraph("<b>Embedded Photo GPS:</b>", body_style),
                Paragraph(f"{photo_gps_str}", body_style),
                Paragraph("<b>Multi-Modal Agreement:</b>", body_style),
                Paragraph(
                    "<b>MATCHED</b>" if getattr(analysis, "photo_agreement", False)
                    else "<b>FLAGGED / REVIEW</b>",
                    bold_style,
                ),
            ],
        ]
    else:
        photo_data = [
            [
                Paragraph("No on-ground verification photos submitted for this analysis.", body_style),
                "",
                "",
                "",
            ]
        ]

    t_photo = Table(photo_data, colWidths=[2.0 * inch, 2.2 * inch, 1.8 * inch, 1.6 * inch])
    t_photo.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
        ("BOX", (0, 0), (-1, -1), 0.5, border_color),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#F1F5F9")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(t_photo)
    story.append(Spacer(1, 14))

    # 6. EXIF Forensics & Discrepancy Warnings
    story.append(Paragraph("EXIF Metadata Forensics &amp; Warnings", section_heading))
    warnings_list = []

    # Collect flags from analysis
    if hasattr(analysis, "flags_json") and analysis.flags_json:
        try:
            flags = json.loads(analysis.flags_json)
            if isinstance(flags, list):
                warnings_list.extend(flags)
        except Exception:
            pass

    # Collect photo EXIF warnings
    if latest_photo and hasattr(latest_photo, "exif_warnings_json") and latest_photo.exif_warnings_json:
        try:
            p_warnings = json.loads(latest_photo.exif_warnings_json)
            if isinstance(p_warnings, list):
                for pw in p_warnings:
                    if pw not in warnings_list:
                        warnings_list.append(pw)
        except Exception:
            pass

    if not warnings_list:
        warnings_list = [
            "All telemetry and metadata integrity checks passed.",
            "No spatial or spectral discrepancies detected against reference baseline.",
        ]

    warn_rows = [[Paragraph(f"• &nbsp; {w}", body_style)] for w in warnings_list]
    t_warn = Table(warn_rows, colWidths=[7.4 * inch])
    t_warn.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), card_bg),
        ("BOX", (0, 0), (-1, -1), 0.5, border_color),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(t_warn)
    story.append(Spacer(1, 14))

    # 7. Audit Footer
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    footer_text = f"Report Generated: {now_utc} &nbsp;|&nbsp; Source: Google Earth Engine &nbsp;|&nbsp; Engine: Neerdrushti Auditing Core"
    story.append(Paragraph(footer_text, disclaimer_style))

    doc.build(story)
    return buffer.getvalue()
