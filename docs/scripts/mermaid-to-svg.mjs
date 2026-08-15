/**
 * Pure-Node Mermaid subset → SVG (no browser).
 * Supports flowchart LR/TD and sequenceDiagram used in product docs.
 */

const esc = (s) =>
  String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');

function parseFlowchart(src) {
  const lines = src
    .split('\n')
    .map((l) => l.trim())
    .filter((l) => l && !l.startsWith('%%'));
  const dirLine = lines.find((l) => /^flowchart\s+(LR|TD|RL|BT)/i.test(l));
  const dir = dirLine?.match(/flowchart\s+(LR|TD|RL|BT)/i)?.[1]?.toUpperCase() ?? 'LR';
  const edges = [];
  const nodes = new Map();
  // A[Label] --> B[Label]  |  A -->|text| B  |  A --> B
  const edgeRe =
    /^([A-Za-z0-9_]+)(?:\[([^\]]+)\])?\s*(?:-->|--)(?:\|([^|]+)\|)?\s*([A-Za-z0-9_]+)(?:\[([^\]]+)\])?/;
  for (const line of lines) {
    if (/^flowchart\b/i.test(line) || /^graph\b/i.test(line)) continue;
    const m = line.match(edgeRe);
    if (!m) continue;
    const [, a, aLabel, _edgeLabel, b, bLabel] = m;
    if (aLabel || !nodes.has(a)) nodes.set(a, aLabel || a);
    if (bLabel || !nodes.has(b)) nodes.set(b, bLabel || b);
    edges.push([a, b]);
  }
  return { dir, nodes, edges };
}

function wrapLabel(label, maxChars) {
  const lines = [];
  let line = '';
  for (const word of String(label).split(/\s+/)) {
    if (line && `${line} ${word}`.length > maxChars) {
      lines.push(line);
      line = word;
      continue;
    }
    line = line ? `${line} ${word}` : word;
  }
  if (line) lines.push(line);
  return lines;
}

function renderFlowchartSvg(src) {
  const { dir, nodes, edges } = parseFlowchart(src);
  if (nodes.size === 0) throw new Error('no flowchart nodes parsed');
  const ids = [...nodes.keys()];
  // topological-ish order following edges
  const order = [];
  const seen = new Set();
  const visit = (id) => {
    if (seen.has(id)) return;
    seen.add(id);
    for (const [a, b] of edges) if (a === id) visit(b);
    order.unshift(id);
  };
  for (const id of ids) visit(id);
  const seq = order.length ? order : ids;

  const boxW = 144;
  const gap = 40;
  const pad = 24;
  const labelLines = new Map([...nodes.entries()].map(([id, label]) => [id, wrapLabel(label, 20)]));
  const maxLines = Math.max(...[...labelLines.values()].map((lines) => lines.length));
  const boxH = 24 + maxLines * 16;
  const horizontal = dir === 'LR' || dir === 'RL';
  const width = horizontal
    ? pad * 2 + seq.length * boxW + (seq.length - 1) * gap
    : pad * 2 + boxW + 40;
  const height = horizontal
    ? pad * 2 + boxH + 20
    : pad * 2 + seq.length * boxH + (seq.length - 1) * gap;

  const pos = new Map();
  seq.forEach((id, i) => {
    if (horizontal) {
      pos.set(id, { x: pad + i * (boxW + gap), y: pad });
    } else {
      pos.set(id, { x: pad + 20, y: pad + i * (boxH + gap) });
    }
  });

  const parts = [
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${width} ${height}" width="${horizontal ? '100%' : width}" role="img" aria-label="flowchart">`,
    `<defs><marker id="mmd-arrow" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto"><polygon points="0 0, 8 3, 0 6" fill="currentColor"/></marker></defs>`,
  ];
  for (const [a, b] of edges) {
    const pa = pos.get(a);
    const pb = pos.get(b);
    if (!pa || !pb) continue;
    const x1 = horizontal ? pa.x + boxW : pa.x + boxW / 2;
    const y1 = horizontal ? pa.y + boxH / 2 : pa.y + boxH;
    const x2 = horizontal ? pb.x : pb.x + boxW / 2;
    const y2 = horizontal ? pb.y + boxH / 2 : pb.y;
    parts.push(
      `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="currentColor" stroke-width="1.5" marker-end="url(#mmd-arrow)"/>`,
    );
  }
  for (const id of seq) {
    const { x, y } = pos.get(id);
    const label = nodes.get(id) ?? id;
    const lines = labelLines.get(id) ?? [label];
    const firstLineY = y + boxH / 2 - ((lines.length - 1) * 16) / 2 + 4;
    const text = lines
      .map((line, index) => `<tspan x="${x + boxW / 2}" dy="${index === 0 ? 0 : 16}">${esc(line)}</tspan>`)
      .join('');
    parts.push(
      `<rect x="${x}" y="${y}" width="${boxW}" height="${boxH}" rx="8" fill="var(--color-fd-card, #fff)" stroke="currentColor" stroke-width="1.5"/>`,
      `<text x="${x + boxW / 2}" y="${firstLineY}" text-anchor="middle" font-size="12" font-family="ui-sans-serif,system-ui,sans-serif" fill="currentColor">${text}</text>`,
    );
  }
  parts.push('</svg>');
  return parts.join('');
}

