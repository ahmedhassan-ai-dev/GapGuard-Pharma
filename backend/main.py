"""GapGuard Pharma REST API: analytical decision support only."""
from __future__ import annotations
import math
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field, model_validator

from gapguard.importer import read_csv_flexible, suggested_fields, normalize_sensor_data, infer_sampling_minutes
from gapguard.engine import recover
from gapguard.pharma import ProductProfile, investigate, generate_multi_product_pdf
from gapguard.numerical import INTERPOLATORS, ROOT_SOLVERS

app = FastAPI(title='GapGuard Pharma API', version='3.1')
app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:5173', 'http://127.0.0.1:5173'],
    allow_credentials=False,
    allow_methods=['*'],
    allow_headers=['*'],
)

class Product(BaseModel):
    id: str
    name_en: str
    name_ar: str
    lower: float
    upper: float
    source: str
    evidence_level: str = 'USER_DEFINED'
    note: str = ''
    manufacturer: str = ''
    batch: str = ''
    allowed_above_minutes: float | None = None
    allowed_below_minutes: float | None = None
    class_name: str = 'Vaccine'

    @model_validator(mode='after')
    def validate_limits(self):
        if not math.isfinite(self.lower) or not math.isfinite(self.upper) or self.lower >= self.upper:
            raise ValueError('lower must be less than upper')
        for x in [self.allowed_above_minutes, self.allowed_below_minutes]:
            if x is not None and (not math.isfinite(x) or x < 0):
                raise ValueError('allowed exposure minutes must be non-negative')
        return self

class MapRequest(BaseModel):
    timestamp_column: str | None = None
    date_column: str | None = None
    time_column: str | None = None
    value_column: str
    sensor_column: str | None = None
    sensor_id: str | None = None
    duplicates: str = 'reject'
    expected_minutes: float | None = None
    method: str = 'Newton divided differences'
    context: int = 2
    max_gap: int = 5
    products: list[Product] = Field(min_length=1, max_length=40)

