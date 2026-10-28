<template>
  <div class="app">
    <div class="map-area">
      <div class="canvas-wrapper">
        <MapCanvas
          v-if="state?.grid"
          :grid="state.grid"
          :agents="state.agents"
          :step="currentStep"
          :selected-agent-id="selectedAgentId"
          :animating="!paused"
          :fps="fps"
          @select-agent="selectedAgentId = $event"
        />
        <div v-if="planning" class="planning-overlay">
          <div style="text-align:center">
            <div class="spinner"></div>
            <div style="margin-top:12px;color:#a0aec0;font-size:14px">规划中...</div>
          </div>
        </div>
        <div v-if="!state" class="empty-state">正在连接服务器...</div>
      </div>

      <div class="playback-bar" v-if="state">
        <div class="playback-controls">
          <button class="icon-btn" title="重置" @click="resetSteps">⏮</button>
          <button class="icon-btn" title="上一步" @click="stepBack">◀</button>
          <button class="icon-btn primary" :title="paused ? '播放' : '暂停'" @click="togglePause">
            {{ paused ? '▶' : '⏸' }}
          </button>
          <button class="icon-btn" title="下一步" @click="stepFwd">▶</button>
          <button class="icon-btn" title="结束" @click="goEnd">⏭</button>
        </div>
        <input
          type="range"
          :min="0"
          :max="makespan"
          v-model.number="currentStep"
          @change="onSeek"
        />
        <div class="step-label">{{ currentStep }} / {{ makespan }}</div>
      </div>
    </div>

    <div class="panel" v-if="state">
      <div class="panel-title">MAPF多智能体路径规划</div>

      <div class="section">
        <div class="section-title">状态</div>
        <div class="control-row">
          <span class="control-label">状态</span>
          <span
            class="status-badge"
            :class="planning ? 'status-planning' : state.simulation.solved ? 'status-solved' : 'status-failed'"
          >
            {{ planning ? '规划中...' : state.simulation.solved ? '已求解' : '无解' }}
          </span>
        </div>
        <div class="stats">
          <div class="stat-box">
            <div class="stat-label">完工时间</div>
            <div class="stat-value">{{ state.simulation.makespan }}</div>
          </div>
          <div class="stat-box" v-if="state.simulation.solved">
            <div class="stat-label">总成本 (SoC)</div>
            <div class="stat-value highlight">{{ state.simulation.totalCost }}</div>
          </div>
          <div class="stat-box" v-else>
            <div class="stat-label">总路径长</div>
            <div class="stat-value">{{ state.simulation.totalPathLength }}</div>
          </div>
          <div class="stat-box">
            <div class="stat-label">空闲格子</div>
            <div class="stat-value">{{ state.grid.freeCells }}</div>
          </div>
          <div class="stat-box">
            <div class="stat-label">连通分量</div>
            <div class="stat-value">{{ state.grid.components }}</div>
          </div>
        </div>
      </div>

      <div class="section">
        <div class="section-title">地图</div>
        <div class="control-row">
          <span class="control-label">宽度</span>
          <div class="number-input">
            <button @click="updateCfg('width', cfg.width - 1)" :disabled="cfg.width <= 5">−</button>
            <span>{{ cfg.width }}</span>
            <button @click="updateCfg('width', cfg.width + 1)" :disabled="cfg.width >= 80">+</button>
          </div>
        </div>
        <div class="control-row">
          <span class="control-label">高度</span>
          <div class="number-input">
            <button @click="updateCfg('height', cfg.height - 1)" :disabled="cfg.height <= 5">−</button>
            <span>{{ cfg.height }}</span>
            <button @click="updateCfg('height', cfg.height + 1)" :disabled="cfg.height >= 80">+</button>
          </div>
        </div>
        <div class="slider-row">
          <span class="control-label" style="min-width:auto">障碍物比例</span>
          <input type="range" min="0" max="0.6" step="0.02" v-model.number="cfg.obstacle_ratio" @change="configure" />
          <span class="slider-value">{{ (cfg.obstacle_ratio * 100).toFixed(0) }}%</span>
        </div>
      </div>

      <div class="section">
        <div class="section-title">车辆</div>
        <div class="control-row">
          <span class="control-label">数量</span>
          <div class="number-input">
            <button @click="updateCfg('num_agents', cfg.num_agents - 1)" :disabled="cfg.num_agents <= 1">−</button>
            <span>{{ cfg.num_agents }}</span>
            <button @click="updateCfg('num_agents', cfg.num_agents + 1)" :disabled="cfg.num_agents >= 60">+</button>
          </div>
        </div>
      </div>

      <div class="section">
        <div class="section-title">规划算法</div>
        <select v-model="cfg.algo" @change="configure">
          <option v-for="a in state.algorithms" :key="a" :value="a">{{ a }}</option>
        </select>
        <div class="regen-row">
          <span class="regen-label">重置</span>
          <div class="regen-grid">
            <button class="btn btn-ghost" @click="regenObstacles">🧱 障碍物</button>
            <button class="btn btn-ghost" @click="regenStarts">🚩 起点</button>
            <button class="btn btn-ghost" @click="regenGoals">🎯 目标</button>
          </div>
        </div>
        <div class="btn-group">
          <button class="btn btn-secondary" @click="regenAll">🔄 全部重置</button>
          <button class="btn btn-primary" @click="replan">⚡ 开始规划</button>
        </div>
      </div>

      <div class="section">
        <div class="section-title">播放</div>
        <div class="slider-row">
          <span class="control-label" style="min-width:auto">车辆速度</span>
          <input type="range" min="1" max="20" step="1" v-model.number="fps" />
          <span class="slider-value">{{ fps }}x</span>
        </div>
      </div>

      <div class="section">
        <div class="section-title">车辆列表 ({{ state.agents.length }})</div>
        <div class="agents-list">
          <div
            v-for="a in state.agents"
            :key="a.id"
            class="agent-item"
            :class="{ selected: selectedAgentId === a.id }"
            @click="selectedAgentId = a.id"
          >
            <div class="agent-dot" :style="{ background: `rgb(${a.color.join(',')})` }"></div>
            <div class="agent-info">
              <div class="agent-id">车辆 #{{ a.id }}</div>
              <div class="agent-pathlen">路径: {{ a.pathLength }} 步</div>
            </div>
            <div class="agent-status">
              <span v-if="a.pathLength === 0" class="agent-fail">✗</span>
              <span v-else class="agent-done">✓</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted, onUnmounted } from 'vue'
