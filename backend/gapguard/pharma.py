"""Pharma workflow for academic cold-chain investigation (NOT product release decisions)."""
from dataclasses import dataclass
import io
import pandas as pd
import numpy as np
from .exposure import exposure_analysis

CDC_URL = 'https://www.cdc.gov/vaccines/hcp/storage-handling/'

@dataclass(frozen=True)
class ProductProfile:
    code: str
    name: str
    lower: float
    upper: float
    unit: str
    source: str
    note: str
    verified_for_product: bool = False
    allowed_above_minutes: float | None = None
    allowed_below_minutes: float | None = None
    evidence_level: str = 'USER_DEFINED'
    manufacturer: str = ''
    batch: str = ''
    class_name: str = 'Product'



# Backward-compatible demonstration profile
PROFILES = {
    'vaccine_demo': ProductProfile('vaccine_demo','Refrigerated vaccine – general demonstration',2.0,8.0,'°C',CDC_URL,
       'Illustrative refrigerated vaccine category. Verify manufacturer package insert for actual vaccine.',False,None,None,'CLASS_REFERENCE_ONLY','','','Vaccine')
}

def custom_profile(name, lower, upper, source, unit='°C'):
    if not name.strip():
        raise ValueError('Product name required')
    if not np.isfinite(lower) or not np.isfinite(upper) or lower >= upper:
        raise ValueError('Invalid temperature limits')
    return ProductProfile(
        'custom', name.strip(), float(lower), float(upper), unit,
        source.strip() or 'User-supplied; not verified',
        'User-defined policy; confirm original manufacturer documentation.',
        False,
    )


def _allowance_summary(episodes, allowed_above, allowed_below):
    high = sum(e['duration_min'] for e in episodes if e['kind'] == 'High')
    low = sum(e['duration_min'] for e in episodes if e['kind'] == 'Low')
    out = []
    if allowed_above is not None:
        out.append({'kind': 'High', 'allowed_minutes': float(allowed_above), 'actual_minutes': float(high), 'status': 'WITHIN_CONFIGURED_ALLOWANCE' if high <= allowed_above else 'EXCEEDED_CONFIGURED_ALLOWANCE'})
    if allowed_below is not None:
        out.append({'kind': 'Low', 'allowed_minutes': float(allowed_below), 'actual_minutes': float(low), 'status': 'WITHIN_CONFIGURED_ALLOWANCE' if low <= allowed_below else 'EXCEEDED_CONFIGURED_ALLOWANCE'})
    return out


def investigate(out, profile, gaps=None):
    """Assess observed and modeled time-series evidence, including no-gap cases."""
    gaps = gaps or []
    episodes = exposure_analysis(out, upper=profile.upper, lower=profile.lower)
    readings = out.loc[out['value'].notna(), 'value'].astype(float)
    measured_breach = bool(((readings < profile.lower) | (readings > profile.upper)).any())
    unknown_points = int((out['provenance'] == 'unknown').sum())
    estimated_points = int((out['provenance'] == 'estimated').sum())
    observed_count = int(len(readings))
    start, end = pd.to_datetime(out['timestamp'].iloc[[0, -1]])
    observed_high = int((readings > profile.upper).sum())
    observed_low = int((readings < profile.lower).sum())
    possible_episodes = [e for e in episodes if e['estimated']]
    open_episodes = [e for e in episodes if e.get('may_be_incomplete')]
    allowance = _allowance_summary(episodes, profile.allowed_above_minutes, profile.allowed_below_minutes)
    if measured_breach:
        status = 'DOCUMENTED EXCURSION — HOLD / REVIEW'
    elif unknown_points or estimated_points or gaps:
        status = 'INCOMPLETE EVIDENCE — REVIEW REQUIRED'
    elif episodes:
        status = 'POSSIBLE BETWEEN-SAMPLES EXCURSION — REVIEW'
    else:
        status = 'NO OUT-OF-RANGE READINGS OBSERVED'
    return {
        'product': profile.name,
        'class_name': profile.class_name,
        'manufacturer': profile.manufacturer,
        'batch': profile.batch,
        'policy': {
            'lower': profile.lower, 'upper': profile.upper, 'unit': profile.unit,
            'source': profile.source, 'note': profile.note,
            'product_specific_verified': profile.verified_for_product,
            'evidence_level': profile.evidence_level,
            'allowed_above_minutes': profile.allowed_above_minutes,
            'allowed_below_minutes': profile.allowed_below_minutes,
        },
        'start': start.isoformat(), 'end': end.isoformat(),
        'status': status,
        'measured_count': observed_count,
        'estimated_count': estimated_points,
        'unknown_count': unknown_points,
        'measured_high_count': observed_high,
        'measured_low_count': observed_low,
        'measured_min': float(readings.min()),
        'measured_max': float(readings.max()),
        'episodes': episodes,
        'episode_count': len(episodes),
        'modeled_exposure_minutes': float(sum(e['duration_min'] for e in episodes)),
        'modeled_degree_minutes': float(sum(e['degree_minutes'] for e in episodes)),
        'estimated_episode_count': len(possible_episodes),
        'open_episode_count': len(open_episodes),
        'gap_count': len(gaps),
        'allowance_review': allowance,
        'caveat': 'Mathematical reconstruction does not establish product potency, safety or suitability for use. A missing interval could conceal an unobserved excursion even if both endpoints are normal. Consult qualified personnel, official product label, and manufacturer/program procedures before disposition.',
        'recommended_action': 'For confirmed temperature excursion: segregate the affected product, document the event, and follow the official product and program procedures. Do not independently discard or release based only on this software.',
    }