# Reference catalog entries: class/reference profiles only, intended for screening/demo.
# Product-specific release decisions require the exact registered brand/presentation label.
CATALOG = [
    Product(id='hepa', name_en='Hepatitis A vaccine', name_ar='لقاح التهاب الكبد أ', lower=2, upper=8, source='https://www.cdc.gov/vaccines/hcp/storage-handling/', evidence_level='CLASS_REFERENCE_ONLY', note='Reference vaccine class profile. Verify exact product insert and local handling SOPs.', class_name='Vaccine'),
    Product(id='hepb', name_en='Hepatitis B vaccine', name_ar='لقاح التهاب الكبد ب', lower=2, upper=8, source='https://www.cdc.gov/vaccines/hcp/storage-handling/', evidence_level='CLASS_REFERENCE_ONLY', note='Reference vaccine class profile.', class_name='Vaccine'),
    Product(id='dtap', name_en='DTaP vaccine', name_ar='لقاح DTaP', lower=2, upper=8, source='https://www.cdc.gov/vaccines/hcp/storage-handling/', evidence_level='CLASS_REFERENCE_ONLY', note='Reference vaccine class profile.', class_name='Vaccine'),
    Product(id='tdap', name_en='Tdap vaccine', name_ar='لقاح Tdap', lower=2, upper=8, source='https://www.cdc.gov/vaccines/hcp/storage-handling/', evidence_level='CLASS_REFERENCE_ONLY', note='Reference vaccine class profile.', class_name='Vaccine'),
    Product(id='td', name_en='Td vaccine', name_ar='لقاح Td', lower=2, upper=8, source='https://www.cdc.gov/vaccines/hcp/storage-handling/', evidence_level='CLASS_REFERENCE_ONLY', note='Reference vaccine class profile.', class_name='Vaccine'),
    Product(id='hib', name_en='Hib vaccine', name_ar='لقاح Hib', lower=2, upper=8, source='https://www.cdc.gov/vaccines/hcp/storage-handling/', evidence_level='CLASS_REFERENCE_ONLY', note='Reference vaccine class profile.', class_name='Vaccine'),
    Product(id='ipv', name_en='Inactivated polio vaccine (IPV)', name_ar='لقاح شلل الأطفال المعطل IPV', lower=2, upper=8, source='https://www.cdc.gov/vaccines/hcp/storage-handling/', evidence_level='CLASS_REFERENCE_ONLY', note='Reference vaccine class profile.', class_name='Vaccine'),
    Product(id='pcv13', name_en='Pneumococcal conjugate vaccine (PCV13)', name_ar='لقاح المكورات الرئوية PCV13', lower=2, upper=8, source='https://www.cdc.gov/vaccines/hcp/storage-handling/', evidence_level='CLASS_REFERENCE_ONLY', note='Reference vaccine class profile.', class_name='Vaccine'),
    Product(id='pcv15', name_en='Pneumococcal conjugate vaccine (PCV15)', name_ar='لقاح المكورات الرئوية PCV15', lower=2, upper=8, source='https://www.cdc.gov/vaccines/hcp/storage-handling/', evidence_level='CLASS_REFERENCE_ONLY', note='Reference vaccine class profile.', class_name='Vaccine'),
    Product(id='pcv20', name_en='Pneumococcal conjugate vaccine (PCV20)', name_ar='لقاح المكورات الرئوية PCV20', lower=2, upper=8, source='https://www.cdc.gov/vaccines/hcp/storage-handling/', evidence_level='CLASS_REFERENCE_ONLY', note='Reference vaccine class profile.', class_name='Vaccine'),
    Product(id='ppsv23', name_en='Pneumococcal polysaccharide vaccine (PPSV23)', name_ar='لقاح المكورات الرئوية PPSV23', lower=2, upper=8, source='https://www.cdc.gov/vaccines/hcp/storage-handling/', evidence_level='CLASS_REFERENCE_ONLY', note='Reference vaccine class profile.', class_name='Vaccine'),
    Product(id='mmr', name_en='MMR vaccine', name_ar='لقاح الحصبة والنكاف والحصبة الألمانية', lower=2, upper=8, source='https://www.cdc.gov/vaccines/hcp/storage-handling/', evidence_level='CLASS_REFERENCE_ONLY', note='Reference vaccine class profile. Some handling details vary by product.', class_name='Vaccine'),
    Product(id='varicella', name_en='Varicella vaccine', name_ar='لقاح الجديري المائي', lower=2, upper=8, source='https://www.cdc.gov/vaccines/hcp/storage-handling/', evidence_level='CLASS_REFERENCE_ONLY', note='Use exact label instructions for product/presentation-specific storage requirements.', class_name='Vaccine'),
    Product(id='rota', name_en='Rotavirus vaccine', name_ar='لقاح فيروس الروتا', lower=2, upper=8, source='https://www.cdc.gov/vaccines/hcp/storage-handling/', evidence_level='CLASS_REFERENCE_ONLY', note='Reference vaccine class profile.', class_name='Vaccine'),
    Product(id='menacwy', name_en='Meningococcal ACWY vaccine', name_ar='لقاح المكورات السحائية ACWY', lower=2, upper=8, source='https://www.cdc.gov/vaccines/hcp/storage-handling/', evidence_level='CLASS_REFERENCE_ONLY', note='Reference vaccine class profile.', class_name='Vaccine'),
    Product(id='menb', name_en='Meningococcal B vaccine', name_ar='لقاح المكورات السحائية B', lower=2, upper=8, source='https://www.cdc.gov/vaccines/hcp/storage-handling/', evidence_level='CLASS_REFERENCE_ONLY', note='Reference vaccine class profile.', class_name='Vaccine'),
    Product(id='hpv', name_en='HPV vaccine', name_ar='لقاح فيروس الورم الحليمي البشري', lower=2, upper=8, source='https://www.cdc.gov/vaccines/hcp/storage-handling/', evidence_level='CLASS_REFERENCE_ONLY', note='Reference vaccine class profile.', class_name='Vaccine'),
    Product(id='influenza', name_en='Inactivated influenza vaccine', name_ar='لقاح الإنفلونزا المعطل', lower=2, upper=8, source='https://www.cdc.gov/vaccines/hcp/storage-handling/', evidence_level='CLASS_REFERENCE_ONLY', note='Reference vaccine class profile.', class_name='Vaccine'),
    Product(id='covid_refrigerated', name_en='Refrigerated COVID-19 product (profile-specific)', name_ar='منتج كوفيد محفوظ مبردًا (حسب الملف)', lower=2, upper=8, source='https://www.cdc.gov/vaccines/hcp/storage-handling/', evidence_level='PROFILE_REFERENCE_ONLY', note='Range and shelf-life vary by manufacturer and formulation; verify exact product profile.', class_name='Vaccine'),
    Product(id='rsv', name_en='RSV product (profile-specific)', name_ar='منتج RSV (حسب الملف)', lower=2, upper=8, source='https://www.cdc.gov/vaccines/hcp/storage-handling/', evidence_level='PROFILE_REFERENCE_ONLY', note='Verify exact monoclonal/vaccine product instructions.', class_name='Vaccine'),
    Product(id='shingrix_pfs_fda', name_en='SHINGRIX — prefilled syringe (FDA US label)', name_ar='شينجريكس — سرنجة معبأة مسبقًا (نشرة FDA)', lower=2, upper=8, source='https://www.fda.gov/downloads/BiologicsBloodVaccines/Vaccines/ApprovedProducts/UCM581605.pdf', evidence_level='FDA_PRESENTATION_REFERENCE', manufacturer='GSK', note='FDA label: store at 2–8°C. The prefilled syringe may be kept up to 72 hours at 8–25°C after removal from refrigerator. This is a CONDITIONAL range-specific handling window, not generic tolerance above 8°C. Prior removal history and exact presentation must be known. Not verified for Egyptian registration.', class_name='Vaccine'),
    Product(id='mmrii_lyo_merck', name_en='M-M-R II — lyophilized vaccine (Merck US)', name_ar='إم إم آر 2 — لقاح مجفد (ميرك)', lower=-50, upper=8, source='https://www.merckvaccines.com/mmr/storage-handling/', evidence_level='MANUFACTURER_PRESENTATION_REFERENCE', manufacturer='Merck', note='Lyophilized vaccine: manufacturer permits storage from -50 to +8°C; diluent has separate conditions. This is a broad permitted storage range, not an instruction for a mixed icebox. Check exact version and local label.', class_name='Vaccine'),
    Product(id='custom', name_en='Custom temperature-sensitive product', name_ar='منتج حساس للحرارة (مخصص)', lower=2, upper=8, source='USER_SUPPLIED', evidence_level='USER_DEFINED', note='Create your own profile from a manufacturer insert or approved SOP.', class_name='Custom'),
]

