import { useMemo, useState, useEffect } from 'react';
import { AlertTriangle, CheckCircle2, CircleHelp, Info, ShieldAlert, Sparkles } from 'lucide-react';

type Item = { name: string; explanation: string; allergens?: string[]; percentage: number | null; percentage_label?: string; status: string; amount?: string | null; source?: string | null };
type Mode = 'composition' | 'risks' | 'health';
type PackKind = 'pouch' | 'box' | 'bottle' | 'jar' | 'can' | 'unknown';
const palette = { conflict: '#d94343', warning: '#ed9b22', clear: '#15905a', unknown: '#9aa6a0' };
function signal(item: Item) { return item.status === 'conflict' ? 'conflict' : item.status === 'warning' ? 'warning' : item.status === 'clear' ? 'clear' : 'unknown'; }
function detectPackKind(name = '', category = ''): PackKind {
  const s = `${name} ${category}`.toLowerCase();
  if (/chips|crisps|snack|noodle|pasta|cereal|biscuits?|cookies?|chocolate|frozen|powder|flour|tea bag|pouch/.test(s)) return 'pouch';
  if (/bottle|beverage|drink|juice|water|soda|shampoo|hand.?wash|sauce bottle/.test(s)) return 'bottle';
  if (/jar|spread|jam|peanut butter|pickle/.test(s)) return 'jar';
  if (/can|tin|soda|energy drink/.test(s)) return 'can';
  if (/box|carton|cereal|milk|pack/.test(s)) return 'box';
  return 'unknown';
}
export default function PackageViz({ items, mode, productName, category }: { items: Item[]; mode: string; productName?: string; category?: string }) {
  const [active, setActive] = useState(0);
  useEffect(() => setActive(0), [items]);
  const selected = items[Math.min(active, Math.max(0, items.length - 1))];
  const view = (['composition', 'risks', 'health'].includes(mode) ? mode : 'composition') as Mode;
  const hasPercentages = items.length > 0 && items.every(x => typeof x.percentage === 'number' && Number.isFinite(x.percentage) && x.percentage! >= 0 && x.percentage! <= 100);
  const colors = items.map(x => palette[signal(x)]);
  const kind = detectPackKind(productName, category);
  const label = view === 'risks' ? 'PERSONAL RISK VIEW' : view === 'health' ? 'GENERAL HEALTH VIEW' : 'INGREDIENT COMPOSITION';
  const statusText = (x: Item) => x.status === 'conflict' ? 'Potential conflict' : x.status === 'warning' ? 'Relevant warning' : x.status === 'clear' ? 'No known conflict in available information' : 'Unknown / unverified';
  const visibleItems = items;
  const count = Math.max(visibleItems.length, 1);
  const top = kind === 'unknown' ? 72 : kind === 'bottle' ? 112 : 82;
  const height = kind === 'unknown' ? 245 : kind === 'bottle' ? 205 : 235;
  const rowH = height / count;
  const shortName = (s: string, max = 25) => s.length > max ? `${s.slice(0, max - 1)}…` : s;
  return <div className="viz-layout">
    <div className="pack-stage">
      <div className="package-stage-heading"><span><Sparkles size={17}/> INTERACTIVE PACKAGE</span><small>{items.length} ingredients · {kind === 'unknown' ? 'generic package view' : `${kind} illustration`}</small></div>
      <svg viewBox="0 0 360 410" role="group" aria-label={`${productName || 'Product'} package illustration with selectable ingredient sections`} className="package-svg">
        <defs>
          <linearGradient id="nlPackFill" x1="0" x2="1"><stop offset="0" stopColor="#145c39"/><stop offset=".5" stopColor="#218451"/><stop offset="1" stopColor="#0e4b2d"/></linearGradient>
          <linearGradient id="nlPackShine" x1="0" x2="1"><stop offset="0" stopColor="#fff" stopOpacity=".03"/><stop offset=".5" stopColor="#fff" stopOpacity=".16"/><stop offset="1" stopColor="#fff" stopOpacity=".02"/></linearGradient>
          <filter id="nlPackShadow" x="-30%" y="-20%" width="160%" height="150%"><feDropShadow dx="0" dy="7" stdDeviation="5" floodColor="#17482c" floodOpacity=".18"/></filter>
        </defs>
        {kind === 'pouch' && <><path d="M68 24 L292 24 L304 53 L292 359 Q180 381 68 359 L56 53 Z" fill="url(#nlPackFill)" stroke="#064629" strokeWidth="2" filter="url(#nlPackShadow)"/><path d="M68 24 L292 24 L288 43 L72 43 Z" fill="#d6f0de"/><path d="M63 52 Q180 62 297 52 L288 357 Q180 376 72 357 Z" fill="url(#nlPackShine)"/></>}
        {kind === 'box' && <><rect x="68" y="28" width="224" height="337" rx="9" fill="url(#nlPackFill)" stroke="#064629" strokeWidth="2" filter="url(#nlPackShadow)"/><path d="M68 28 L180 12 L292 28 Z" fill="#b9dfc4" stroke="#064629" strokeWidth="2"/></>}
        {kind === 'bottle' && <><path d="M148 24 H212 V63 Q212 78 233 92 Q258 108 258 139 V350 Q258 370 238 370 H122 Q102 370 102 350 V139 Q102 108 127 92 Q148 78 148 63 Z" fill="url(#nlPackFill)" stroke="#064629" strokeWidth="2" filter="url(#nlPackShadow)"/><rect x="151" y="12" width="58" height="22" rx="4" fill="#d6f0de" stroke="#064629" strokeWidth="2"/></>}
        {kind === 'jar' && <><rect x="120" y="35" width="120" height="27" rx="5" fill="#d6f0de" stroke="#064629" strokeWidth="2"/><path d="M113 62 Q105 62 105 82 V345 Q105 365 125 365 H235 Q255 365 255 345 V82 Q255 62 247 62 Z" fill="url(#nlPackFill)" stroke="#064629" strokeWidth="2" filter="url(#nlPackShadow)"/></>}
        {kind === 'can' && <><rect x="105" y="25" width="150" height="340" rx="24" fill="url(#nlPackFill)" stroke="#064629" strokeWidth="2" filter="url(#nlPackShadow)"/><ellipse cx="180" cy="31" rx="74" ry="9" fill="#d6f0de" stroke="#064629" strokeWidth="2"/><ellipse cx="180" cy="359" rx="74" ry="9" fill="#d6f0de" stroke="#064629" strokeWidth="2"/></>}
        {kind === 'unknown' && <><rect x="62" y="52" width="236" height="305" rx="20" fill="#f2f6f2" stroke="#8fa899" strokeWidth="2" strokeDasharray="7 5" filter="url(#nlPackShadow)"/><text x="180" y="82" textAnchor="middle" fontSize="14" fill="#285a3c" fontWeight="800">{shortName(productName || 'PRODUCT LABEL', 24).toUpperCase()}</text><text x="180" y="101" textAnchor="middle" fontSize="11" fill="#577565">Generic package view</text></>}
        {kind !== 'unknown' && <><text x="180" y={kind === 'bottle' ? 113 : 68} fill="#e9f8ed" textAnchor="middle" fontSize="10" letterSpacing="1.2">NUTRILENS • LABEL VIEW</text><text x="180" y={kind === 'bottle' ? 137 : 91} fill="#fff" textAnchor="middle" fontSize="15" fontWeight="800">{shortName((productName || 'PRODUCT').toUpperCase(), 22)}</text></>}
        {visibleItems.map((it, i) => {
          const y = top + i * rowH; const h = rowH; const c = colors[i]; const pct = it.percentage;
          const x = kind === 'unknown' ? 78 : kind === 'bottle' ? 112 : kind === 'jar' ? 114 : kind === 'can' ? 111 : kind === 'box' ? 75 : 63;
          const w = kind === 'unknown' ? 204 : kind === 'bottle' ? 136 : kind === 'jar' ? 132 : kind === 'can' ? 138 : kind === 'box' ? 210 : 234;
          const textColor = kind === 'unknown' ? '#243c2c' : '#fff';
          return <g key={`${it.name}-${i}`} onClick={() => setActive(i)} onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setActive(i); } }} role="button" tabIndex={0} aria-pressed={active === i} aria-label={`Inspect ${it.name}`} style={{ cursor: 'pointer', outline: 'none' }}>
            <rect x={x} y={y} width={w} height={Math.max(h - 2, 14)} rx={kind === 'unknown' ? 6 : 3} fill={c} fillOpacity={view === 'composition' ? '.94' : signal(it) === 'unknown' ? '.62' : '.98'} stroke={active === i ? '#f4d35e' : '#ffffffbd'} strokeWidth={active === i ? 3 : 1.2}/>
            {active === i && <rect x={x + 3} y={y + 3} width={w - 6} height={Math.max(h - 8, 8)} rx="3" fill="none" stroke={kind === 'unknown' ? '#285a3c' : '#fff'} strokeWidth="1.5"/>}
            <text x={180} y={y + h * .43} textAnchor="middle" fontSize={Math.min(14, Math.max(10, h * .27))} fill={textColor} fontWeight="800">{shortName(it.name, kind === 'unknown' ? 27 : 29)}</text>
            <text x={180} y={y + h * .72} textAnchor="middle" fontSize={Math.min(12, Math.max(9, h * .23))} fill={textColor} fontWeight="700">{pct != null && Number.isFinite(pct) ? `${pct}%` : (it.amount || 'Percentage unavailable')}</text>
          </g>;
        })}
        {items.length === 0 && <text x="180" y="215" textAnchor="middle" fontSize="15" fill="#647b6b">No ingredients detected</text>}
      </svg>
      <div className="package-data-note"><Info size={16}/><span>{hasPercentages ? 'Quantities are supplied in the source data; verify them against the label.' : 'Qualitative view only. No ingredient proportions are inferred from ingredient order.'}</span></div>
      <div className="legend"><span><i className="dot red"/> Conflict</span><span><i className="dot orange"/> Warning</span><span><i className="dot green"/> No known conflict</span><span><i className="dot gray"/> Unknown</span></div>
      <small className="muted">Illustrative package shape selected from the product name/category. Not a photo of the scanned product.</small>
    </div>
    <div className="ingredient-panel">
      <div className="eyebrow">{label}</div><h3>{selected?.name || 'Ingredient details'}</h3>
      <div className={`ingredient-status status-${selected ? signal(selected) : 'unknown'}`}>{selected && signal(selected) === 'clear' ? <CheckCircle2 size={18}/> : selected && signal(selected) === 'conflict' ? <ShieldAlert size={18}/> : selected && signal(selected) === 'warning' ? <AlertTriangle size={18}/> : <CircleHelp size={18}/>}<span>{selected ? statusText(selected) : 'No ingredient selected'}</span></div>
      <p>{selected?.explanation || 'Add or correct the ingredient list during OCR review to see simplified explanations.'}</p>
      <div className="data-row"><span>Quantity / share</span><b>{selected?.percentage != null && Number.isFinite(selected.percentage) ? `${selected.percentage}%` : selected?.amount || 'Percentage unavailable'}</b></div>
      <div className="data-row"><span>Evidence source</span><b>{selected?.source || (selected?.percentage != null ? 'Provided analysis data' : 'Not verified')}</b></div>
      {selected?.allergens?.length ? <div className="alert alert-red"><AlertTriangle size={18}/><span>Allergen terms detected: {selected.allergens.join(', ')}. Verify the full label and cross-contact statement.</span></div> : null}
      {view === 'risks' && <div className="viz-context"><ShieldAlert size={18}/><span>Personal-risk view compares available ingredient text with your selected restrictions. Missing text is not proof of safety.</span></div>}
      {view === 'health' && <div className="viz-context"><Info size={18}/><span>Health warnings are shown only when supported by available ingredient or nutrition evidence.</span></div>}
      <div className="ingredient-list-heading">All ingredients <small>· select to inspect ({items.length})</small></div>
      <div className="ingredient-list">{items.map((x, i) => <button className={`ingredient-row ${active === i ? 'selected' : ''}`} key={`${x.name}-${i}`} onClick={() => setActive(i)} aria-pressed={active === i}><i className="dot" style={{ background: palette[signal(x)] }}/><span>{x.name}</span><small>{x.percentage != null && Number.isFinite(x.percentage) ? `${x.percentage}%` : 'Amount unavailable'}</small></button>)}</div>
    </div>
  </div>;
}
