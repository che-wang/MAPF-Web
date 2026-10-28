<template>
  <canvas
    ref="canvasRef"
    @click="onClick"
    @mousemove="onMouseMove"
    @mouseleave="hoverCell = null"
  />
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted, computed } from 'vue'

const props = defineProps({
  grid: Object,
  agents: Array,
  step: { type: Number, default: 0 },
  selectedAgentId: { type: Number, default: null },
  animating: { type: Boolean, default: true },
  fps: { type: Number, default: 3 }
})

const emit = defineEmits(['select-agent', 'cell-hover'])

const canvasRef = ref(null)
const hoverCell = ref(null)
const cellSize = ref(40)
const animProgress = ref(0)
let rafId = null
let lastT = 0

const animDuration = computed(() => 1 / props.fps)

function rgba(arr, a = 1) {
  return `rgba(${arr[0]},${arr[1]},${arr[2]},${a})`
}

function fitCanvas() {
  const canvas = canvasRef.value
  if (!canvas || !props.grid) return
  const parent = canvas.parentElement
  const pw = parent.clientWidth
  const ph = parent.clientHeight
  const w = props.grid.width
  const h = props.grid.height
  const cs = Math.max(12, Math.min(Math.floor((pw - 40) / w), Math.floor((ph - 40) / h), 60))
  cellSize.value = cs
  canvas.width = w * cs
  canvas.height = h * cs
  draw()
}

