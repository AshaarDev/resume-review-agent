import { Fragment, useEffect, useId, useLayoutEffect, useRef, useState } from 'react';
import { API_BASE_URL, artifactUrl } from '../services/api';
import './ResumeBuilder.css';

type BuiltInSection = 'contact' | 'experiences' | 'education' | 'projects' | 'skill_groups';
type Section = BuiltInSection | `custom:${string}`;
type Collection = Exclude<Section, 'contact'>;
interface Entry { id: string; name: string; title: string; location: string; dates: string; stack: string; coursework: string; points: string[]; skills: string[] }
interface CustomSection { id: string; name: string; entries: Entry[] }
interface Draft { full_name: string; email: string; phone: string; location: string; experiences: Entry[]; education: Entry[]; projects: Entry[]; skill_groups: Entry[]; custom_sections: CustomSection[]; section_order: string[] }
const STORAGE = 'resumeai.manual-builder.v1';
const sections: { key: Section; name: string; hint: string }[] = [
  { key: 'contact', name: 'Personal details', hint: 'Start with your resume header.' },
  { key: 'experiences', name: 'Experience', hint: 'Your roles, responsibilities, and achievements.' },
  { key: 'education', name: 'Education', hint: 'Schools, degrees, and relevant coursework.' },
  { key: 'projects', name: 'Projects', hint: 'What you built, how you built it, and why it matters.' },
  { key: 'skill_groups', name: 'Skills', hint: 'Organize your skills into clear, scannable groups.' },
];
const emptyDraft = (): Draft => ({ full_name: '', email: '', phone: '', location: '', experiences: [], education: [], projects: [], skill_groups: [], custom_sections: [], section_order: [] });
const newEntry = (): Entry => ({ id: crypto.randomUUID(), name: '', title: '', location: '', dates: '', stack: '', coursework: '', points: [''], skills: [] });
function loadDraft(): Draft {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE) || 'null');
    if (saved && ['full_name', 'email', 'phone', 'location'].every(k => typeof saved[k] === 'string') &&
      ['experiences', 'education', 'projects', 'skill_groups'].every(k => Array.isArray(saved[k]) && saved[k].length <= 12 && saved[k].every((e: Entry) =>
        e && typeof e.id === 'string' && ['name', 'title', 'location', 'dates', 'stack', 'coursework'].every(f => typeof (e as unknown as Record<string, unknown>)[f] === 'string') && Array.isArray(e.points) && e.points.every(p => typeof p === 'string') && Array.isArray(e.skills) && e.skills.every(s => typeof s === 'string')))) {
        const custom = saved.custom_sections ?? [];
        if (!Array.isArray(custom) || custom.length > 8 || !custom.every(c => c && typeof c.id === 'string' && typeof c.name === 'string' && c.name.trim() && c.name.length <= 80 && Array.isArray(c.entries) && c.entries.length <= 12 && c.entries.every((e: Entry) => e && typeof e.id === 'string' && ['name', 'title', 'location', 'dates', 'stack', 'coursework'].every(f => typeof (e as unknown as Record<string, unknown>)[f] === 'string') && Array.isArray(e.points) && e.points.every(p => typeof p === 'string') && Array.isArray(e.skills) && e.skills.every(p => typeof p === 'string')))) return emptyDraft();
        const normalizeEntry = (entry: Entry): Entry => ({
          ...entry,
          coursework: normalizeFormatting(entry.coursework),
          points: entry.points.map(normalizeFormatting),
        });
        return {
          ...saved,
          experiences: saved.experiences.map(normalizeEntry),
          education: saved.education.map(normalizeEntry),
          projects: saved.projects.map(normalizeEntry),
          skill_groups: saved.skill_groups.map(normalizeEntry),
          custom_sections: custom.map((item: CustomSection) => ({
            ...item,
            entries: item.entries.map(normalizeEntry),
          })),
          section_order: Array.isArray(saved.section_order) ? saved.section_order.filter((k: unknown) => typeof k === 'string').slice(0, 12) : [],
        };
      }
  } catch { /* Invalid/unavailable browser storage must not break the editor. */ }
  return emptyDraft();
}

