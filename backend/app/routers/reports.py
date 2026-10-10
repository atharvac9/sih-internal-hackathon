"""
Reports API — PDF export via WeasyPrint.
"""

import io
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.site import Site
from app.models.analysis import AnalysisResult
from app.models.photo import Photo

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/reports", tags=["reports"])


def _generate_report_html(site: Site, analysis: AnalysisResult, photos: list[Photo]) -> str:
    """Generate HTML for the PDF report — uses the same visual language as the frontend."""

    # Determine colors based on status
    status = analysis.overall_status or "N/A"
    status_color = {
        "confirmed": "#16A34A",
        "anomaly": "#DC2626",
        "inconclusive": "#EAB308",
    }.get(status, "#6B7280")

    score = analysis.health_score or 0
    grade = analysis.health_grade or "?"
    score_color = "#16A34A" if score >= 70 else "#EAB308" if score >= 45 else "#DC2626"

    mode_label = "Before/After Analysis" if analysis.mode == "full" else "Current Snapshot"

    # Build flags HTML
    flags_html = ""
    if analysis.flags_json:
        flags = json.loads(analysis.flags_json)
        if flags:
            flag_items = "".join(f'<li style="color: #DC2626; margin: 4px 0;">{f}</li>' for f in flags)
            flags_html = f'''
            <div style="background: #FEF2F2; border: 1px solid #FECACA; border-radius: 8px; padding: 12px; margin: 16px 0;">
                <strong style="color: #DC2626;">⚠ Cross-Validation Flags</strong>
                <ul style="margin: 8px 0 0 16px; padding: 0;">{flag_items}</ul>
            </div>
            '''

    # Build satellite section
    sat_html = '<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin: 12px 0;">'
    if analysis.mode == "full":
        sat_html += f'''
        <div style="background: #F0FDF4; border-radius: 8px; padding: 12px;">
            <div style="font-size: 10px; color: #6B7280; text-transform: uppercase;">NDVI Change</div>
            <div style="font-size: 24px; font-weight: 700;">{analysis.delta_ndvi or 0:+.3f}</div>
            <div style="font-size: 11px; color: #9CA3AF;">{analysis.ndvi_t0 or 0:.3f} → {analysis.ndvi_tnow or 0:.3f}</div>
        </div>
        <div style="background: #EFF6FF; border-radius: 8px; padding: 12px;">
            <div style="font-size: 10px; color: #6B7280; text-transform: uppercase;">NDWI Change</div>
            <div style="font-size: 24px; font-weight: 700;">{analysis.delta_ndwi or 0:+.3f}</div>
            <div style="font-size: 11px; color: #9CA3AF;">{analysis.ndwi_t0 or 0:.3f} → {analysis.ndwi_tnow or 0:.3f}</div>
        </div>
        '''
    else:
        sat_html += f'''
        <div style="background: #F0FDF4; border-radius: 8px; padding: 12px;">
            <div style="font-size: 10px; color: #6B7280; text-transform: uppercase;">Current NDVI</div>
            <div style="font-size: 24px; font-weight: 700;">{analysis.ndvi_tnow or 0:.3f}</div>
        </div>
        <div style="background: #EFF6FF; border-radius: 8px; padding: 12px;">
            <div style="font-size: 10px; color: #6B7280; text-transform: uppercase;">Current NDWI</div>
            <div style="font-size: 24px; font-weight: 700;">{analysis.ndwi_tnow or 0:.3f}</div>
        </div>
        '''
    sat_html += '</div>'

    # Photo evidence section
    photos_html = ""
    if photos:
        photo_items = ""
        for p in photos[:4]:  # Max 4 photos in report
            url = p.public_url or ""
            photo_items += f'''
            <div style="flex: 1; min-width: 200px;">
                <img src="{url}" style="width: 100%; border-radius: 8px; max-height: 200px; object-fit: cover;" />
                <div style="font-size: 10px; color: #6B7280; margin-top: 4px;">
                    {p.predicted_class or "Unclassified"} ({(p.classification_confidence or 0) * 100:.0f}%)
                </div>
            </div>
            '''
        photos_html = f'''
        <h3 style="margin-top: 20px; color: #0F766E;">Photo Evidence</h3>
        <div style="display: flex; gap: 12px; flex-wrap: wrap;">{photo_items}</div>
        '''

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    html = f'''<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    body {{
        font-family: 'Inter', sans-serif;
        color: #1E293B;
        max-width: 800px;
        margin: 0 auto;
        padding: 40px;
        font-size: 13px;
        line-height: 1.5;
    }}
    h1 {{ font-size: 22px; font-weight: 700; margin: 0; }}
    h2 {{ font-size: 16px; font-weight: 600; color: #0F766E; margin: 24px 0 8px 0; }}
    h3 {{ font-size: 14px; font-weight: 600; margin: 16px 0 8px 0; }}
</style>
</head>
<body>
    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 24px; padding-bottom: 16px; border-bottom: 2px solid #0F766E;">
        <div>
            <h1>🌊 Watershed Site Report</h1>
            <div style="color: #6B7280; margin-top: 4px;">{mode_label}</div>
        </div>
        <div style="text-align: right;">
            <div style="background: {status_color}15; color: {status_color}; border: 1px solid {status_color}40; padding: 4px 12px; border-radius: 16px; font-weight: 600; font-size: 11px; text-transform: uppercase;">
                {status}
            </div>
        </div>
    </div>

    <h2>Site Information</h2>
    <table style="width: 100%; border-collapse: collapse;">
        <tr><td style="padding: 6px 0; color: #6B7280; width: 140px;">Coordinates</td><td>{site.lat:.4f}°N, {site.lon:.4f}°E</td></tr>
        <tr><td style="padding: 6px 0; color: #6B7280;">Activity Type</td><td>{site.activity_type or "Not specified"}</td></tr>
        <tr><td style="padding: 6px 0; color: #6B7280;">Buffer Radius</td><td>{analysis.buffer_radius_m}m</td></tr>
        <tr><td style="padding: 6px 0; color: #6B7280;">Description</td><td>{site.description or "—"}</td></tr>
    </table>

    <h2>Health Score</h2>
    <div style="display: flex; align-items: center; gap: 16px; background: #F8FAFC; border-radius: 12px; padding: 16px; margin: 8px 0;">
        <div style="font-size: 48px; font-weight: 700; color: {score_color};">{score}</div>
        <div>
            <div style="font-size: 11px; color: #6B7280; text-transform: uppercase;">out of 100</div>
            <div style="background: {score_color}15; color: {score_color}; padding: 2px 8px; border-radius: 4px; font-weight: 600; font-size: 12px; display: inline-block; margin-top: 4px;">Grade {grade}</div>
        </div>
    </div>

    <h2>Satellite Indices</h2>
    {sat_html}

    {flags_html}
    {photos_html}

    <div style="margin-top: 32px; padding-top: 12px; border-top: 1px solid #E2E8F0; color: #9CA3AF; font-size: 10px; text-align: center;">
        Clean Water Initiative — Report generated {generated_at}
    </div>
</body>
</html>'''

    return html