function draw() {
  const canvas = canvasRef.value
  if (!canvas || !props.grid) return
  const ctx = canvas.getContext('2d')
  const { width, height } = props.grid
  const cs = cellSize.value

  ctx.clearRect(0, 0, canvas.width, canvas.height)

  ctx.fillStyle = '#1a2035'
  ctx.fillRect(0, 0, canvas.width, canvas.height)

  ctx.strokeStyle = '#2a3148'
  ctx.lineWidth = 1
  for (let x = 0; x <= width; x++) {
    ctx.beginPath()
    ctx.moveTo(x * cs + 0.5, 0)
    ctx.lineTo(x * cs + 0.5, height * cs)
    ctx.stroke()
  }
  for (let y = 0; y <= height; y++) {
    ctx.beginPath()
    ctx.moveTo(0, y * cs + 0.5)
    ctx.lineTo(width * cs, y * cs + 0.5)
    ctx.stroke()
  }

  if (props.grid.obstacles) {
    ctx.fillStyle = '#3d4763'
    for (const o of props.grid.obstacles) {
      ctx.fillRect(o.x * cs + 2, o.y * cs + 2, cs - 4, cs - 4)
    }
  }

  if (hoverCell.value) {
    const h = hoverCell.value
    ctx.fillStyle = 'rgba(100,181,246,0.15)'
    ctx.fillRect(h.x * cs, h.y * cs, cs, cs)
  }

  if (props.agents) {
    for (const a of props.agents) {
      if (!a.path || a.path.length < 2) continue
      const isSel = props.selectedAgentId === a.id
      const baseAlpha = isSel ? 1.0 : 0.35
      const lineW = isSel ? 3 : 2
      drawPath(ctx, a.path, a.color, baseAlpha, lineW, cs)
    }
  }

  if (props.agents) {
    for (const a of props.agents) {
      if (!a.path || a.path.length < 2) continue
      const isSel = props.selectedAgentId === a.id
      drawTraveledPath(ctx, a.path, a.color, props.step, isSel, cellSize.value)
    }
  }

  if (props.agents) {
    for (const a of props.agents) {
      const cs2 = cellSize.value
      const sx = a.start.x * cs2 + cs2 / 2
      const sy = a.start.y * cs2 + cs2 / 2
      ctx.strokeStyle = rgba(a.color, 0.8)
      ctx.lineWidth = 2
      ctx.strokeRect(sx - cs2 / 2 + 4, sy - cs2 / 2 + 4, cs2 - 8, cs2 - 8)
      ctx.fillStyle = rgba(a.color, 0.3)
      ctx.fillRect(sx - cs2 / 2 + 4, sy - cs2 / 2 + 4, cs2 - 8, cs2 - 8)

      const gx = a.goal.x * cs2 + cs2 / 2
      const gy = a.goal.y * cs2 + cs2 / 2
      ctx.fillStyle = rgba(a.color, 0.2)
      ctx.beginPath()
      ctx.arc(gx, gy, cs2 / 2 - 4, 0, Math.PI * 2)
      ctx.fill()
      ctx.strokeStyle = rgba(a.color, 1)
      ctx.lineWidth = 2.5
      ctx.beginPath()
      ctx.arc(gx, gy, cs2 / 2 - 4, 0, Math.PI * 2)
      ctx.stroke()
      ctx.fillStyle = rgba(a.color, 1)
      ctx.font = `bold ${Math.max(8, Math.floor(cs2 * 0.28))}px sans-serif`
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      ctx.fillText('★', gx, gy)
    }
  }

  if (props.agents) {
    for (const a of props.agents) {
      const pose = interpolatePose(a, props.step)
      const cs2 = cellSize.value
      const cx = pose.x * cs2 + cs2 / 2
      const cy = pose.y * cs2 + cs2 / 2
      const r = cs2 / 2 - 5

      ctx.fillStyle = 'rgba(0,0,0,0.35)'
      ctx.beginPath()
      ctx.ellipse(cx + 2, cy + r - 3, r * 0.9, r * 0.3, 0, 0, Math.PI * 2)
      ctx.fill()

      ctx.save()
      ctx.translate(cx, cy)
      ctx.rotate(pose.angle)

      ctx.fillStyle = rgba(a.color, 1)
      ctx.beginPath()
      ctx.moveTo(r * 1.1, 0)
      ctx.lineTo(-r * 0.6, r * 0.8)
      ctx.lineTo(-r * 0.25, 0)
      ctx.lineTo(-r * 0.6, -r * 0.8)
      ctx.closePath()
      ctx.fill()

      ctx.strokeStyle = 'rgba(255,255,255,0.75)'
      ctx.lineWidth = 1.5
      ctx.beginPath()
      ctx.moveTo(r * 1.1, 0)
      ctx.lineTo(-r * 0.6, r * 0.8)
      ctx.lineTo(-r * 0.25, 0)
      ctx.lineTo(-r * 0.6, -r * 0.8)
      ctx.closePath()
      ctx.stroke()

      ctx.fillStyle = 'rgba(0,0,0,0.25)'
      ctx.beginPath()
      ctx.arc(-r * 0.05, 0, r * 0.35, 0, Math.PI * 2)
      ctx.fill()

      ctx.restore()

      if (props.selectedAgentId === a.id) {
        ctx.strokeStyle = '#fff'
        ctx.lineWidth = 2.5
        ctx.setLineDash([4, 3])
        ctx.beginPath()
        ctx.arc(cx, cy, r + 5, 0, Math.PI * 2)
        ctx.stroke()
        ctx.setLineDash([])
      }

      ctx.fillStyle = '#fff'
      ctx.font = `bold ${Math.max(8, Math.floor(cs2 * 0.32))}px sans-serif`
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      ctx.fillText(a.id, cx, cy)
    }
  }
}

function pathPoint(p, cs) {
  return { x: p.x * cs + cs / 2, y: p.y * cs + cs / 2 }
}

function drawPath(ctx, path, color, alpha, lineW, cs) {
  ctx.strokeStyle = rgba(color, alpha)
  ctx.lineWidth = lineW
  ctx.lineCap = 'round'
  ctx.lineJoin = 'round'
  ctx.beginPath()
  for (let i = 0; i < path.length; i++) {
    const p = pathPoint(path[i], cs)
    if (i === 0) ctx.moveTo(p.x, p.y)
    else ctx.lineTo(p.x, p.y)
  }
  ctx.stroke()
}