def assess_batches(investigation, batches):
    """Backward-compatible overlap review helper."""
    begin = pd.Timestamp(investigation['start'])
    finish = pd.Timestamp(investigation['end'])
    ans = []
    for b in batches:
        entry = pd.Timestamp(b['in_time']); exit = pd.Timestamp(b['out_time'])
        if exit < entry: raise ValueError('Batch out_time earlier than in_time')
        overlap = max(0.0, (min(exit, finish) - max(entry, begin)).total_seconds() / 60)
        event_overlap = 0.0
        for e in investigation['episodes']:
            a = pd.Timestamp(e['start']); z = pd.Timestamp(e['end'])
            event_overlap += max(0.0, (min(exit, z) - max(entry, a)).total_seconds() / 60)
        ans.append({'batch': str(b['batch']), 'product': str(b.get('product', investigation['product'])),
                    'analysis_overlap_min': round(overlap, 3), 'modeled_excursion_overlap_min': round(event_overlap, 3),
                    'review': 'REVIEW' if overlap > 0 and (investigation['status'] != 'NO OUT-OF-RANGE READINGS OBSERVED') else 'NO EXCURSION OBSERVED IN WINDOW',
                    'note': 'Not a product release or expiry judgment'})
    return ans


def generate_pdf(assessment, batch_rows=None):
    """Backward-compatible single-product PDF wrapper."""
    payload = {'assessments': [{'item': {'name_en': assessment.get('product', 'Product'), 'name_ar': '', 'lower': assessment['policy']['lower'], 'upper': assessment['policy']['upper'], 'batch': assessment.get('batch', ''), 'manufacturer': assessment.get('manufacturer','')}, 'result': assessment}]}
    return generate_multi_product_pdf(payload, 'GapGuard Pharma Evidence Report')