function orderedSections(draft: Draft): string[] {
  const defaults = ['skill_groups', 'experiences', 'projects', 'education', ...draft.custom_sections.map(c => `custom:${c.id}`)];
  return [...new Set([...draft.section_order.filter(k => defaults.includes(k)), ...defaults])];
}
function moved<T>(items: T[], index: number, direction: number): T[] {
  const next = [...items], target = index + direction;
  if (target < 0 || target >= next.length) return next;
  const [item] = next.splice(index, 1);
  next.splice(target, 0, item);
  return next;
}
function formattedText(value: string): React.ReactNode[] {
  function render(source: string, bold = false, italic = false, path = 'root'): React.ReactNode[] {
    const expression = /\*\*\*([\s\S]+?)\*\*\*|\*\*([\s\S]+?)\*\*|\*([\s\S]+?)\*/g;
    const parts: React.ReactNode[] = [];
    let cursor = 0;
    let index = 0;
    const add = (text: string, isBold: boolean, isItalic: boolean) => {
      const key = path + '-' + index++;
      parts.push(isBold && isItalic ? <strong key={key}><em>{text}</em></strong> : isBold ? <strong key={key}>{text}</strong> : isItalic ? <em key={key}>{text}</em> : text);
    };
    for (const match of source.matchAll(expression)) {
      const start = match.index ?? 0;
      if (start > cursor) add(source.slice(cursor, start), bold, italic);
      if (match[1] !== undefined) parts.push(...render(match[1], true, true, path + '-' + index++));
      else if (match[2] !== undefined) parts.push(...render(match[2], true, italic, path + '-' + index++));
      else parts.push(...render(match[3], bold, true, path + '-' + index++));
      cursor = start + match[0].length;
    }
    if (cursor < source.length) add(source.slice(cursor), bold, italic);
    return parts;
  }
  return render(normalizeFormatting(value));
}
function normalizeFormatting(value: string): string {
  return value
    .replace(/(?<!\*)\*{6}(?!\*)([\s\S]+?)(?<!\*)\*{6}(?!\*)/g, '***$1***')
    .replace(/(?<!\*)\*{4}(?!\*)([\s\S]+?)(?<!\*)\*{4}(?!\*)/g, '**$1**');
}
function editorHtml(value: string): string {
  return normalizeFormatting(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\*\*\*([\s\S]+?)\*\*\*/g, '<strong><em>$1</em></strong>')
    .replace(/\*\*([\s\S]+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*([\s\S]+?)\*/g, '<em>$1</em>')
    .replace(/\n/g, '<br>');
}
interface EditorSegment { text: string; bold: boolean; italic: boolean }
function appendEditorSegment(segments: EditorSegment[], text: string, bold: boolean, italic: boolean) {
  if (!text) return;
  const previous = segments.at(-1);
  if (previous && previous.bold === bold && previous.italic === italic) previous.text += text;
  else segments.push({ text, bold, italic });
}
function collectEditorSegments(node: Node, inheritedBold: boolean, inheritedItalic: boolean, segments: EditorSegment[]) {
  if (node.nodeType === Node.TEXT_NODE) {
    appendEditorSegment(segments, node.textContent ?? '', inheritedBold, inheritedItalic);
    return;
  }
  if (!(node instanceof HTMLElement)) return;
  if (node.tagName === 'BR') {
    appendEditorSegment(segments, '\n', false, false);
    return;
  }
  const weight = Number(node.style.fontWeight);
  const bold = inheritedBold || node.tagName === 'B' || node.tagName === 'STRONG' || node.style.fontWeight === 'bold' || weight >= 600;
  const italic = inheritedItalic || node.tagName === 'I' || node.tagName === 'EM' || node.style.fontStyle === 'italic';
  Array.from(node.childNodes).forEach(child => collectEditorSegments(child, bold, italic, segments));
  if ((node.tagName === 'DIV' || node.tagName === 'P') && segments.at(-1)?.text.slice(-1) !== '\n') {
    appendEditorSegment(segments, '\n', false, false);
  }
}
function serializeEditorSegment(segment: EditorSegment): string {
  const marker = segment.bold && segment.italic ? '***' : segment.bold ? '**' : segment.italic ? '*' : '';
  if (!marker) return segment.text;
  return segment.text.split('\n').map(line => {
    const leading = line.match(/^\s*/)?.[0] ?? '';
    const trailing = line.match(/\s*$/)?.[0] ?? '';
    const content = line.slice(leading.length, line.length - trailing.length);
    return content ? leading + marker + content + marker + trailing : line;
  }).join('\n');
}
function editorValue(element: HTMLElement): string {
  const segments: EditorSegment[] = [];
  Array.from(element.childNodes).forEach(node => collectEditorSegments(node, false, false, segments));
  return normalizeFormatting(segments
    .map(serializeEditorSegment)
    .join('')
    .replace(/\u00a0/g, ' ')
    .replace(/\n{3,}/g, '\n\n')
    .replace(/\n$/, ''));
}
function FormattedTextarea({ label, value, onChange, rows = 3, maxLength = 700, placeholder = '' }: { label: string; value: string; onChange: (value: string) => void; rows?: number; maxLength?: number; placeholder?: string }) {
  const id = useId();
  const editor = useRef<HTMLDivElement>(null);
  useLayoutEffect(() => {
    const field = editor.current;
    if (field && editorValue(field) !== value) field.innerHTML = editorHtml(value);
  }, [value]);
  function emitChange() {
    const field = editor.current;
    if (!field) return;
    const next = editorValue(field);
    if (next.length > maxLength) {
      field.innerHTML = editorHtml(value);
      return;
    }
    onChange(next);
  }
  function format(command: 'bold' | 'italic') {
    const field = editor.current;
    if (!field) return;
    field.focus();
    document.execCommand(command, false);
    emitChange();
  }
  return <div className="byo-rich-field">
    <div className="byo-rich-heading"><span id={id}>{label}</span><span>Select text, then format it</span></div>
    <div className="byo-format-toolbar" role="toolbar" aria-label={label + ' formatting'}>
      <button type="button" onMouseDown={event => event.preventDefault()} onClick={() => format('bold')} aria-label="Bold selected text" title="Bold selected text"><strong>B</strong></button>
      <button type="button" onMouseDown={event => event.preventDefault()} onClick={() => format('italic')} aria-label="Italicize selected text" title="Italicize selected text"><em>I</em></button>
    </div>
    <div
      ref={editor}
      className="byo-rich-editor"
      contentEditable
      role="textbox"
      aria-multiline="true"
      aria-labelledby={id}
      data-placeholder={placeholder}
      style={{ minHeight: rows * 1.6 + 1.4 + 'rem' }}
      suppressContentEditableWarning
      onInput={emitChange}
      onKeyDown={event => {
        if ((event.ctrlKey || event.metaKey) && (event.key === 'b' || event.key === 'i')) {
          event.preventDefault();
          format(event.key === 'b' ? 'bold' : 'italic');
        }
      }}
      onPaste={event => {
        event.preventDefault();
        document.execCommand('insertText', false, event.clipboardData.getData('text/plain'));
        emitChange();
      }}
    />
  </div>;
}
function MoveControls({ index, count, label, group, onMove }: { index: number; count: number; label: string; group: string; onMove: (direction: number) => void }) {
  const drag = useRef<{ x: number; y: number; target: number; item: HTMLElement; ghost: HTMLElement | null; indicator: HTMLElement | null } | null>(null);
  function cleanup() {
    const active = drag.current;
    if (active) { active.ghost?.remove(); active.item.classList.remove('byo-is-dragging'); active.indicator?.classList.remove('byo-drop-target'); }
    drag.current = null;
  }
  useEffect(() => cleanup, []);
  return <span className="byo-drag-handle" role="button" tabIndex={count > 1 ? 0 : -1}
    aria-disabled={count < 2} aria-label={`Drag ${label} to reorder. Use arrow keys to move.`}
    title="Drag to reorder / arrow keys" data-sort-group={group} data-sort-index={index}
    onClick={e => { e.preventDefault(); e.stopPropagation(); }}
    onKeyDown={e => {
      const direction = e.key === 'ArrowUp' || e.key === 'ArrowLeft' ? -1 : e.key === 'ArrowDown' || e.key === 'ArrowRight' ? 1 : 0;
      if (direction) { e.preventDefault(); e.stopPropagation(); if (index + direction >= 0 && index + direction < count) onMove(direction); }
    }}
    onPointerDown={e => {
      if (count < 2 || e.button !== 0) return;
      e.preventDefault(); e.stopPropagation();
      const item = e.currentTarget.closest<HTMLElement>('.byo-point, .byo-entry-card, .byo-section-tab');
      if (!item) return;
      cleanup(); drag.current = { x: e.clientX, y: e.clientY, target: index, item, ghost: null, indicator: null };
      e.currentTarget.setPointerCapture(e.pointerId);
    }}
    onPointerMove={e => {
      const active = drag.current;
      if (!active) return;
      if (!active.ghost && Math.hypot(e.clientX - active.x, e.clientY - active.y) < 5) return;
      if (!active.ghost) {
        const rect = active.item.getBoundingClientRect();
        const ghost = active.item.cloneNode(true) as HTMLElement;
        ghost.classList.add('byo-drag-ghost'); ghost.setAttribute('aria-hidden', 'true');
        Object.assign(ghost.style, { width: `${rect.width}px`, height: `${rect.height}px`, left: `${rect.left}px`, top: `${rect.top}px` });
        document.body.appendChild(ghost); active.ghost = ghost; active.item.classList.add('byo-is-dragging');
      }
      active.ghost.style.transform = `translate(${e.clientX - active.x}px, ${e.clientY - active.y}px)`;
      const handles = Array.from(document.querySelectorAll<HTMLElement>('.byo-drag-handle')).filter(h => h.dataset.sortGroup === group && !h.closest('.byo-drag-ghost'));
      let nearest = index, distance = Infinity, indicator: HTMLElement | null = null;
      for (const handle of handles) {
        const item = handle.closest<HTMLElement>('.byo-point, .byo-entry-card, .byo-section-tab');
        if (!item) continue;
        const rect = item.getBoundingClientRect();
        const dx = Math.max(rect.left - e.clientX, 0, e.clientX - rect.right);
        const dy = Math.max(rect.top - e.clientY, 0, e.clientY - rect.bottom);
        const score = Math.hypot(dx, dy);
        if (score < distance) { distance = score; nearest = Number(handle.dataset.sortIndex); indicator = item; }
      }
      active.indicator?.classList.remove('byo-drop-target');
      active.target = nearest; active.indicator = indicator;
      if (nearest !== index) indicator?.classList.add('byo-drop-target');
    }}
    onPointerUp={e => {
      const target = drag.current?.target ?? index;
      cleanup(); if (e.currentTarget.hasPointerCapture(e.pointerId)) e.currentTarget.releasePointerCapture(e.pointerId);
      if (target !== index) onMove(target - index);
    }}
    onPointerCancel={cleanup} onLostPointerCapture={cleanup}
  ><span aria-hidden="true">&#x283F;</span></span>;
}
function ResumePaper({ draft }: { draft: Draft }) {
  const blocks: Record<string, React.ReactNode> = {};
  blocks.education = draft.education.length > 0 && <section><h3>EDUCATION</h3>{draft.education.map(e => <div className="byo-paper-entry" key={e.id}><div><strong>{e.name || 'School / university'}{e.location && `, ${e.location}`}</strong><span>{e.dates}</span></div><div><em>{e.title || 'Degree / diploma'}</em></div>{e.coursework && <p>Relevant coursework: {formattedText(e.coursework)}</p>}</div>)}</section>;
  blocks.projects = draft.projects.length > 0 && <section><h3>PROJECTS</h3>{draft.projects.map(e => <div className="byo-paper-entry" key={e.id}><div><strong>{e.name || 'Project name'}{e.stack && <small> | {e.stack}</small>}</strong><span>{e.dates}</span></div><ul>{e.points.filter(p => p.trim()).map((p, i) => <li key={i}>{formattedText(p)}</li>)}</ul></div>)}</section>;
  blocks.experiences = draft.experiences.length > 0 && <section><h3>EXPERIENCE</h3>{draft.experiences.map(e => <div className="byo-paper-entry" key={e.id}><div><strong>{e.name || 'Company'}{e.location && `, ${e.location}`}</strong><span>{e.dates}</span></div><div><em>{e.title || 'Job title'}</em></div><ul>{e.points.filter(p => p.trim()).map((p, i) => <li key={i}>{formattedText(p)}</li>)}</ul></div>)}</section>;
  blocks.skill_groups = draft.skill_groups.length > 0 && <section><h3>TECHNICAL SKILLS</h3>{draft.skill_groups.map(e => <p key={e.id}><strong>{e.name || 'Skills'}:</strong> {e.skills.filter(Boolean).join(', ')}</p>)}</section>;
  draft.custom_sections.forEach(c => { blocks[`custom:${c.id}`] = <section key={c.id}><h3>{c.name.toUpperCase()}</h3>{c.entries.map(e => <div className="byo-paper-entry" key={e.id}><div><strong>{e.name || 'Entry name'}{e.location && `, ${e.location}`}</strong><span>{e.dates}</span></div>{e.title && <div><em>{e.title}</em></div>}<ul>{e.points.filter(p => p.trim()).map((p, i) => <li key={i}>{formattedText(p)}</li>)}</ul></div>)}</section>; });
  return <div className="byo-paper">
    <header><h2>{draft.full_name || 'Your name'}</h2><p>{[draft.phone, draft.email, draft.location].filter(Boolean).join(' | ') || 'Your contact details will appear here'}</p></header>





    {orderedSections(draft).map(key => <Fragment key={key}>{blocks[key]}</Fragment>)}
    {!draft.custom_sections.length && !draft.experiences.length && !draft.education.length && !draft.projects.length && !draft.skill_groups.length && <div className="byo-paper-placeholder"><span>YOUR NEXT CHAPTER</span><p>Add your first section to start shaping your resume.</p></div>}
  </div>;
}

export default function ResumeBuilder({ onSendToReview }: { onSendToReview: (file: File) => Promise<void> }) {
  const [draft, setDraft] = useState<Draft>(loadDraft);
  const [section, setSection] = useState<Section>('contact');
  const [saveStatus, setSaveStatus] = useState('Saved on this device');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [previewSize, setPreviewSize] = useState<{ width: number; height: number } | null>(null);
  const previewPanel = useRef<HTMLElement>(null);
  const builderGrid = useRef<HTMLDivElement>(null);
  const resizeStart = useRef<{ x: number; y: number; width: number; height: number } | null>(null);
  function resizePreview(width: number, height: number) {
    const available = builderGrid.current?.clientWidth ?? 800;
    const maxWidth = window.innerWidth > 1050 ? Math.max(300, available - 342) : available;
    setPreviewSize({ width: Math.max(Math.min(300, maxWidth), Math.min(maxWidth, width)), height: Math.max(320, Math.min(1400, height)) });
  }
  const [undoDraft, setUndoDraft] = useState<Draft | null>(null);
  const [downloads, setDownloads] = useState<{ pdf_download_url: string; tex_download_url: string; docx_download_url: string; snapshot: string } | null>(null);
  const request = useRef<AbortController | null>(null);
  const dialog = useRef<HTMLDialogElement>(null);
  const snapshot = JSON.stringify(draft);
  const customSection = draft.custom_sections.find(c => `custom:${c.id}` === section);
  const entries = section === 'contact' ? [] : customSection ? customSection.entries : draft[section as Exclude<BuiltInSection, 'contact'>] ?? [];
  const allSections = [...sections, ...draft.custom_sections.map(c => ({ key: `custom:${c.id}` as Section, name: c.name, hint: 'Add your own entries and achievement points.' }))];
  const documentOrder = orderedSections(draft);
  const orderedNavigation = [sections[0], ...documentOrder.map(key => allSections.find(s => s.key === key)!)];
  function moveSection(key: string, direction: number) {
    update({ ...draft, section_order: moved(documentOrder, documentOrder.indexOf(key), direction) });
  }
  const current = allSections.find(s => s.key === section) ?? sections[0];
  const [addingSection, setAddingSection] = useState(false);
  const [sectionName, setSectionName] = useState('');
  function addSection() {
    const name = sectionName.trim();
    if (!name || draft.custom_sections.length >= 8) return;
    const id = crypto.randomUUID();
    update({ ...draft, custom_sections: [...draft.custom_sections, { id, name, entries: [] }] });
    setSection(`custom:${id}`); setSectionName(''); setAddingSection(false);
  }
  function replaceEntries(key: Collection, next: Entry[]) {
    if (key.startsWith('custom:')) update({ ...draft, custom_sections: draft.custom_sections.map(c => `custom:${c.id}` === key ? { ...c, entries: next } : c) });
    else update({ ...draft, [key]: next });
  }

  useEffect(() => {
    const timer = window.setTimeout(() => {
      try { localStorage.setItem(STORAGE, JSON.stringify(draft)); setSaveStatus('Saved on this device'); }
      catch { setSaveStatus('Storage unavailable - keep this page open'); }
    }, 350);
    return () => window.clearTimeout(timer);
  }, [draft]);
  useEffect(() => () => { request.current?.abort(); }, []);
  useEffect(() => {
    if (expanded) dialog.current?.showModal(); else dialog.current?.close();
  }, [expanded]);

  function update(next: Draft) {
    request.current?.abort();
    setBusy(false);
    setError('');
    setDraft(next);
  }
  function updateEntry(key: Collection, id: string, patch: Partial<Entry>) {
    replaceEntries(key, entries.map(e => e.id === id ? { ...e, ...patch } : e));
  }
  function addEntry() {
    if (section === 'contact' || entries.length >= 12) return;
    replaceEntries(section, [...entries, newEntry()]);
  }
  function removeEntry(key: Collection, id: string) {
    setUndoDraft(draft); replaceEntries(key, entries.filter(e => e.id !== id));
  }
  async function sendToReview() {
    request.current?.abort();
    const controller = new AbortController(); request.current = controller;
    setBusy(true); setError('');
    try {
      const response = await fetch(`${API_BASE_URL}/api/resume-builder/source-pdf`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: snapshot, signal: controller.signal,
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => null);
        throw new Error(typeof payload?.detail === 'string' ? payload.detail : 'The resume could not be prepared for review.');
      }
      const blob = await response.blob();
      if (!controller.signal.aborted) {
        const safeName = (draft.full_name.trim() || 'resume').replace(/[^a-z0-9_-]+/gi, '-').replace(/^-|-$/g, '') || 'resume';
        await onSendToReview(new File([blob], `${safeName}.pdf`, { type: 'application/pdf' }));
      }
    } catch (reason) {
      if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : 'Unable to send the resume for review.');
    } finally { if (!controller.signal.aborted) setBusy(false); }
  }
  async function prepareDownloads() {
    request.current?.abort();
    const controller = new AbortController(); request.current = controller;
    setBusy(true); setError('');
    try {
      const response = await fetch(`${API_BASE_URL}/api/resume-builder/export`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: snapshot, signal: controller.signal,
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => null);
        throw new Error(typeof payload?.detail === 'string' ? payload.detail : 'Check the section fields and try again.');
      }
      const result = await response.json();
      if (!controller.signal.aborted) setDownloads({ ...result, snapshot });
    } catch (reason) {
      if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : 'Unable to render PDF.');
    } finally { if (!controller.signal.aborted) setBusy(false); }
  }

  const paper = <ResumePaper draft={draft} />;
  return <section className="byo-workspace">
    <div className="byo-intro"><div><span className="section-kicker">YOUR WORDS. YOUR STORY.</span><h2>Build your own.</h2><p>A beautiful resume, without a document editor. Add your content and let the template handle the rest.</p></div><span className="byo-no-ai">100% yours / No AI</span></div>
    <div className="byo-toolbar"><span role="status">{saveStatus}</span><div><button className="btn btn-secondary" type="button" disabled={busy} onClick={() => void sendToReview()}>Send to review</button><button className="btn btn-ghost" type="button" onClick={() => { if (window.confirm('Clear this device\'s builder draft?')) { setUndoDraft(draft); update(emptyDraft()); setSection('contact'); } }}>Clear draft</button><button className="btn btn-primary" type="button" disabled={busy} onClick={() => void prepareDownloads()}>{busy ? 'Preparing...' : 'Prepare downloads'}</button></div></div>
    {downloads?.snapshot === snapshot && <div className="byo-downloads" role="status"><span>Your files are ready.</span><a className="btn btn-primary" href={artifactUrl(downloads.pdf_download_url)} download>Download PDF</a><a className="btn btn-secondary" href={artifactUrl(downloads.docx_download_url)} download>Download Word</a><a className="btn btn-secondary" href={artifactUrl(downloads.tex_download_url)} download>Download LaTeX</a></div>}
    {error && <div className="error-banner" role="alert"><strong>Document notice</strong><span>{error}</span></div>}
    {undoDraft && <div className="byo-undo"><span>Draft updated.</span><button type="button" onClick={() => { update(undoDraft); setSection('contact'); setUndoDraft(null); }}>Undo removal / clear</button><button type="button" aria-label="Dismiss undo" onClick={() => setUndoDraft(null)}>Dismiss</button></div>}
    <div className="byo-grid" ref={builderGrid} style={previewSize ? { '--byo-preview-width': `min(${previewSize.width}px, max(300px, calc(100% - 342px)))` } as React.CSSProperties : undefined}>
      <div className="byo-editor">
        <nav className="byo-section-nav" aria-label="Resume sections">{orderedNavigation.map((s, i) => <span className="byo-section-tab" key={s.key}><button type="button" key={s.key} className={section === s.key ? 'active' : ''} aria-pressed={section === s.key} onClick={() => setSection(s.key)}><span>0{i + 1}</span>{s.name}{s.key !== 'contact' && <small>{s.key.startsWith('custom:') ? draft.custom_sections.find(c => `custom:${c.id}` === s.key)?.entries.length : draft[s.key as Exclude<BuiltInSection, 'contact'>].length}</small>}</button>{s.key !== 'contact' && <MoveControls index={i - 1} count={documentOrder.length} group="sections" label={s.name} onMove={direction => moveSection(s.key, direction)} />}</span>)}<button type="button" disabled={draft.custom_sections.length >= 8} onClick={() => setAddingSection(true)}>+ Add section</button></nav>
        {addingSection && <form className="byo-toolbar" onSubmit={e => { e.preventDefault(); addSection(); }}><label>Section name<input autoFocus maxLength={80} value={sectionName} onChange={e => setSectionName(e.target.value)} placeholder="Leadership, Awards, Volunteering..." /></label><button className="btn btn-primary" type="submit" disabled={!sectionName.trim()}>Add section</button><button className="btn btn-ghost" type="button" onClick={() => setAddingSection(false)}>Cancel</button></form>}
        {customSection && <div className="byo-toolbar"><label>Section name<input maxLength={80} value={customSection.name} onChange={e => { const name = e.target.value; if (name.trim()) update({ ...draft, custom_sections: draft.custom_sections.map(c => c.id === customSection.id ? { ...c, name } : c) }); }} /></label><button className="byo-remove" type="button" onClick={() => { if (window.confirm('Remove this section and its entries?')) { setUndoDraft(draft); update({ ...draft, custom_sections: draft.custom_sections.filter(c => c.id !== customSection.id) }); setSection('contact'); } }}>Remove section</button></div>}
        <div className="byo-section-heading"><div><h3>{current.name}</h3><p>{current.hint}</p></div>{section !== 'contact' && <button className="btn btn-secondary" type="button" disabled={entries.length >= 12} onClick={addEntry}>+ Add {section === 'skill_groups' ? 'skill group' : section === 'experiences' ? 'experience' : section === 'projects' ? 'project' : customSection ? 'entry' : 'education'}</button>}</div>
        {section === 'contact' ? <div className="byo-entry-card"><div className="byo-fields">
          {(['full_name', 'email', 'phone', 'location'] as const).map(key => <label key={key}>{({ full_name: 'Full name', email: 'Email address', phone: 'Phone number', location: 'City / region' })[key]}<input maxLength={key === 'full_name' ? 120 : key === 'email' ? 200 : key === 'phone' ? 80 : 160} type={key === 'email' ? 'email' : 'text'} value={draft[key]} onChange={e => update({ ...draft, [key]: e.target.value })} placeholder={key === 'full_name' ? 'Jordan Lee' : key === 'location' ? 'Toronto, Ontario' : ''} /></label>)}
          </div><div className="byo-tip">Start here, then add sections in any order. Your preview updates as you type.</div></div> : <>
          {!entries.length && <div className="byo-empty"><span>+</span><h4>Your {current.name.toLowerCase()} starts here</h4><p>Add an entry. You can always edit, add more, or remove it later.</p><button className="btn btn-primary" type="button" onClick={addEntry}>Add your first entry</button></div>}
          {entries.map((entry, index) => <details className="byo-entry-card" key={entry.id} open><summary><span className="byo-entry-number">{String(index + 1).padStart(2, '0')}</span><div><strong>{entry.name || `Untitled ${section === 'skill_groups' ? 'skill group' : 'entry'}`}</strong><small>{entry.title || 'Click to collapse / expand'}</small></div><span className="byo-chevron">v</span></summary><div className="byo-entry-body">
            <div className="byo-entry-order"><span>Entry {index + 1} of {entries.length}</span><MoveControls index={index} count={entries.length} group={`entries:${section}`} label={entry.name || 'entry'} onMove={direction => replaceEntries(section as Collection, moved(entries, index, direction))} /></div>
            <div className="byo-fields">
              <label>{section === 'experiences' ? 'Company / organization' : section === 'education' ? 'University / school' : section === 'projects' ? 'Project name' : customSection ? 'Entry name / organization' : 'Skill section name'}<input maxLength={section === 'skill_groups' ? 80 : 180} value={entry.name} onChange={e => updateEntry(section, entry.id, { name: e.target.value })} placeholder={section === 'skill_groups' ? 'Languages & frameworks' : ''} /></label>
              {(section === 'experiences' || section === 'education' || !!customSection) && <label>{section === 'experiences' ? 'Job title' : customSection ? 'Role / subtitle (optional)' : 'Major / degree / diploma'}<input maxLength={180} value={entry.title} onChange={e => updateEntry(section, entry.id, { title: e.target.value })} /></label>}
              {section !== 'skill_groups' && <label>Dates<input maxLength={100} value={entry.dates} onChange={e => updateEntry(section, entry.id, { dates: e.target.value })} placeholder="Jan 2023 - Present" /></label>}
              {(section === 'experiences' || section === 'education' || !!customSection) && <label>Location<input maxLength={160} value={entry.location} onChange={e => updateEntry(section, entry.id, { location: e.target.value })} /></label>}
              {section === 'projects' && <label>Project stack<input maxLength={180} value={entry.stack} onChange={e => updateEntry(section, entry.id, { stack: e.target.value })} placeholder="React, FastAPI, PostgreSQL" /></label>}
            </div>
            {section === 'education' && <FormattedTextarea label="Relevant coursework" value={entry.coursework} onChange={coursework => updateEntry(section, entry.id, { coursework })} placeholder="Algorithms, Databases, Software Engineering" />}
            {section === 'skill_groups' && <label>Skills, separated by commas<textarea rows={3} maxLength={3500} value={entry.skills.join(',')} onChange={e => updateEntry(section, entry.id, { skills: e.target.value.split(',') })} placeholder="Python, TypeScript, React, SQL" /><small>Up to 40 skills per group. Add another group for a new category.</small></label>}
            {(section === 'experiences' || section === 'projects' || !!customSection) && <div className="byo-points"><h4>Achievement points</h4><p>One idea per point. Select important metrics and make them bold.</p>{entry.points.map((point, pi) => <div className="byo-point" key={pi}><MoveControls index={pi} count={entry.points.length} group={`points:${entry.id}`} label={`point ${pi + 1}`} onMove={direction => updateEntry(section as Collection, entry.id, { points: moved(entry.points, pi, direction) })} /><FormattedTextarea label={`Point ${pi + 1}`} value={point} onChange={value => updateEntry(section, entry.id, { points: entry.points.map((p, i) => i === pi ? value : p) })} placeholder="Reduced processing time by 40% by introducing caching." /><button type="button" aria-label={`Remove point ${pi + 1}`} onClick={() => { setUndoDraft(draft); updateEntry(section, entry.id, { points: entry.points.filter((_, i) => i !== pi) }); }}>x</button></div>)}<button className="byo-add-point" type="button" disabled={entry.points.length >= 6} onClick={() => updateEntry(section, entry.id, { points: [...entry.points, ''] })}>+ Add point {entry.points.length + 1}</button></div>}
            <button className="byo-remove" type="button" onClick={() => removeEntry(section, entry.id)}>Remove this entry</button>
          </div></details>)}
        </>}
        <p className="byo-privacy">Drafts are stored in this browser, not in an account. Use Clear draft on a shared device.</p>
      </div>
      <aside ref={previewPanel} className={`byo-preview-panel${previewSize ? ' byo-preview-resized' : ''}`} style={previewSize ? { height: previewSize.height } : undefined}>
        <div className="byo-preview-heading"><div><span className="section-kicker">HARSHIBAR TEMPLATE</span><h3>Live preview</h3></div><button className="btn btn-ghost" type="button" onClick={() => setExpanded(true)}>Expand</button></div>
        <div className="byo-preview-tools" aria-live="polite"><span className="byo-preview-status" data-state="ready"><i aria-hidden="true" />Changes appear instantly</span><span>Live layout</span></div>
        <div className="byo-paper-stage">
          <div className="byo-paper-open" role="button" tabIndex={0} aria-label="Expand resume preview" title="Click to expand" onClick={() => setExpanded(true)} onKeyDown={event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); setExpanded(true); } }}>
            {paper}
            <span className="byo-paper-open-hint" aria-hidden="true">Expand preview</span>
          </div>
        </div>
        <p className="byo-preview-note">This preview updates as you type. Click the page to expand it; prepare your downloads for the final compiled files.</p>
        <span className="byo-preview-resize" role="button" tabIndex={0} aria-label="Resize preview. Drag or use arrow keys. Double-click to reset." title="Drag to resize / double-click to reset"
        onDoubleClick={() => setPreviewSize(null)}
        onKeyDown={e => {
          if (e.key === 'Escape' || e.key === 'Home') { e.preventDefault(); setPreviewSize(null); return; }
          const rect = previewPanel.current?.getBoundingClientRect();
          if (!rect || !['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(e.key)) return;
          e.preventDefault(); resizePreview(rect.width + (e.key === 'ArrowRight' ? 24 : e.key === 'ArrowLeft' ? -24 : 0), rect.height + (e.key === 'ArrowDown' ? 24 : e.key === 'ArrowUp' ? -24 : 0));
        }}
        onPointerDown={e => {
          if (e.button !== 0) return;
          const rect = previewPanel.current?.getBoundingClientRect(); if (!rect) return;
          e.preventDefault(); resizeStart.current = { x: e.clientX, y: e.clientY, width: rect.width, height: rect.height };
          e.currentTarget.setPointerCapture(e.pointerId);
        }}
        onPointerMove={e => {
          const start = resizeStart.current; if (!start) return;
          resizePreview(start.width + e.clientX - start.x, start.height + e.clientY - start.y);
        }}
        onPointerUp={e => { resizeStart.current = null; if (e.currentTarget.hasPointerCapture(e.pointerId)) e.currentTarget.releasePointerCapture(e.pointerId); }}
        onPointerCancel={() => { resizeStart.current = null; }}
        onLostPointerCapture={() => { resizeStart.current = null; }}
      ><span aria-hidden="true">&#x25E2;</span></span>
      </aside>
    </div>
    <dialog className="byo-dialog" ref={dialog} onCancel={() => setExpanded(false)} onClick={e => { if (e.target === e.currentTarget) setExpanded(false); }}><div className="byo-dialog-header"><div><span className="section-kicker">YOUR RESUME</span><h3>Document preview</h3></div><button type="button" autoFocus onClick={() => setExpanded(false)} aria-label="Close document preview">Close</button></div><div className="byo-dialog-paper">{paper}</div></dialog>
  </section>;
}