FORMULAS = [
    {
        'id': 'newton',
        'title_en': 'Newton interpolation',
        'title_ar': 'استيفاء نيوتن',
        'equation': 'P(t) = Σ[i=0→n] aᵢ Π[j=0→i-1] (t - tⱼ)',
        'use_en': 'Estimate missing temperature values inside short gaps.',
        'use_ar': 'تقدير القراءات المفقودة داخل الفجوات القصيرة.'
    },
    {
        'id': 'root',
        'title_en': 'Threshold crossing equation',
        'title_ar': 'معادلة تجاوز الحد',
        'equation': 'f(t) = P(t) - T_limit = 0',
        'use_en': 'Find the modeled time when the reconstructed temperature crosses a limit.',
        'use_ar': 'إيجاد الزمن المتوقع الذي يتقاطع فيه المنحنى المقدر مع حد الحرارة.'
    },
    {
        'id': 'exposure',
        'title_en': 'Exposure duration and severity',
        'title_ar': 'مدة وشدة التعرض',
        'equation': 'D = t_return - t_start,  E = ∫ max(P(t)-T_upper, 0) dt',
        'use_en': 'Measure how long the product stayed outside range and how severe the excursion was.',
        'use_ar': 'قياس مدة البقاء خارج النطاق ومدى شدة التجاوز.'
    },
]