def generate_multi_product_pdf(analysis: dict, title: str = 'GapGuard Pharma Evidence Report'):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from xml.sax.saxutils import escape

    buff = io.BytesIO()
    doc = SimpleDocTemplate(buff, pagesize=A4, rightMargin=28, leftMargin=28, topMargin=32, bottomMargin=32)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Tiny', parent=styles['BodyText'], fontSize=8, leading=10, textColor=colors.HexColor('#4d5d72')))
    styles.add(ParagraphStyle(name='Eq', parent=styles['Code'], fontName='Helvetica-Bold', fontSize=11, leading=14, textColor=colors.HexColor('#173047')))

    elements = [
        Paragraph(escape(title), styles['Title']),
        Paragraph('GapGuard Pharma | Academic decision-support report (not a release certificate)', styles['Tiny']),
        Spacer(1, 12),
        Paragraph('Workflow diagram', styles['Heading2']),
        Paragraph('Icebox products → Sensor CSV → Numerical reconstruction → Product-by-product cold-chain assessment', styles['BodyText']),
        Spacer(1, 8),
    ]

    assessments = analysis.get('assessments', [])
    rows = [['Product', 'Batch', 'Range', 'Status', 'Exposure min', 'Degree-min']]
    for a in assessments:
        item = a.get('item', {})
        res = a.get('result', {})
        rows.append([
            str(item.get('name_en') or res.get('product', 'Product')),
            str(item.get('batch', '—')),
            f"{item.get('lower', res.get('policy', {}).get('lower', '?'))} to {item.get('upper', res.get('policy', {}).get('upper', '?'))} °C",
            str(res.get('status', '—'))[:32],
            f"{float(res.get('modeled_exposure_minutes', 0)):.2f}",
            f"{float(res.get('modeled_degree_minutes', 0)):.2f}",
        ])
    summary = Table(rows, repeatRows=1, colWidths=[120, 62, 70, 150, 55, 55])
    summary.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e8f5f2')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#16384d')),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('GRID', (0, 0), (-1, -1), 0.35, colors.HexColor('#c9d6df')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elements += [Paragraph('Icebox summary', styles['Heading2']), summary, Spacer(1, 12)]

    # The report intentionally excludes a mathematics section.
    # Numerical evidence remains in analysis metrics and episode tables.

    for idx, a in enumerate(assessments):
        item = a.get('item', {})
        res = a.get('result', {})
        elements += [Paragraph(escape(str(item.get('name_en', res.get('product', f'Product {idx+1}')))), styles['Heading1'])]
        meta_rows = [
            ['Field', 'Value'],
            ['Arabic / English name', f"{item.get('name_ar', '—')} / {item.get('name_en', '—')}"],
            ['Batch / lot', str(item.get('batch', '—'))],
            ['Policy range', f"{res.get('policy', {}).get('lower')} to {res.get('policy', {}).get('upper')} °C"],
            ['Evidence level', str(res.get('policy', {}).get('evidence_level', '—'))],
            ['Policy source', str(res.get('policy', {}).get('source', '—'))],
            ['Configured allowed minutes above upper limit', str(res.get('policy', {}).get('allowed_above_minutes', '—'))],
            ['Configured allowed minutes below lower limit', str(res.get('policy', {}).get('allowed_below_minutes', '—'))],
            ['Assessment status', str(res.get('status', '—'))],
        ]
        meta = Table(meta_rows, repeatRows=1, colWidths=[165, 345])
        meta.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#eef3f9')),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.35, colors.HexColor('#c9d6df')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        elements += [meta, Spacer(1, 8)]
        elements += [Paragraph('Storage instructions are presentation-specific; recorded temperature time outside the usual band is NOT automatically permissible time. If no authorized time-temperature allowance is documented, hold for expert review.', styles['Tiny']), Spacer(1, 8)]

        metric_rows = [
            ['Measured samples', str(res.get('measured_count', 0)), 'Estimated samples', str(res.get('estimated_count', 0))],
            ['Unknown samples', str(res.get('unknown_count', 0)), 'Episode count', str(res.get('episode_count', 0))],
            ['Exposure minutes', f"{float(res.get('modeled_exposure_minutes', 0)):.2f}", 'Degree-minutes', f"{float(res.get('modeled_degree_minutes', 0)):.2f}"],
        ]
        metrics = Table([['Metric', 'Value', 'Metric', 'Value']] + metric_rows, colWidths=[120, 90, 120, 90])
        metrics.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f9fafc')),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.35, colors.HexColor('#d2dbe3')),
        ]))
        elements += [Paragraph('Assessment metrics', styles['Heading2']), metrics, Spacer(1, 8)]

        allow = res.get('allowance_review', []) or []
        if allow:
            allow_rows = [['Direction', 'Allowed minutes', 'Actual minutes', 'Compliance']]
            for x in allow:
                allow_rows.append([x['kind'], f"{x['allowed_minutes']:.2f}", f"{x['actual_minutes']:.2f}", x['status']])
            t = Table(allow_rows, repeatRows=1, colWidths=[80, 100, 100, 220])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#eaf8f4')),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.35, colors.HexColor('#c5d8d2')),
            ]))
            elements += [Paragraph('Configured policy allowance review', styles['Heading2']), t, Spacer(1, 8)]

        eps = res.get('episodes', []) or []
        elements += [Paragraph('Modeled excursion episodes', styles['Heading2'])]
        if eps:
            ep_rows = [['Type', 'Start', 'End', 'Minutes', 'C×min', 'Estimated']]
            for e in eps:
                ep_rows.append([str(e.get('kind')), str(e.get('start'))[:19], str(e.get('end'))[:19], f"{float(e.get('duration_min',0)):.2f}", f"{float(e.get('degree_minutes',0)):.2f}", 'Yes' if e.get('estimated') else 'No'])
            ep = Table(ep_rows, repeatRows=1, colWidths=[45, 120, 120, 60, 60, 55])
            ep.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#eef3f9')),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.35, colors.HexColor('#c9d6df')),
            ]))
            elements += [ep, Spacer(1, 8)]
        else:
            elements += [Paragraph('No modeled episodes were detected.', styles['BodyText']), Spacer(1, 8)]

        elements += [Paragraph(escape(str(res.get('caveat', ''))), styles['Tiny']), Paragraph(escape(str(res.get('recommended_action', ''))), styles['Tiny'])]
        if idx < len(assessments) - 1:
            elements.append(PageBreak())

    doc.build(elements)
    return buff.getvalue()
