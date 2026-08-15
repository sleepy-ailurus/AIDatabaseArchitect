// Self-contained ER diagram renderer used for PNG/JPEG/SVG export.
// No external dependencies: draws the same nodes/edges VueFlow shows onto a
// plain canvas or into an SVG string.

const TABLE_WIDTH = 260
const HEADER_H = 30
const ROW_H = 20
const PAD = 12
const MARGIN = 30

function esc(s) {
  return String(s == null ? '' : s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

function tableHeight(columns) {
  return HEADER_H + (columns || []).length * ROW_H + PAD * 2
}

export function computeScene(nodes, edges) {
  const items = (nodes || []).map((n) => {
    const cols = n.data?.columns || []
    const x = n.position?.x || 0
    const y = n.position?.y || 0
    const w = TABLE_WIDTH
    const h = tableHeight(cols)
    return {
      id: String(n.id),
      name: n.data?.name || n.id,
      comment: n.data?.comment || '',
      x,
      y,
      w,
      h,
      cx: x + w / 2,
      cy: y + h / 2,
      columns: cols.map((c) => ({
        name: c.name,
        type: c.type || '',
        isPK: !!c.isPK || !!c.is_primary_key,
        isFK: !!c.isFK || !!c.is_fk,
        isUnique: !!c.isUnique || !!c.is_unique,
        comment: c.comment || ''
      }))
    }
  })

  const edgeItems = (edges || []).map((e) => {
    const src = items.find((t) => t.id === String(e.source))
    const tgt = items.find((t) => t.id === String(e.target))
    if (!src || !tgt) return null
    return {
      id: String(e.id),
      src,
      tgt,
      label: `${e.data?.fromColumn || ''}→${e.data?.toColumn || ''}`.replace(/^→|→$/g, ''),
      cardinality: e.data?.cardinality || ''
    }
  }).filter(Boolean)

  let maxX = 0
  let maxY = 0
  for (const t of items) {
    maxX = Math.max(maxX, t.x + t.w)
    maxY = Math.max(maxY, t.y + t.h)
  }
  for (const e of edgeItems) {
    maxX = Math.max(maxX, e.src.cx, e.tgt.cx)
    maxY = Math.max(maxY, e.src.cy, e.tgt.cy)
  }
  const width = Math.max(maxX + MARGIN, 600)
  const height = Math.max(maxY + MARGIN, 400)
  return { width, height, tables: items, edges: edgeItems }
}

function drawTable(ctx, t, scale) {
  const s = scale || 1
  ctx.save()
  ctx.translate(t.x * s, t.y * s)
  // shadow
  ctx.shadowColor = 'rgba(15, 23, 42, 0.12)'
  ctx.shadowBlur = 8 * s
  ctx.fillStyle = '#ffffff'
  roundRect(ctx, 0, 0, t.w * s, t.h * s, 8 * s)
  ctx.shadowColor = 'transparent'
  ctx.fill()
  ctx.strokeStyle = '#cbd5e1'
  ctx.lineWidth = s
  ctx.stroke()

  // header
  ctx.fillStyle = '#3b82f6'
  roundRect(ctx, 0, 0, t.w * s, HEADER_H * s, 8 * s)
  ctx.fill()
  ctx.fillRect(0, HEADER_H * s / 2, t.w * s, HEADER_H * s / 2)
  ctx.fillStyle = '#ffffff'
  ctx.font = `600 ${13 * s}px system-ui, sans-serif`
  ctx.textBaseline = 'middle'
  ctx.fillText(truncate(t.name, 28), 10 * s, HEADER_H * s / 2)

  // columns
  ctx.font = `${11 * s}px 'SF Mono', Consolas, monospace`
  t.columns.forEach((c, i) => {
    const rowY = HEADER_H * s + i * ROW_H * s
    if (i % 2 === 1) {
      ctx.fillStyle = '#f8fafc'
      ctx.fillRect(0, rowY, t.w * s, ROW_H * s)
    }
    let prefix = ''
    let color = '#334155'
    if (c.isPK) { prefix = '🔑 '; color = '#b45309' }
    else if (c.isFK) { prefix = '🔗 '; color = '#1e40af' }
    else if (c.isUnique) { prefix = 'U '; color = '#4338ca' }
    ctx.fillStyle = color
    ctx.fillText(prefix + truncate(c.name, 18), 8 * s, rowY + ROW_H * s / 2)
    ctx.fillStyle = '#64748b'
    ctx.textAlign = 'right'
    ctx.fillText(truncate(c.type, 12), (t.w - 8) * s, rowY + ROW_H * s / 2)
    ctx.textAlign = 'left'
  })
  ctx.restore()
}

function drawEdge(ctx, e, scale) {
  const s = scale || 1
  // Connect the table borders (plus a gap) instead of centers so lines and
  // markers never overlap the table bodies.
  const { p1, p2 } = edgeEndpoints(e)
  const x1 = p1.x * s
  const y1 = p1.y * s
  const x2 = p2.x * s
  const y2 = p2.y * s
  ctx.strokeStyle = '#64748b'
  ctx.lineWidth = 1.4 * s
  ctx.beginPath()
  ctx.moveTo(x1, y1)
  ctx.lineTo(x2, y2)
  ctx.stroke()
  // Crow's foot / double-bar markers at both ends based on cardinality.
  const card = String(e.cardinality || '1:N').toUpperCase()
  const srcInward = Math.atan2(e.src.cy - p1.y, e.src.cx - p1.x)
  const tgtInward = Math.atan2(e.tgt.cy - p2.y, e.tgt.cx - p2.x)
  drawEndMarker(ctx, x1, y1, srcInward, card.startsWith('N') ? 'N' : '1', s)
  drawEndMarker(ctx, x2, y2, tgtInward, card.endsWith('N') ? 'N' : '1', s)
  if (e.label) {
    ctx.font = `500 ${10 * s}px system-ui, sans-serif`
    const mx = (x1 + x2) / 2
    const my = (y1 + y2) / 2
    const tw = ctx.measureText(e.label).width + 10 * s
    ctx.fillStyle = 'rgba(255,255,255,0.9)'
    roundRect(ctx, mx - tw / 2, my - 9 * s, tw, 16 * s, 4 * s)
    ctx.fill()
    ctx.fillStyle = '#334155'
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillText(e.label, mx, my + 1 * s)
    ctx.textAlign = 'left'
  }
}

function rectBorderPoint(rect, px, py) {
  // Intersection of the ray from rect center through (px, py) with the border.
  const cx = rect.cx
  const cy = rect.cy
  const dx = px - cx
  const dy = py - cy
  const absDx = Math.abs(dx) || 1e-6
  const absDy = Math.abs(dy) || 1e-6
  const t = Math.min(rect.w / 2 / absDx, rect.h / 2 / absDy)
  return { x: cx + dx * t, y: cy + dy * t }
}

function edgeEndpoints(e, gap = 16) {
  // Line endpoints sit `gap` pixels outside each table border, so the
  // cardinality markers have breathing room from the table frame.
  const p1 = rectBorderPoint(e.src, e.tgt.cx, e.tgt.cy)
  const p2 = rectBorderPoint(e.tgt, e.src.cx, e.src.cy)
  const extend = (p, cx, cy) => {
    const d = Math.hypot(p.x - cx, p.y - cy) || 1
    return { x: p.x + ((p.x - cx) / d) * gap, y: p.y + ((p.y - cy) / d) * gap }
  }
  return { p1: extend(p1, e.src.cx, e.src.cy), p2: extend(p2, e.tgt.cx, e.tgt.cy) }
}

function drawEndMarker(ctx, x, y, inwardAng, type, s) {
  // inwardAng points from the line end INTO the entity.
  ctx.strokeStyle = '#64748b'
  ctx.lineWidth = 1.4 * s
  const size = 10 * s
  if (type === 'N') {
    // Crow's foot: three prongs fanning INTO the entity (open side faces the
    // table), so it reads as a "chicken foot", not an arrow.
    ctx.beginPath()
    for (const da of [-0.45, 0, 0.45]) {
      ctx.moveTo(x, y)
      ctx.lineTo(x + size * Math.cos(inwardAng + da), y + size * Math.sin(inwardAng + da))
    }
    ctx.stroke()
  } else {
    // Double bar: two parallel bars perpendicular to the line, placed one
    // behind the other along the relationship line at the "one" end.
    const lineAng = inwardAng + Math.PI
    const perp = lineAng + Math.PI / 2
    const half = size * 0.72
    for (const off of [2.5 * s, 8.5 * s]) {
      const bx = x + off * Math.cos(lineAng)
      const by = y + off * Math.sin(lineAng)
      ctx.beginPath()
      ctx.moveTo(bx + half * Math.cos(perp), by + half * Math.sin(perp))
      ctx.lineTo(bx - half * Math.cos(perp), by - half * Math.sin(perp))
      ctx.stroke()
    }
  }
}

function roundRect(ctx, x, y, w, h, r) {
  const rr = Math.min(r, w / 2, h / 2)
  ctx.beginPath()
  ctx.moveTo(x + rr, y)
  ctx.arcTo(x + w, y, x + w, y + h, rr)
  ctx.arcTo(x + w, y + h, x, y + h, rr)
  ctx.arcTo(x, y + h, x, y, rr)
  ctx.arcTo(x, y, x + w, y, rr)
  ctx.closePath()
}

function truncate(s, n) {
  const str = String(s == null ? '' : s)
  return str.length > n ? str.slice(0, n - 1) + '…' : str
}

export function renderCanvas(nodes, edges, scale = 2) {
  const scene = computeScene(nodes, edges)
  const canvas = document.createElement('canvas')
  canvas.width = Math.round(scene.width * scale)
  canvas.height = Math.round(scene.height * scale)
  const ctx = canvas.getContext('2d')
  ctx.fillStyle = '#ffffff'
  ctx.fillRect(0, 0, canvas.width, canvas.height)
  ctx.save()
  ctx.scale(scale, scale)
  ctx.translate(MARGIN / 2, MARGIN / 2)
  for (const t of scene.tables) drawTable(ctx, t, 1)
  // Edges are drawn on top so the connection markers are never clipped.
  for (const e of scene.edges) drawEdge(ctx, e, 1)
  ctx.restore()
  return canvas
}

export function renderSvg(nodes, edges) {
  const scene = computeScene(nodes, edges)
  const parts = []
  parts.push(
    `<svg xmlns="http://www.w3.org/2000/svg" width="${scene.width}" height="${scene.height}" viewBox="0 0 ${scene.width} ${scene.height}" font-family="system-ui, sans-serif">`
  )
  parts.push(`<rect width="${scene.width}" height="${scene.height}" fill="#ffffff"/>`)
  parts.push(`<g transform="translate(${MARGIN / 2}, ${MARGIN / 2})">`)

  // Tables first, then edges on top.
  for (const t of scene.tables) {
    const h = t.h
    parts.push(
      `<rect x="${t.x}" y="${t.y}" width="${t.w}" height="${h}" rx="8" fill="#ffffff" stroke="#cbd5e1" stroke-width="1"/>`
    )
    parts.push(
      `<path d="M${t.x} ${t.y + 8} a8 8 0 0 1 8 -8 h${t.w - 16} a8 8 0 0 1 8 8 v${HEADER_H - 8} h-${t.w} z" fill="#3b82f6"/>`
    )
    parts.push(
      `<text x="${t.x + 10}" y="${t.y + HEADER_H / 2 + 4}" font-size="13" font-weight="600" fill="#ffffff">${esc(truncate(t.name, 28))}</text>`
    )
    t.columns.forEach((c, i) => {
      const rowY = t.y + HEADER_H + i * ROW_H
      if (i % 2 === 1) {
        parts.push(`<rect x="${t.x}" y="${rowY}" width="${t.w}" height="${ROW_H}" fill="#f8fafc"/>`)
      }
      const key = c.isPK ? '🔑 ' : c.isFK ? '🔗 ' : c.isUnique ? 'U ' : ''
      const color = c.isPK ? '#b45309' : c.isFK ? '#1e40af' : c.isUnique ? '#4338ca' : '#334155'
      parts.push(
        `<text x="${t.x + 8}" y="${rowY + ROW_H / 2 + 3.5}" font-size="11" font-family="'SF Mono', Consolas, monospace" fill="${color}">${esc(key + truncate(c.name, 18))}</text>`
      )
      parts.push(
        `<text x="${t.x + t.w - 8}" y="${rowY + ROW_H / 2 + 3.5}" font-size="11" text-anchor="end" fill="#64748b">${esc(truncate(c.type, 12))}</text>`
      )
    })
  }

  for (const e of scene.edges) {
    const { p1, p2 } = edgeEndpoints(e)
    const x1 = p1.x
    const y1 = p1.y
    const x2 = p2.x
    const y2 = p2.y
    parts.push(
      `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="#64748b" stroke-width="1.4"/>`
    )
    const card = String(e.cardinality || '1:N').toUpperCase()
    const srcInward = Math.atan2(e.src.cy - p1.y, e.src.cx - p1.x)
    const tgtInward = Math.atan2(e.tgt.cy - p2.y, e.tgt.cx - p2.x)
    parts.push(svgEndMarker(x1, y1, srcInward, card.startsWith('N') ? 'N' : '1'))
    parts.push(svgEndMarker(x2, y2, tgtInward, card.endsWith('N') ? 'N' : '1'))
    if (e.label) {
      const mx = (x1 + x2) / 2
      const my = (y1 + y2) / 2
      parts.push(
        `<rect x="${mx - 45}" y="${my - 9}" width="90" height="16" rx="4" fill="rgba(255,255,255,0.92)"/>` +
          `<text x="${mx}" y="${my + 3.5}" text-anchor="middle" font-size="10" fill="#334155">${esc(e.label)}</text>`
      )
    }
  }

  parts.push('</g></svg>')
  return parts.join('')
}

function svgEndMarker(x, y, inwardAng, type) {
  const size = 10
  const px = (a) => (x + size * Math.cos(a)).toFixed(1)
  const py = (a) => (y + size * Math.sin(a)).toFixed(1)
  if (type === 'N') {
    return (
      `<path d="M${x} ${y} L${px(inwardAng - 0.45)} ${py(inwardAng - 0.45)} ` +
      `M${x} ${y} L${px(inwardAng)} ${py(inwardAng)} ` +
      `M${x} ${y} L${px(inwardAng + 0.45)} ${py(inwardAng + 0.45)}" stroke="#64748b" stroke-width="1.4" fill="none"/>`
    )
  }
  const lineAng = inwardAng + Math.PI
  const perp = lineAng + Math.PI / 2
  const half = size * 0.72
  let d = ''
  for (const off of [2.5, 8.5]) {
    const bx = x + off * Math.cos(lineAng)
    const by = y + off * Math.sin(lineAng)
    d += `M${(bx + half * Math.cos(perp)).toFixed(1)} ${(by + half * Math.sin(perp)).toFixed(1)} ` +
      `L${(bx - half * Math.cos(perp)).toFixed(1)} ${(by - half * Math.sin(perp)).toFixed(1)} `
  }
  return `<path d="${d}" stroke="#64748b" stroke-width="1.4" fill="none"/>`
}

export function downloadBlob(content, mime, filename) {
  const blob = content instanceof Blob ? content : new Blob([content], { type: mime })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

export function canvasToBlob(canvas, format, quality = 0.92) {
  return new Promise((resolve, reject) => {
    canvas.toBlob((blob) => (blob ? resolve(blob) : reject(new Error('toBlob failed'))), format, quality)
  })
}