METHODS = [
    {'name': 'Linear interpolation', 'category': 'Interpolation', 'role_en': 'Baseline reconstruction inside gaps.', 'role_ar': 'إعادة بناء أساسية داخل الفجوات.'},
    {'name': 'Newton divided differences', 'category': 'Interpolation', 'role_en': 'Local polynomial reconstruction for gap filling.', 'role_ar': 'إعادة بناء محلية متعددة الحدود لتعويض الفجوات.'},
    {'name': 'Lagrange interpolation', 'category': 'Interpolation', 'role_en': 'Alternative local interpolator for comparison.', 'role_ar': 'بديل عددي للمقارنة مع نيوتن.'},
    {'name': 'Bisection', 'category': 'Root finding', 'role_en': 'Robustly finds threshold crossing times.', 'role_ar': 'إيجاد أوقات تجاوز الحدود بطريقة مستقرة.'},
    {'name': 'Secant', 'category': 'Root finding', 'role_en': 'Fast threshold root approximation without explicit derivative.', 'role_ar': 'تقريب سريع للجذر دون مشتقة صريحة.'},
    {'name': 'Newton-Raphson', 'category': 'Root finding', 'role_en': 'Fast convergence when derivative estimate is available.', 'role_ar': 'تقارب سريع عندما يتوفر تقدير للمشتقة.'},
    {'name': 'Trapezoidal integration', 'category': 'Integration', 'role_en': 'Computes degree-minutes of exposure.', 'role_ar': 'حساب شدة التعرض بوحدة درجة×دقيقة.'},
]

@app.get('/api/health')
def health():
    return {'status': 'ok', 'numerical_core': 'GapGuard MATH301'}

@app.get('/api/catalog')
def catalog():
    return {
        'products': [p.model_dump() for p in CATALOG],
        'note': 'Built-in entries are reference/demo profiles. Product-specific release decisions require the exact local registered product documentation.'
    }

@app.get('/api/sources')
def sources():
    return {
        'catalog': [p.model_dump() for p in CATALOG],
        'formulas': [],
        'methods': METHODS,
        'official_sources': [
            {'title': 'CDC Vaccine Storage and Handling', 'url': 'https://www.cdc.gov/vaccines/hcp/storage-handling/'},
            {'title': 'CDC Vaccine Storage and Handling Toolkit (July 2026)', 'url': 'https://cdc.gov/vaccines/hcp/downloads/storage-handling-toolkit.pdf'},
            {'title':'FDA SHINGRIX package insert — presentation-specific storage', 'url':'https://www.fda.gov/downloads/BiologicsBloodVaccines/Vaccines/ApprovedProducts/UCM581605.pdf'},
            {'title':'Merck M-M-R II storage and handling', 'url':'https://www.merckvaccines.com/mmr/storage-handling/'},
        ],
        'notes': [
            'Class/reference profiles are not a substitute for the exact manufacturer insert or national SOP.',
            'If no product-specific time-temperature allowance is verified, do not interpret exposure duration as an allowable excursion.',
            'Example: SHINGRIX prefilled syringe FDA label describes up to 72 hours between 8–25°C. It is not blanket tolerance at any temperature above 8°C; prior time outside refrigeration and presentation must be known.',
        ]
    }


def _load(data: bytes):
    try:
        return read_csv_flexible(data)
    except Exception as exc:
        raise HTTPException(422, str(exc))

@app.post('/api/preview')
async def preview(file: UploadFile = File(...)):
    df = _load(await file.read())
    hints = suggested_fields(df.columns)
    return {
        'columns': list(df.columns),
        'hints': hints,
        'rows': len(df),
        'preview': df.head(6).replace({np.nan: None}).to_dict(orient='records'),
        'sensors': {str(c): sorted(df[c].dropna().astype(str).unique().tolist())[:100] for c in df.columns if c == hints.get('sensor')},
    }


def _normalize_json(x: Any):
    if isinstance(x, dict):
        return {k: _normalize_json(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_normalize_json(z) for z in x]
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.floating, float)):
        return float(x) if np.isfinite(x) else None
    if isinstance(x, (pd.Timestamp,)):
        return x.isoformat()
    if isinstance(x, (np.bool_,)):
        return bool(x)
    return x