@router.get("/{site_id}/pdf")
async def export_pdf(site_id: str, db: AsyncSession = Depends(get_db)):
    """Export a site analysis report as PDF."""

    # Get site
    result = await db.execute(select(Site).where(Site.id == site_id))
    site = result.scalar_one_or_none()
    if site is None:
        raise HTTPException(status_code=404, detail="Site not found")

    # Get latest analysis
    result = await db.execute(
        select(AnalysisResult)
        .where(AnalysisResult.site_id == site_id)
        .order_by(AnalysisResult.created_at.desc())
        .limit(1)
    )
    analysis = result.scalar_one_or_none()
    if analysis is None:
        raise HTTPException(status_code=404, detail="No analysis results found")

    # Get photos
    result = await db.execute(
        select(Photo)
        .where(Photo.site_id == site_id)
        .order_by(Photo.created_at.desc())
    )
    photos = result.scalars().all()

    # Generate HTML
    html_content = _generate_report_html(site, analysis, list(photos))

    # Convert to PDF with WeasyPrint
    try:
        from weasyprint import HTML
        pdf_bytes = HTML(string=html_content).write_pdf()
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="WeasyPrint is not installed. Install with: pip install weasyprint",
        )
    except Exception as e:
        logger.error(f"PDF generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {e}")

    site_code = site.site_code or site.id[:8]
    filename = f"watershed_report_{site_code}_{datetime.now(timezone.utc).strftime('%Y%m%d')}.pdf"

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
