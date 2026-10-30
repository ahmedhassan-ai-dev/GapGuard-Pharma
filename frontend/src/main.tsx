import React, { useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { Activity, Archive, ArrowRight, BarChart3, BookOpen, CircleAlert, ClipboardList, FileDown, FileUp, FlaskConical, Globe2, Info, PackagePlus, Plus, ShieldCheck, Trash2, UploadCloud, ChevronDown, Link2 } from 'lucide-react';
import { ResponsiveContainer, LineChart, Line, CartesianGrid, XAxis, YAxis, Tooltip, ReferenceLine, Legend } from 'recharts';
import './style.css';

type Product = { id:string; name_en:string; name_ar:string; lower:number; upper:number; source:string; evidence_level:string; note:string; manufacturer?:string; batch?:string; allowed_above_minutes?:number|null; allowed_below_minutes?:number|null; class_name?:string };
type View = 'icebox'|'import'|'results'|'sources';
type Lang = 'en'|'ar';
const API = 'http://127.0.0.1:8000';

const dict = {
  en: {
    step:'WORKFLOW', subtitle:'Cold chain, understood.',
    icebox:'My Icebox', import:'Import & Analyze', results:'Investigation', lab:'Mathematical Lab', sources:'Sources & Catalog',
    home:'Your cold-chain workspace', intro:'Build your icebox, upload sensor readings, and investigate each product against its own storage policy.',
    products:'Products in this icebox', add:'Add product', custom:'Create custom product', upload:'Continue to CSV upload', noitems:'Your icebox is empty. Start by adding a product.',
    catalog:'Reference product library', batch:'Batch / lot number', remove:'Remove', source:'Policy source', policy:'Storage range', notice:'Reference profiles are not product-specific verified labels. Confirm manufacturer instructions before use.',
    selectcsv:'Upload temperature data', csvhelp:'Import a CSV from your data logger. GapGuard suggests the columns automatically.', demo:'Or try a demo scenario', normal:'Normal readings', excursion:'Excursion (complete data)', missing:'Missing readings',
    mapping:'Check data columns', time:'Date & time', measurement:'Temperature measurement', sensor:'Sensor column (optional)', sensorid:'Sensor ID', advanced:'Advanced import settings', interval:'Sampling minutes override', method:'Interpolation method', analyze:'Analyze temperatures',
    measured:'Measured', estimated:'Estimated', unknown:'Unknown', issues:'Temperature investigations', safe:'No out-of-range readings observed', review:'Review required',
    exposure:'Modeled exposure', severity:'Degree-minutes', gaps:'Data gaps', chart:'Temperature timeline', none:'No analysis yet. Upload a CSV to begin.', explain:'Mathematics behind every decision',
    caution:'These results are decision-support evidence, not proof of medicine viability.', download:'Download full PDF report', customName:'Product name', lower:'Lower limit (°C)', upper:'Upper limit (°C)', ref:'Manufacturer policy URL / reference',
    addbox:'Add to icebox', summary:'Review every product against its own policy', error:'Could not complete analysis', status:'Analysis status', footer:'MATH 301 • From Equations to Innovation', verified:'Policy verification level',
    allowedAbove:'Allowed minutes above upper limit', allowedBelow:'Allowed minutes below lower limit', manufacturer:'Manufacturer / company', className:'Class',
    technical:'Technical explanation', sourcesTitle:'Sources & product evidence', libraryTitle:'Reference product library', official:'Official sources',
    equation:'Equation', use:'Use in GapGuard', compliance:'Configured allowance review', actual:'Actual minutes', allowed:'Allowed minutes', result:'Result', noAllowance:'No configured allowed-duration rule for this product.',
    reportDiagram:'Workflow diagram', productSource:'Product policy source', productEvidence:'Evidence level', batchSummary:'Icebox summary', addCustomHint:'Use this when you have a new medicine policy or manufacturer reference.',
  },
  ar: {
    step:'خطوات العمل', subtitle:'سلسلة تبريد أكثر وضوحًا.',
    icebox:'صندوق الأدوية', import:'رفع وتحليل البيانات', results:'نتائج التحقيق', lab:'المعمل الرياضي', sources:'المصادر والكتالوج',
    home:'مساحة متابعة سلسلة التبريد', intro:'أضف المنتجات داخل صندوق التبريد، ثم ارفع ملف الحرارة، وسيحلل البرنامج كل منتج حسب شروط تخزينه.',
    products:'المنتجات داخل الصندوق', add:'إضافة منتج', custom:'إنشاء منتج مخصص', upload:'متابعة لرفع CSV', noitems:'الصندوق فارغ، أضف منتجًا لتبدأ.',
    catalog:'مكتبة المنتجات المرجعية', batch:'رقم التشغيلة', remove:'حذف', source:'مصدر سياسة التخزين', policy:'نطاق التخزين', notice:'الملفات المرجعية ليست بديلًا عن النشرة الأصلية أو تعليمات الشركة المصنعة.',
    selectcsv:'ارفع قراءات الحرارة', csvhelp:'ارفع ملف CSV من جهاز تسجيل الحرارة، وسيقترح البرنامج الأعمدة المناسبة تلقائيًا.', demo:'أو جرب سيناريو جاهز', normal:'قراءات طبيعية', excursion:'تجاوز بدون فقد بيانات', missing:'قراءات مفقودة',
    mapping:'راجع أعمدة البيانات', time:'عمود التاريخ والوقت', measurement:'عمود درجة الحرارة', sensor:'عمود الحساس (اختياري)', sensorid:'معرّف الحساس', advanced:'إعدادات الاستيراد المتقدمة', interval:'الفاصل بالدقائق (اختياري)', method:'طريقة الاستيفاء العددي', analyze:'تحليل درجات الحرارة',
    measured:'قراءة مسجلة', estimated:'قراءة مقدرة', unknown:'غير معروف', issues:'تحقيقات التعرض الحراري', safe:'لا توجد قراءات مسجلة خارج النطاق', review:'تحتاج مراجعة',
    exposure:'مدة التعرض المقدرة', severity:'شدة التعرض (درجة×دقيقة)', gaps:'فجوات البيانات', chart:'الخط الزمني لدرجة الحرارة', none:'لا يوجد تحليل بعد. ارفع ملف CSV للبدء.', explain:'الرياضيات وراء كل قرار',
    caution:'النتائج للمساعدة في المراجعة وليست شهادة بصلاحية الدواء.', download:'تحميل التقرير الكامل PDF', customName:'اسم المنتج', lower:'الحد الأدنى (°C)', upper:'الحد الأعلى (°C)', ref:'رابط النشرة أو مرجع السياسة',
    addbox:'إضافة للصندوق', summary:'مراجعة كل منتج وفقًا لحدوده الخاصة', error:'تعذر إجراء التحليل', status:'حالة التحليل', footer:'MATH 301 • من المعادلات إلى الابتكار', verified:'مستوى التوثيق',
    allowedAbove:'الحد المسموح فوق الدرجة العليا (بالدقائق)', allowedBelow:'الحد المسموح تحت الدرجة الدنيا (بالدقائق)', manufacturer:'الشركة المصنعة', className:'الفئة',
    technical:'شرح تقني', sourcesTitle:'المصادر وأدلة المنتجات', libraryTitle:'مكتبة المنتجات المرجعية', official:'المصادر الرسمية',
    equation:'المعادلة', use:'الدور داخل GapGuard', compliance:'مراجعة المدة المسموح بها', actual:'المدة الفعلية', allowed:'المدة المسموح بها', result:'النتيجة', noAllowance:'لا توجد مدة مسموح بها معرفة لهذا المنتج.',
    reportDiagram:'مخطط سير العمل', productSource:'مصدر سياسة المنتج', productEvidence:'مستوى التوثيق', batchSummary:'ملخص الصندوق', addCustomHint:'استخدم هذا الخيار عندما يكون لديك دواء جديد أو سياسة تخزين خاصة به.',
  }
};

function App(){
  const [lang,setLang]=useState<Lang>('en');
  const [view,setView]=useState<View>('icebox');
  const [catalog,setCatalog]=useState<Product[]>([]);
  const [sourcesData,setSourcesData]=useState<any>(null);
  const [box,setBox]=useState<Product[]>([]);
  const [selected,setSelected]=useState('hepa');
  const [showCustom,setShowCustom]=useState(false);
  const [custom,setCustom]=useState<Product>({id:'custom-'+Date.now(),name_en:'',name_ar:'',lower:2,upper:8,source:'',evidence_level:'USER_DEFINED',note:'User-defined profile.',manufacturer:'',batch:'',allowed_above_minutes:null,allowed_below_minutes:null,class_name:'Custom'});
  const [batch,setBatch]=useState('');
  const [manufacturer,setManufacturer]=useState('');
  const [allowedAbove,setAllowedAbove]=useState('');
  const [allowedBelow,setAllowedBelow]=useState('');
  const [file,setFile]=useState<File|null>(null);
  const [preview,setPreview]=useState<any>(null);
  const [mapping,setMapping]=useState<any>({});
  const [advanced,setAdvanced]=useState(false);
  const [loading,setLoading]=useState(false);
  const [error,setError]=useState('');
  const [result,setResult]=useState<any>(null);
  const [active,setActive]=useState(0);
  const t=(dict as any)[lang]; const ar=lang==='ar';

  useEffect(()=>{
    fetch(API+'/api/catalog').then(r=>r.json()).then(d=>{setCatalog(d.products); if(d.products?.length) setSelected(d.products[0].id)}).catch(()=>setError('Start the FastAPI backend on port 8000.'));
    fetch(API+'/api/sources').then(r=>r.json()).then(setSourcesData).catch(()=>{});
  },[]);

  const label=(p:Product)=>ar?p.name_ar:p.name_en;
  const selectedProduct = useMemo(()=>catalog.find((x)=>x.id===selected),[catalog,selected]);

  const chooseFile = async (f:File)=>{
    setFile(f); setResult(null); setError(''); setPreview(null);
    try{
      const fd=new FormData(); fd.append('file',f);
      const r=await fetch(API+'/api/preview',{method:'POST',body:fd});
      const data=await r.json(); if(!r.ok) throw Error(data.detail||'CSV error');
      setPreview(data);
      setMapping({ timestamp_column:data.hints.timestamp||data.columns[0], value_column:data.hints.value||data.columns[1], sensor_column:'', sensor_id:'', method:'Newton divided differences', max_gap:5, context:2, expected_minutes:'' });
    }catch(e:any){ setError(e.message); }
  };

  const demo=async(name:string)=>{
    try{
      const r=await fetch(API+'/api/demo/'+name); if(!r.ok) throw Error('Demo unavailable');
      const blob=await r.blob(); await chooseFile(new File([blob],`${name}.csv`,{type:'text/csv'}));
    }catch(e:any){ setError(e.message); }
  };

  const addSelectedProduct=()=>{
    if(!selectedProduct) return;
    const item:Product={...selectedProduct,batch,manufacturer,allowed_above_minutes:allowedAbove?Number(allowedAbove):null,allowed_below_minutes:allowedBelow?Number(allowedBelow):null};
    setBox(prev=>[...prev,item]); setBatch(''); setManufacturer(''); setAllowedAbove(''); setAllowedBelow('');
  };

  const addCustom=()=>{
    if(!custom.name_en.trim()) return;
    setBox(prev=>[...prev,{...custom,id:'custom-'+Date.now(),batch:custom.batch||'',manufacturer:custom.manufacturer||''}]);
    setCustom({id:'custom-'+Date.now(),name_en:'',name_ar:'',lower:2,upper:8,source:'',evidence_level:'USER_DEFINED',note:'User-defined profile.',manufacturer:'',batch:'',allowed_above_minutes:null,allowed_below_minutes:null,class_name:'Custom'});
    setShowCustom(false);
  };

  const removeFromBox=(idx:number)=>setBox(box.filter((_,i)=>i!==idx));

  const run = async ()=>{
    if(!file || box.length===0) return;
    setLoading(true); setError('');
    try{
      const fd=new FormData(); fd.append('file',file);
      fd.append('mapping',JSON.stringify({...mapping, expected_minutes:mapping.expected_minutes?Number(mapping.expected_minutes):null, sensor_column:mapping.sensor_column||null, sensor_id:mapping.sensor_id||null, products:box}));
      const r=await fetch(API+'/api/analyze',{method:'POST',body:fd}); const data=await r.json();
      if(!r.ok) throw Error(typeof data.detail==='string'?data.detail:JSON.stringify(data.detail));
      setResult(data); setActive(0); setView('results');
    }catch(e:any){ setError(e.message); } finally { setLoading(false); }
  };

  const downloadReport=async()=>{
    if(!result) return;
    try{
      const r=await fetch(API+'/api/report',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({analysis:result,title:'GapGuard Pharma Evidence Report'})});
      if(!r.ok) throw Error('PDF export failed');
      const u=URL.createObjectURL(await r.blob()); const a=document.createElement('a'); a.href=u; a.download='gapguard-pharma-evidence.pdf'; a.click(); URL.revokeObjectURL(u);
    }catch(e:any){ setError(e.message); }
  };

  const nav=[{key:'icebox',icon:Archive,text:t.icebox},{key:'import',icon:FileUp,text:t.import},{key:'results',icon:ClipboardList,text:t.results},{key:'sources',icon:BookOpen,text:t.sources}] as const;

  const currentAssessment = result?.assessments?.[active];

  return <div className={'app '+(ar?'rtl':'')} dir={ar?'rtl':'ltr'}>
    <aside className="sidebar">
      <div className="brand"><span className="brandmark"><Activity size={25}/></span><span><b>GapGuard<span className="accent">.</span></b><small>PHARMA INTELLIGENCE</small></span></div>
      <div className="sidelabel">{t.step}</div>
      <nav>{nav.map(n=><button key={n.key} onClick={()=>setView(n.key)} className={'navitem '+(view===n.key?'on':'')}><n.icon size={19}/><span>{n.text}</span>{view===n.key&&<span className="navdot"/>}</button>)}</nav>
      <div className="sidebarbottom"><div className="smallcard"><ShieldCheck size={20}/><p>{t.notice}</p></div><small>{t.footer}</small></div>
    </aside>
    <main>
      <header className="topbar"><div className="breadcrumb">GapGuard <span>/</span> {nav.find(n=>n.key===view)?.text}</div><button className="language" onClick={()=>setLang(ar?'en':'ar')}><Globe2 size={17}/>{ar?'English':'العربية'}</button></header>
      <div className="content">
        <div className="heading"><div><div className="eyebrow">GAPGUARD PHARMA <span className="greenpoint">●</span> NUMERICAL INTELLIGENCE</div><h1>{view==='icebox'?t.home:view==='import'?t.selectcsv:view==='results'?t.issues:t.sourcesTitle}</h1><p>{view==='icebox'?t.intro:view==='import'?t.csvhelp:view==='results'?t.summary:'Official sources and product-specific storage conditions'}</p></div><div className="stepbadge">{Math.max(1,nav.findIndex(n=>n.key===view)+1)} / {nav.length}</div></div>
        {error&&<div className="alert error"><CircleAlert size={18}/>{error}<button onClick={()=>setError('')}>×</button></div>}

        {view==='icebox'&&<div className="twocol">
          <section className="panel">
            <div className="paneltitle"><div><PackagePlus size={21}/><h2>{t.add}</h2></div><span className="hint">01</span></div>
            <label>{t.catalog}</label>
            <select value={selected} onChange={e=>setSelected(e.target.value)}>{catalog.filter(p=>p.id!=='custom').map(p=><option key={p.id} value={p.id}>{label(p)}</option>)}</select>
            {selectedProduct&&<div className="profilepreview">
              <div className="profileline"><span>{t.policy}</span><strong>{selectedProduct.lower} → {selectedProduct.upper} °C</strong></div>
              <div className="profileline"><span>{t.verified}</span><span className="tag amber">{selectedProduct.evidence_level}</span></div>
              <div className="profileline"><span>{t.source}</span><a href={selectedProduct.source} target="_blank" rel="noreferrer" className="linkish">{selectedProduct.source.replace('https://','')}</a></div>
              <small>{selectedProduct.note}</small>
            </div>}
            <div className="twoval">
              <div><label>{t.batch}</label><input value={batch} onChange={e=>setBatch(e.target.value)} placeholder="e.g. VAX-2026-001"/></div>
              <div><label>{t.manufacturer}</label><input value={manufacturer} onChange={e=>setManufacturer(e.target.value)} placeholder="e.g. GSK / Pfizer"/></div>
            </div>
            <div className="twoval">
              <div><label>{t.allowedAbove}</label><input type="number" value={allowedAbove} onChange={e=>setAllowedAbove(e.target.value)} placeholder="Optional"/></div>
              <div><label>{t.allowedBelow}</label><input type="number" value={allowedBelow} onChange={e=>setAllowedBelow(e.target.value)} placeholder="Optional"/></div>
            </div>
            <button className="primary full" onClick={addSelectedProduct}><Plus size={18}/>{t.addbox}</button>
            <button className="linkbtn" onClick={()=>setShowCustom(!showCustom)}>{showCustom?'− ':'+ '}{t.custom}</button>
            {showCustom&&<div className="customform">
              <small className="hint blockhint">{t.addCustomHint}</small>
              <div className="twoval"><div><label>{t.customName} (EN)</label><input value={custom.name_en||''} onChange={e=>setCustom({...custom,name_en:e.target.value})}/></div><div><label>{t.customName} (AR)</label><input value={custom.name_ar||''} onChange={e=>setCustom({...custom,name_ar:e.target.value})}/></div></div>
              <div className="twoval"><div><label>{t.lower}</label><input type="number" value={custom.lower} onChange={e=>setCustom({...custom,lower:Number(e.target.value)})}/></div><div><label>{t.upper}</label><input type="number" value={custom.upper} onChange={e=>setCustom({...custom,upper:Number(e.target.value)})}/></div></div>
              <div className="twoval"><div><label>{t.batch}</label><input value={custom.batch||''} onChange={e=>setCustom({...custom,batch:e.target.value})}/></div><div><label>{t.manufacturer}</label><input value={custom.manufacturer||''} onChange={e=>setCustom({...custom,manufacturer:e.target.value})}/></div></div>
              <div className="twoval"><div><label>{t.allowedAbove}</label><input type="number" value={custom.allowed_above_minutes??''} onChange={e=>setCustom({...custom,allowed_above_minutes:e.target.value?Number(e.target.value):null})}/></div><div><label>{t.allowedBelow}</label><input type="number" value={custom.allowed_below_minutes??''} onChange={e=>setCustom({...custom,allowed_below_minutes:e.target.value?Number(e.target.value):null})}/></div></div>
              <label>{t.ref}</label><input value={custom.source||''} onChange={e=>setCustom({...custom,source:e.target.value})} placeholder="https://..."/>
              <button className="primary full" onClick={addCustom}>{t.addbox}</button>
            </div>}
          </section>
          <section className="panel">
            <div className="paneltitle"><div><Archive size={21}/><h2>{t.products}</h2></div><span className="count">{box.length}</span></div>
            {box.length===0?<div className="emptystate"><Archive size={38}/><p>{t.noitems}</p></div>:<div className="basket">{box.map((p,i)=><div key={i} className="basketrow"><div className="vial"><BarChart3 size={18}/></div><div className="basketinfo"><strong>{label(p)}</strong><small>{p.lower} to {p.upper} °C · {p.batch||'No batch'} · {p.manufacturer||'—'}</small><small>{(p.allowed_above_minutes!=null||p.allowed_below_minutes!=null)?`${t.allowedAbove}: ${p.allowed_above_minutes??'—'} | ${t.allowedBelow}: ${p.allowed_below_minutes??'—'}`:t.noAllowance}</small></div><button className="iconbtn" onClick={()=>removeFromBox(i)}><Trash2 size={18}/></button></div>)}</div>}
            <div className="panelbottom"><button className="primary full" disabled={box.length===0} onClick={()=>setView('import')}>{t.upload}<ArrowRight size={18}/></button></div>
          </section>
        </div>}

        {view==='import'&&<div className="twocol">
          <section className="panel">
            <div className="paneltitle"><div><UploadCloud size={21}/><h2>{t.selectcsv}</h2></div><span className="hint">02</span></div>
            <label className="dropzone"><UploadCloud size={30}/><strong>{file?file.name:t.selectcsv}</strong><small>{file?`${(file.size/1024).toFixed(1)} KB`:t.csvhelp}</small><input type="file" accept=".csv,text/csv" onChange={e=>e.target.files&&chooseFile(e.target.files[0])}/></label>
            <div className="demoarea"><span>{t.demo}</span><div className="demobuttons"><button onClick={()=>demo('normal')}>{t.normal}</button><button onClick={()=>demo('excursion')}>{t.excursion}</button><button onClick={()=>demo('missing')}>{t.missing}</button></div></div>
            {preview&&<div className="previewtable"><table><thead><tr>{preview.columns.map((c:string)=><th key={c}>{c}</th>)}</tr></thead><tbody>{preview.preview.map((row:any,i:number)=><tr key={i}>{preview.columns.map((c:string)=><td key={c}>{String(row[c]??'')}</td>)}</tr>)}</tbody></table></div>}
          </section>
          <section className="panel">
            <div className="paneltitle"><div><ClipboardList size={21}/><h2>{t.mapping}</h2></div><span className="hint">03</span></div>
            {!preview?<div className="emptystate"><FileUp size={36}/><p>{t.none}</p></div>:<>
              <label>{t.time}</label><select value={mapping.timestamp_column||''} onChange={e=>setMapping({...mapping,timestamp_column:e.target.value})}>{preview.columns.map((c:string)=><option key={c}>{c}</option>)}</select>
              <label>{t.measurement}</label><select value={mapping.value_column||''} onChange={e=>setMapping({...mapping,value_column:e.target.value})}>{preview.columns.map((c:string)=><option key={c}>{c}</option>)}</select>
              <button className="disclosure" onClick={()=>setAdvanced(!advanced)}><ChevronDown className={advanced?'flipped':''} size={16}/>{t.advanced}</button>
              {advanced&&<div className="advanced"><label>{t.sensor}</label><select value={mapping.sensor_column||''} onChange={e=>setMapping({...mapping,sensor_column:e.target.value})}><option value="">—</option>{preview.columns.map((c:string)=><option key={c}>{c}</option>)}</select><label>{t.sensorid}</label><input value={mapping.sensor_id||''} onChange={e=>setMapping({...mapping,sensor_id:e.target.value})}/><div className="twoval"><div><label>{t.interval}</label><input type="number" value={mapping.expected_minutes||''} onChange={e=>setMapping({...mapping,expected_minutes:e.target.value})}/></div><div><label>{t.method}</label><select value={mapping.method||''} onChange={e=>setMapping({...mapping,method:e.target.value})}><option>Newton divided differences</option><option>Lagrange</option><option>Linear interpolation</option></select></div></div></div>}
              <button className="primary full" disabled={!file||box.length===0||loading} onClick={run}>{loading?'…':t.analyze}</button>
            </>}
          </section>
        </div>}

        {view==='results'&&<>
          {!result?<div className="panel"><div className="emptystate"><ClipboardList size={36}/><p>{t.none}</p></div></div>:<>
            <div className="producttabs">{result.assessments.map((a:any,i:number)=><button key={i} className={i===active?'selected':''} onClick={()=>setActive(i)}>{lang==='ar'?a.item.name_ar:a.item.name_en}</button>)}</div>
            <section className="panel">
              <div className="paneltitle"><div><ClipboardList size={21}/><h2>{lang==='ar'?currentAssessment.item.name_ar:currentAssessment.item.name_en}</h2></div><button className="secondary" onClick={downloadReport}><FileDown size={16}/>{t.download}</button></div>
              <div className="statusline"><div className="statusicon"><ShieldCheck size={22}/></div><div><div className="minor">{t.status}</div><h2>{currentAssessment.result.status}</h2><small>{currentAssessment.result.policy.note}</small></div><span className="tag green">{currentAssessment.result.policy.evidence_level}</span></div>
              <div className="metrics">
                <div className="metric"><span>{t.exposure}</span><strong>{currentAssessment.result.modeled_exposure_minutes.toFixed(2)} <small>min</small></strong></div>
                <div className="metric"><span>{t.severity}</span><strong>{currentAssessment.result.modeled_degree_minutes.toFixed(2)}</strong></div>
                <div className="metric"><span>{t.gaps}</span><strong>{currentAssessment.result.gap_count}</strong></div>
                <div className="metric"><span>{t.policy}</span><strong>{currentAssessment.item.lower}–{currentAssessment.item.upper}<small> °C</small></strong></div>
              </div>
              <div className="alert info"><Info size={18}/>{ar?'مدة التعرض المعروضة تقديرية. لا توجد مدة مسموحة تلقائية لمعظم المنتجات؛ تحقق من النشرة الدقيقة والحالة الصيدلية ومدة التعرض السابقة. بعض تعليمات التخزين (مثل SHINGRIX prefilled syringe) لها درجة حرارة وزمن مشروطان معًا.':'Exposure minutes are modeled, NOT an automatic permitted duration. Most products have no verified generic allowance. A temperature-and-time-specific window (e.g., SHINGRIX prefilled syringe) must be checked with its exact presentation and prior handling history.'}</div>
              <div className="metrics three">
                <div className="metric"><span>{t.batch}</span><strong>{currentAssessment.item.batch||'—'}</strong></div>
                <div className="metric"><span>{t.manufacturer}</span><strong>{currentAssessment.item.manufacturer||'—'}</strong></div>
                <div className="metric"><span>{t.productSource}</span><strong><a className="linkish" href={currentAssessment.result.policy.source} target="_blank" rel="noreferrer">{currentAssessment.result.policy.source.replace('https://','')}</a></strong></div>
              </div>
            </section>
            <section className="panel"><div className="paneltitle"><div><BarChart3 size={21}/><h2>{t.chart}</h2></div><span className="hint">{result.method}</span></div>
              <div className="chart"><ResponsiveContainer width="100%" height="100%"><LineChart data={result.timeline}><CartesianGrid stroke="#edf1f5" vertical={false}/><XAxis dataKey="timestamp" tick={{fontSize:11}} minTickGap={18}/><YAxis tick={{fontSize:11}}/><Tooltip/><Legend/><ReferenceLine y={currentAssessment.item.upper} stroke="#d94f4f" strokeDasharray="6 4"/><ReferenceLine y={currentAssessment.item.lower} stroke="#4677d9" strokeDasharray="6 4"/><Line type="monotone" dataKey="measured" stroke="#16a085" strokeWidth={2.8} dot={false} name={t.measured}/><Line type="monotone" dataKey="estimated" stroke="#f39c12" strokeWidth={2.6} strokeDasharray="5 4" dot={false} name={t.estimated}/></LineChart></ResponsiveContainer></div>
            </section>
            <section className="panel">
              <div className="paneltitle"><div><ShieldCheck size={21}/><h2>{t.compliance}</h2></div></div>
              {currentAssessment.result.allowance_review?.length?
                <div className="tablewrap"><table><thead><tr><th>Type</th><th>{t.allowed}</th><th>{t.actual}</th><th>{t.result}</th></tr></thead><tbody>{currentAssessment.result.allowance_review.map((row:any,i:number)=><tr key={i}><td>{row.kind}</td><td>{row.allowed_minutes.toFixed(2)}</td><td>{row.actual_minutes.toFixed(2)}</td><td>{row.status}</td></tr>)}</tbody></table></div>
                :<div className="alert info"><Info size={16}/>{t.noAllowance}</div>}
            </section>
            <section className="panel">
              <div className="paneltitle"><div><ClipboardList size={21}/><h2>{t.issues}</h2></div></div>
              {currentAssessment.result.episodes.length?
                <div className="tablewrap"><table><thead><tr><th>Type</th><th>Start</th><th>End</th><th>Minutes</th><th>°C·min</th><th>Estimated</th></tr></thead><tbody>{currentAssessment.result.episodes.map((e:any,i:number)=><tr key={i}><td>{e.kind}</td><td>{e.start}</td><td>{e.end}</td><td>{e.duration_min.toFixed(2)}</td><td>{e.degree_minutes.toFixed(2)}</td><td>{String(e.estimated)}</td></tr>)}</tbody></table></div>
                :<div className="emptystate"><ShieldCheck size={32}/><p>{t.safe}</p></div>}
            </section>
            <div className="alert info"><Info size={18}/>{t.caution}</div>
          </>}
        </>}

        {view==='sources'&&<div className="panel">
          <div className="paneltitle"><div><BookOpen size={21}/><h2>{t.sourcesTitle}</h2></div></div>
          <section className="panel nested"><div className="paneltitle"><div><Archive size={21}/><h2>{t.libraryTitle}</h2></div></div><div className="tablewrap"><table><thead><tr><th>{t.className}</th><th>{lang==='ar'?'الاسم':'Name'}</th><th>{t.policy}</th><th>{t.productEvidence}</th><th>{t.productSource}</th></tr></thead><tbody>{(sourcesData?.catalog||[]).filter((p:any)=>p.id!=='custom').map((p:any)=><tr key={p.id}><td>{p.class_name||'—'}</td><td>{lang==='ar'?p.name_ar:p.name_en}</td><td>{p.lower} to {p.upper} °C</td><td>{p.evidence_level}</td><td><a className="linkish" href={p.source} target="_blank" rel="noreferrer">{p.source.replace('https://','')}</a></td></tr>)}</tbody></table></div></section>
          <section className="panel nested"><div className="paneltitle"><div><Link2 size={21}/><h2>{t.official}</h2></div></div><div className="sourceList">{(sourcesData?.official_sources||[]).map((s:any,i:number)=><a key={i} href={s.url} target="_blank" rel="noreferrer" className="sourceItem"><strong>{s.title}</strong><small>{s.url}</small></a>)}</div></section>
          {(sourcesData?.notes||[]).length?<section className="panel nested"><div className="paneltitle"><div><Info size={21}/><h2>Notes</h2></div></div><ul className="notesList">{sourcesData.notes.map((n:string,i:number)=><li key={i}>{n}</li>)}</ul></section>:null}
        </div>}
      </div>
    </main>
  </div>
}

createRoot(document.getElementById('root')!).render(<App/>);