import MapCanvas from './components/MapCanvas.vue'

const state = ref(null)
const planning = ref(false)
const paused = ref(false)
const fps = ref(3)
const currentStep = ref(0)
const selectedAgentId = ref(null)
const ws = ref(null)

const cfg = reactive({
  width: 20,
  height: 20,
  obstacle_ratio: 0.2,
  num_agents: 5,
  algo: 'Prioritized Planning',
  obstacle_seed: null,
  start_seed: null,
  goal_seed: null,
})

const makespan = computed(() => state.value?.simulation?.makespan || 0)

let stepTimer = null

function connectWS() {
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:'
  ws.value = new WebSocket(`${proto}//${location.host}/ws`)
  ws.value.onmessage = (ev) => {
    try {
      const data = JSON.parse(ev.data)
      state.value = data
      if (data.config) Object.assign(cfg, {
        width: data.config.width,
        height: data.config.height,
        obstacle_ratio: data.config.obstacle_ratio,
        num_agents: data.config.num_agents,
        algo: data.config.algo,
        obstacle_seed: data.config.obstacle_seed,
        start_seed: data.config.start_seed,
        goal_seed: data.config.goal_seed,
      })
      if (justConfigured) {
        currentStep.value = 0
        justConfigured = false
      }
      planning.value = false
    } catch (e) {}
  }
  ws.value.onclose = () => {
    setTimeout(connectWS, 1500)
  }
}

function sendWS(msg) {
  if (ws.value?.readyState === WebSocket.OPEN) {
    ws.value.send(JSON.stringify(msg))
  }
}

async function fetchState() {
  try {
    const r = await fetch('/api/state')
    const d = await r.json()
    state.value = d
    if (d.config) Object.assign(cfg, {
      width: d.config.width,
      height: d.config.height,
      obstacle_ratio: d.config.obstacle_ratio,
      num_agents: d.config.num_agents,
      algo: d.config.algo,
      obstacle_seed: d.config.obstacle_seed,
      start_seed: d.config.start_seed,
      goal_seed: d.config.goal_seed,
    })
  } catch (e) {}
}

let justConfigured = false
let cfgTimer = null

function configure() {
  if (cfgTimer) clearTimeout(cfgTimer)
  cfgTimer = setTimeout(() => {
    justConfigured = true
    sendWS({ action: 'configure', config: {
      algo: cfg.algo,
      obstacle_ratio: cfg.obstacle_ratio,
      width: cfg.width,
      height: cfg.height,
      num_agents: cfg.num_agents,
    }})
  }, 150)
}

function updateCfg(key, val) {
  cfg[key] = val
  configure()
}

function replan() {
  planning.value = true
  justConfigured = true
  sendWS({ action: 'plan', config: {
    algo: cfg.algo,
    obstacle_ratio: cfg.obstacle_ratio,
    width: cfg.width,
    height: cfg.height,
    num_agents: cfg.num_agents,
  }})
}

function regenAll() {
  justConfigured = true
  sendWS({ action: 'regen-all', config: { algo: cfg.algo } })
}

function regenObstacles() {
  justConfigured = true
  sendWS({ action: 'regen-obstacles', config: { algo: cfg.algo } })
}

function regenStarts() {
  justConfigured = true
  sendWS({ action: 'regen-starts', config: { algo: cfg.algo } })
}

function regenGoals() {
  justConfigured = true
  sendWS({ action: 'regen-goals', config: { algo: cfg.algo } })
}

function onSeek() {
  sendWS({ action: 'step', step: currentStep.value })
}

function stepFwd() {
  if (currentStep.value < makespan.value) {
    currentStep.value++
    sendWS({ action: 'step', step: currentStep.value })
  }
}

function stepBack() {
  if (currentStep.value > 0) {
    currentStep.value--
    sendWS({ action: 'step', step: currentStep.value })
  }
}

function resetSteps() {
  currentStep.value = 0
  sendWS({ action: 'reset-steps' })
}

function goEnd() {
  currentStep.value = makespan.value
  sendWS({ action: 'step', step: currentStep.value })
}

function togglePause() {
  paused.value = !paused.value
}

function tick() {
  if (!paused.value && currentStep.value < makespan.value) {
    currentStep.value++
    sendWS({ action: 'step', step: currentStep.value })
  }
}

watch(fps, (v) => {
  if (stepTimer) clearInterval(stepTimer)
  stepTimer = setInterval(tick, 1000 / v)
})

onMounted(() => {
  fetchState()
  connectWS()
  stepTimer = setInterval(tick, 1000 / fps.value)
})

onUnmounted(() => {
  if (stepTimer) clearInterval(stepTimer)
})
</script>