def analyze_data(data: bytes, req: MapRequest) -> dict:
    df = _load(data)
    try:
        source, transforms = normalize_sensor_data(
            df,
            timestamp_column=req.timestamp_column,
            date_column=req.date_column,
            time_column=req.time_column,
            value_column=req.value_column,
            sensor_column=req.sensor_column,
            sensor_id=req.sensor_id,
            duplicates=req.duplicates,
        )
        inferred = infer_sampling_minutes(source)
        interval = req.expected_minutes or inferred
        if interval is None or not float(interval).is_integer() or not 1 <= interval <= 1440:
            raise ValueError('Sampling interval cannot be inferred as whole minutes; inspect timestamp cadence or supply an explicit value.')
        interval = int(interval)
        if req.method not in INTERPOLATORS:
            raise ValueError('Unknown interpolation method')
        recovered, gaps = recover(source, minutes=interval, max_gap=req.max_gap, method=req.method, window=req.context)
    except (ValueError, KeyError, TypeError) as exc:
        raise HTTPException(422, str(exc))

    assessments = []
    for item in req.products:
        profile = ProductProfile(
            item.id,
            item.name_en,
            item.lower,
            item.upper,
            '°C',
            item.source,
            item.note,
            False,
            item.allowed_above_minutes,
            item.allowed_below_minutes,
            item.evidence_level,
            item.manufacturer,
            item.batch,
            item.class_name,
        )
        review = investigate(recovered, profile, gaps)
        assessments.append({'item': item.model_dump(), 'result': review})

    times = recovered.timestamp.dt.strftime('%Y-%m-%dT%H:%M:%S').tolist()
    timeline = [
        {
            'timestamp': times[i],
            'measured': float(v) if pd.notna(v) else None,
            'estimated': float(recovered.estimated.iloc[i]) if pd.notna(recovered.estimated.iloc[i]) else None,
            'provenance': recovered.provenance.iloc[i],
        }
        for i, v in enumerate(recovered.value)
    ]

    result = {
        'interval_minutes': interval,
        'inferred_minutes': inferred,
        'transformations': transforms,
        'timeline': timeline,
        'gaps': gaps,
        'assessments': assessments,
        'method': req.method,
        'numerical_explanation': {
            'interpolation': 'Local interpolation estimates missing observations; modeled values are NOT measured.',
            'root_finding': 'Bisection solves each linear segment crossing of P(t)-limit=0.',
            'exposure': 'Trapezoidal integration over above/below-limit segments measures degree-minutes.',
            'limitation': 'No sensor readings between samples can prove a product remained within specification.',
        },
    }
    return _normalize_json(result)

@app.post('/api/analyze')
async def analyze(file: UploadFile = File(...), mapping: str = Form(...)):
    try:
        req = MapRequest.model_validate_json(mapping)
    except Exception as exc:
        raise HTTPException(422, f'Invalid analysis settings: {exc}')
    return analyze_data(await file.read(), req)

class ReportRequest(BaseModel):
    analysis: dict
    title: str = 'GapGuard Pharma Evidence Report'

@app.post('/api/report')
def report(payload: ReportRequest):
    try:
        pdf = generate_multi_product_pdf(payload.analysis, payload.title)
        return Response(pdf, media_type='application/pdf', headers={'Content-Disposition': 'attachment; filename="gapguard-pharma-evidence.pdf"'})
    except Exception as exc:
        raise HTTPException(422, str(exc))

@app.get('/api/demo/{name}')
def demo(name: str):
    filenames = {
        'normal': 'vaccine_delivery_normal.csv',
        'excursion': 'vaccine_delivery_nomissing.csv',
        'missing': 'vaccine_delivery_missing.csv',
    }
    if name not in filenames:
        raise HTTPException(404, 'Unknown scenario')
    return Response((Path(__file__).parent / 'data' / filenames[name]).read_bytes(), media_type='text/csv', headers={'Content-Disposition': f'attachment; filename="{filenames[name]}"'})