function drawTraveledPath(ctx, path, color, step, isSel, cs) {
  if (step <= 0) return
  const count = Math.min(step, path.length - 1)
  ctx.strokeStyle = rgba(color, isSel ? 0.25 : 0.12)
  ctx.lineWidth = 1.5
  ctx.setLineDash([4, 4])
  ctx.beginPath()
  for (let i = 0; i <= count; i++) {
    const p = pathPoint(path[i], cs)
    if (i === 0) ctx.moveTo(p.x, p.y)
    else ctx.lineTo(p.x, p.y)
  }
  ctx.stroke()
  ctx.setLineDash([])
}

function dirAngle(from, to) {
  return Math.atan2(to.y - from.y, to.x - from.x)
}

function angleDiff(from, to) {
  let d = to - from
  while (d > Math.PI) d -= 2 * Math.PI
  while (d < -Math.PI) d += 2 * Math.PI
  return d
}

function smoothstep(t) {
  return t * t * (3 - 2 * t)
}

function interpolatePose(agent, step) {
  if (!agent.path || agent.path.length === 0) {
    return { x: agent.start.x, y: agent.start.y, angle: 0 }
  }
  const path = agent.path
  const idx = Math.min(step, path.length - 1)
  const t = Math.min(1, animProgress.value)

  let x, y
  if (idx >= path.length - 1 || !props.animating) {
    x = path[idx].x
    y = path[idx].y
  } else {
    const a = path[idx]
    const b = path[idx + 1]
    x = a.x + (b.x - a.x) * t
    y = a.y + (b.y - a.y) * t
  }

  let angle
  if (path.length >= 2 && idx < path.length - 1) {
    const enterAngle = idx === 0
      ? dirAngle(path[0], path[1])
      : dirAngle(path[idx - 1], path[idx])
    const exitAngle = dirAngle(path[idx], path[idx + 1])
    const diff = angleDiff(enterAngle, exitAngle)

    let turnT
    if (diff === 0) {
      turnT = 0
    } else if (t > 0.5) {
      turnT = 1
    } else {
      turnT = smoothstep(t / 0.5)
    }
    angle = enterAngle + diff * turnT
  } else if (path.length >= 2) {
    angle = dirAngle(path[path.length - 2], path[path.length - 1])
  } else {
    angle = 0
  }

  return { x, y, angle }
}

function loop(t) {
  if (!lastT) lastT = t
  const dt = (t - lastT) / 1000
  lastT = t
  if (props.animating && props.agents && props.step < maxPathLen()) {
    animProgress.value += dt / animDuration.value
  }
  draw()
  rafId = requestAnimationFrame(loop)
}

function maxPathLen() {
  if (!props.agents) return 0
  return Math.max(...props.agents.map(a => (a.path?.length || 1) - 1))
}

function onClick(e) {
  const rect = canvasRef.value.getBoundingClientRect()
  const mx = e.clientX - rect.left
  const my = e.clientY - rect.top
  const cs = cellSize.value
  const cx = Math.floor(mx / cs)
  const cy = Math.floor(my / cs)
  for (const a of props.agents) {
    const pose = interpolatePose(a, props.step)
    if (pose.x === cx && pose.y === cy) {
      emit('select-agent', a.id)
      return
    }
  }
}

function onMouseMove(e) {
  const rect = canvasRef.value.getBoundingClientRect()
  const mx = e.clientX - rect.left
  const my = e.clientY - rect.top
  const cs = cellSize.value
  hoverCell.value = { x: Math.floor(mx / cs), y: Math.floor(my / cs) }
}

watch(() => props.grid, fitCanvas, { deep: true })
watch(() => props.selectedAgentId, draw)
watch(() => props.step, () => { animProgress.value = 0; draw() })
watch(() => props.animating, draw)

let ro = null
onMounted(() => {
  fitCanvas()
  window.addEventListener('resize', fitCanvas)
  rafId = requestAnimationFrame(loop)
})

onUnmounted(() => {
  window.removeEventListener('resize', fitCanvas)
  if (rafId) cancelAnimationFrame(rafId)
})
</script>