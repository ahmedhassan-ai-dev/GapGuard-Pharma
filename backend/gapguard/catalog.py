"""Evidence-tracked candidate catalog. NOT a verified Egypt SKU database.
These are CDC vaccine *classes* for screening only; confirm Egyptian brand,
manufacturer, presentation, diluent and current insert before clinical use.
"""
from dataclasses import dataclass

CDC_TABLE = 'https://www.cdc.gov/vaccines/hcp/imz-best-practices/storage-handling-immunobiologics.html'
CDC_TOOLKIT = 'https://www.cdc.gov/vaccines/hcp/storage-handling/index.html'

@dataclass(frozen=True)
class CatalogEntry:
    key: str
    name_en: str
    name_ar: str
    category: str
    lower: float | None
    upper: float | None
    source: str
    verification: str = 'CLASS_REFERENCE_ONLY'
    note: str = 'Not SKU-specific. Verify current Egypt-registered product insert, formulation, diluent and manufacturer before use.'

# Only class-level policy, 2–8°C, where specifically supported by CDC.
# NO implied validation of local brand availability, and no expiration or release calculations.
_CLASSES = [
    ('hepa','Hepatitis A vaccine','لقاح التهاب الكبد A'),
    ('hepb','Hepatitis B vaccine','لقاح التهاب الكبد B'),
    ('dtap','DTaP vaccine','لقاح الدفتيريا والتيتانوس والسعال الديكي للأطفال'),
    ('tdap','Tdap vaccine','لقاح التيتانوس والدفتيريا والسعال الديكي'),
    ('td','Td vaccine','لقاح التيتانوس والدفتيريا'),
    ('pcv13','PCV13 pneumococcal vaccine','لقاح المكورات الرئوية PCV13'),
    ('pcv15','PCV15 pneumococcal vaccine','لقاح المكورات الرئوية PCV15'),
    ('pcv20','PCV20 pneumococcal vaccine','لقاح المكورات الرئوية PCV20'),
    ('hpv','HPV vaccine','لقاح فيروس الورم الحليمي'),
    ('ipv','Inactivated polio vaccine (IPV)','لقاح شلل الأطفال المعطل'),
    ('hib','Hib vaccine','لقاح المستدمية النزلية ب'),
    ('menacwy','Meningococcal ACWY vaccine','لقاح المكورات السحائية ACWY'),
    ('menb','Meningococcal B vaccine','لقاح المكورات السحائية B'),
    ('ppsv23','Pneumococcal polysaccharide vaccine','لقاح المكورات الرئوية متعدد السكريات'),
    ('influenza_iiv','Inactivated influenza vaccine','لقاح الإنفلونزا المعطل'),
    ('influenza_laiv','Live attenuated influenza vaccine','لقاح الإنفلونزا الحي المضعف'),
    ('rv1','Rotavirus RV1 vaccine','لقاح فيروس الروتا RV1'),
    ('rv5','Rotavirus RV5 vaccine','لقاح فيروس الروتا RV5'),
    ('rzv','Recombinant zoster vaccine (RZV)','لقاح الحزام الناري المؤتلف'),
    ('rsv','RSV vaccine (formulation-specific)','لقاح الفيروس التنفسي المخلوي'),
]

CATALOG = {key:CatalogEntry(key,en,ar,'vaccine_class',2.,8.,CDC_TABLE if key not in ('rv1','rv5','rsv') else CDC_TOOLKIT)
           for key,en,ar in _CLASSES}

def catalog_rows():
    return [{'id':p.key,'English':p.name_en,'العربية':p.name_ar,'Screening range °C':f'{p.lower:g} to {p.upper:g}',
             'Evidence level':p.verification,'Reference':p.source} for p in CATALOG.values()]