function parseSequence(src) {
  const lines = src
    .split('\n')
    .map((l) => l.trim())
    .filter((l) => l && !l.startsWith('%%') && !/^sequenceDiagram/i.test(l));
  const participants = [];
  const messages = [];
  for (const line of lines) {
    const p = line.match(/^participant\s+(\S+)(?:\s+as\s+(.+))?/i);
    if (p) {
      participants.push(p[2]?.trim() || p[1]);
      continue;
    }
    const m = line.match(/^(\S+)\s*-->>?(\S+)\s*:\s*(.+)$/);
    if (m) {
      const from = m[1];
      const to = m[2];
      if (!participants.includes(from)) participants.push(from);
      if (!participants.includes(to)) participants.push(to);
      messages.push({ from, to, label: m[3].trim() });
    }
  }
  return { participants, messages };
}

function renderSequenceSvg(src) {
  const { participants, messages } = parseSequence(src);
  if (participants.length === 0) throw new Error('no sequence participants parsed');
  const roleW = 120;
  const left = 40;
  const top = 28;
  const rowH = 36;
  const width = left * 2 + participants.length * roleW;
  const height = top + 40 + Math.max(1, messages.length) * rowH;
  const parts = [
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${width} ${height}" width="100%" role="img" aria-label="sequence diagram">`,
    `<defs><marker id="mmd-seq-arrow" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto"><polygon points="0 0, 8 3, 0 6" fill="currentColor"/></marker></defs>`,
  ];
  participants.forEach((role, i) => {
    const x = left + i * roleW + roleW / 2;
    parts.push(
      `<rect x="${x - 48}" y="8" width="96" height="28" rx="8" fill="var(--color-fd-card,#fff)" stroke="currentColor" stroke-width="1.5"/>`,
      `<text x="${x}" y="26" text-anchor="middle" font-size="12" font-family="ui-sans-serif,system-ui,sans-serif" fill="currentColor">${esc(role)}</text>`,
      `<line x1="${x}" y1="40" x2="${x}" y2="${height - 8}" stroke="currentColor" stroke-opacity="0.35" stroke-dasharray="2 4"/>`,
    );
  });
  messages.forEach((msg, idx) => {
    const fi = participants.indexOf(msg.from);
    const ti = participants.indexOf(msg.to);
    const x1 = left + fi * roleW + roleW / 2;
    const x2 = left + ti * roleW + roleW / 2;
    const y = top + 30 + idx * rowH;
    parts.push(
      `<line x1="${x1}" y1="${y}" x2="${x2}" y2="${y}" stroke="currentColor" stroke-width="1.5" marker-end="url(#mmd-seq-arrow)"/>`,
      `<text x="${(x1 + x2) / 2}" y="${y - 6}" text-anchor="middle" font-size="12" font-family="ui-sans-serif,system-ui,sans-serif" fill="currentColor">${esc(msg.label)}</text>`,
    );
  });
  parts.push('</svg>');
  return parts.join('');
}

export function mermaidToSvg(source) {
  const text = source.trim();
  if (/^flowchart\b/im.test(text) || /^graph\b/im.test(text)) {
    return renderFlowchartSvg(text.replace(/^graph\b/im, 'flowchart'));
  }
  if (/^sequenceDiagram\b/im.test(text)) {
    return renderSequenceSvg(text);
  }
  throw new Error(`unsupported mermaid diagram type (need flowchart or sequenceDiagram)`);
}
