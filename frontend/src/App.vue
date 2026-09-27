
<script setup>
import { ref, onMounted } from 'vue'

// Sandbox 清單及建立狀態
const sandboxes = ref([])
const message = ref('')
const loading = ref(false)

// 每個 Sandbox 使用自己的 ID 儲存資料
const codes = ref({})
const aiTasks = ref({})
const results = ref({})
const running = ref({})
const generating = ref({})
const messages = ref({})
const workspaceFiles = ref({})
const uploading = ref({})
const refreshing = ref({})
const uploadInputs = ref({})

// 取得 Sandbox 清單
async function loadSandboxes() {
  try {
    const response = await fetch('/api/sandboxes')

    if (!response.ok) {
      throw new Error('無法取得 Sandbox 清單')
    }

    sandboxes.value = await response.json()
  } catch (error) {
    message.value = error.message
  }
}

// 建立 Sandbox
async function createSandbox() {
  loading.value = true
  message.value = '正在建立 Sandbox...'

  try {
    const response = await fetch('/api/sandboxes', {
      method: 'POST',
    })

    if (!response.ok) {
      throw new Error('建立 Sandbox 失敗')
    }

    const sandbox = await response.json()

    // 初始化新 Sandbox 的前端資料
    codes.value[sandbox.id] = ''
    aiTasks.value[sandbox.id] = ''
    results.value[sandbox.id] = null
    messages.value[sandbox.id] = ''

    message.value = 'Sandbox 建立成功！'

    await loadSandboxes()
  } catch (error) {
    message.value = error.message
  } finally {
    loading.value = false
  }
}

// 刪除 Sandbox
async function deleteSandbox(id) {
  if (!confirm('確定要刪除這個 Sandbox 嗎？')) {
    return
  }

  if (running.value[id] || generating.value[id] || uploading.value[id]) {
    messages.value[id] = '請等待目前的操作完成'
    return
  }

  try {
    const response = await fetch(
      `/api/sandboxes/${encodeURIComponent(id)}`,
      {
        method: 'DELETE',
      }
    )

    if (!response.ok) {
      throw new Error('刪除 Sandbox 失敗')
    }

    // 刪除成功後，清除這個 Sandbox 的前端資料
    delete codes.value[id]
    delete aiTasks.value[id]
    delete results.value[id]
    delete running.value[id]
    delete generating.value[id]
    delete messages.value[id]
    delete workspaceFiles.value[id]
    delete uploading.value[id]
    delete uploadInputs.value[id]
    delete refreshing.value[id]

    message.value = 'Sandbox 已刪除'

    await loadSandboxes()
  } catch (error) {
    messages.value[id] = error.message
  }
}

// 使用 Gemini 產生 Python 程式碼
async function generateCode(id) {
  const task = aiTasks.value[id]?.trim()

  if (!task) {
    messages.value[id] = '請先輸入 AI 任務'
    return
  }

  generating.value[id] = true
  messages.value[id] = 'Gemini 正在產生程式碼...'

  try {
    const response = await fetch('/api/agent/generate', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        task: task,
      }),
    })

    const data = await response.json()

    if (!response.ok) {
      throw new Error(
        typeof data.detail === 'string'
          ? data.detail
          : 'Gemini 產生程式碼失敗'
      )
    }

    if (typeof data.code !== 'string') {
      throw new Error('Gemini 未回傳有效的程式碼')
    }

    // 只更新指定 Sandbox 的 Python Code
    codes.value[id] = data.code

    // 清除該 Sandbox 上一次的執行結果
    results.value[id] = null

    messages.value[id] =
      '程式碼產生成功！請確認程式碼後，再按 Run Python。'
  } catch (error) {
    messages.value[id] = error.message
  } finally {
    generating.value[id] = false
  }
}

// 在指定 Sandbox 執行 Python
async function runPython(id) {
  const code = codes.value[id] || ''

  if (!code.trim()) {
    results.value[id] = {
      error: '請先輸入 Python 程式碼',
    }
    return
  }

  running.value[id] = true
  results.value[id] = null
  messages.value[id] = '正在執行 Python...'

  try {
    const response = await fetch(
      `/api/sandboxes/${encodeURIComponent(id)}/execute`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          code: code,
        }),
      }
    )

    const data = await response.json()

    if (!response.ok) {
      throw new Error(
        typeof data.detail === 'string'
          ? data.detail
          : 'Python 執行失敗'
      )
    }

    results.value[id] = data
    messages.value[id] = 'Python 執行完成'
    await refreshWorkspace(id).catch(() => {})
  } catch (error) {
    results.value[id] = {
      error: error.message,
    }

    messages.value[id] = '執行時發生錯誤'
  } finally {
    running.value[id] = false
  }
}

// Each Sandbox has its own file picker and upload state.
function chooseFile(id) {
  uploadInputs.value[id]?.click()
}

async function refreshWorkspace(id) {
  refreshing.value[id] = true
  try {
    const response = await fetch(`/api/sandboxes/${encodeURIComponent(id)}/workspace-files`)
    const data = await response.json()
    if (!response.ok) throw new Error(data.detail || '讀取檔案失敗')
    workspaceFiles.value[id] = data.files
  } finally {
    refreshing.value[id] = false
  }
}

async function uploadFile(id, event) {
  const input = event.target
  const file = input.files?.[0]
  if (!file) return
  if (file.size > 5 * 1024 * 1024) {
    messages.value[id] = '檔案不可超過 5 MB'
    input.value = ''
    return
  }
  uploading.value[id] = true
  try {
    const form = new FormData()
    form.append('file', file)
    const response = await fetch(`/api/sandboxes/${encodeURIComponent(id)}/files`, {
      method: 'POST', body: form
    })
    const data = await response.json()
    if (!response.ok) throw new Error(data.detail || '上傳失敗')
    messages.value[id] = `${file.name} 已存入此 Sandbox 的 /workspace/`
    await refreshWorkspace(id)
  } catch (error) {
    messages.value[id] = error.message
  } finally {
    uploading.value[id] = false
    input.value = ''
  }
}

// 頁面載入時取得 Sandbox
onMounted(loadSandboxes)
</script>

<template>
  <main class="dashboard">
    <header class="page-header">
      <div>
        <div class="eyebrow">DOCKER · ISOLATED WORKSPACES</div>
        <h1>AI Agent Sandbox</h1>
        <p class="subtitle">Vue 3 + FastAPI + Docker + Gemini</p>
      </div>
      <button class="btn btn-primary create" :disabled="loading" @click="createSandbox">
        {{ loading ? '建立中...' : '＋ Create Sandbox' }}
      </button>
    </header>

    <p v-if="message" class="global-message" role="status">{{ message }}</p>

    <div class="section-heading">
      <h2>Sandboxes <span class="count">{{ sandboxes.length }}</span></h2>
      <span class="section-tip">每個容器擁有獨立的 /workspace</span>
    </div>

    <div v-if="sandboxes.length === 0" class="empty">目前沒有 Sandbox，請按右上角建立。</div>

    <div v-else class="sandbox-grid">
      <article v-for="(sandbox, index) in sandboxes" :key="sandbox.id" class="sandbox-card">
        <div class="card-header">
          <div class="card-title-wrap">
            <span class="sandbox-icon">{{ index + 1 }}</span>
            <div class="card-title">
              <h3>Sandbox {{ index + 1 }}</h3>
              <span class="sandbox-id" :title="sandbox.id">{{ sandbox.id }}</span>
            </div>
          </div>
          <span class="status" :class="{ stopped: sandbox.status !== 'running' }">
            <span class="status-dot"></span>{{ sandbox.status }}
          </span>
        </div>

        <div class="card-body">
          <section class="panel ai-panel">
            <div class="panel-heading"><span class="panel-icon">✧</span><h4>AI Agent</h4></div>
            <label :for="'task-' + sandbox.id">AI Task</label>
            <textarea :id="'task-' + sandbox.id" v-model="aiTasks[sandbox.id]"
              placeholder="例如：讀取 /workspace/data.csv 並計算平均值" rows="3"></textarea>
            <button class="btn btn-purple" :disabled="generating[sandbox.id] || running[sandbox.id] || sandbox.status !== 'running'"
              @click="generateCode(sandbox.id)">
              {{ generating[sandbox.id] ? '產生中...' : '✧ Generate with Gemini' }}
            </button>
          </section>

          <section class="panel code-panel">
            <div class="panel-heading"><span class="panel-icon">&lt;/&gt;</span><h4>Python Code</h4></div>
            <label :for="'code-' + sandbox.id" class="sr-only">Python Code</label>
            <textarea :id="'code-' + sandbox.id" v-model="codes[sandbox.id]"
              placeholder="輸入 Python 程式碼，或使用 Gemini 產生" rows="7" spellcheck="false" class="code-editor"></textarea>
            <button class="btn btn-green" :disabled="running[sandbox.id] || generating[sandbox.id] || sandbox.status !== 'running'"
              @click="runPython(sandbox.id)">
              {{ running[sandbox.id] ? '執行中...' : '▶ Run Python' }}
            </button>
          </section>

          <p v-if="messages[sandbox.id]" class="sandbox-message" role="status">{{ messages[sandbox.id] }}</p>

          <section class="panel files-panel">
            <div class="panel-heading files-heading">
              <div class="file-title"><span class="panel-icon">▣</span><h4>檔案管理 <small>/workspace</small></h4></div>
              <span class="file-count">{{ workspaceFiles[sandbox.id]?.length ?? 0 }} files</span>
            </div>
            <input :ref="el => { if (el) uploadInputs[sandbox.id] = el }"
              type="file" accept=".csv,.txt,.json,.py" class="hidden-file-input"
              @change="uploadFile(sandbox.id, $event)" />
            <div class="file-actions">
              <button class="btn btn-primary" :disabled="uploading[sandbox.id] || sandbox.status !== 'running'"
                @click="chooseFile(sandbox.id)">
                {{ uploading[sandbox.id] ? '上傳中...' : '＋ 新增檔案' }}
              </button>
              <button class="btn btn-secondary" :disabled="refreshing[sandbox.id] || sandbox.status !== 'running'"
                @click="refreshWorkspace(sandbox.id).catch(error => messages[sandbox.id] = error.message)">
                {{ refreshing[sandbox.id] ? '整理中...' : '↻ 重新整理' }}
              </button>
            </div>
            <p class="file-hint">CSV、TXT、JSON、PY · 最大 5 MB · 不與其他 Sandbox 共用</p>
            <div class="file-list">
              <p v-if="workspaceFiles[sandbox.id] === undefined || workspaceFiles[sandbox.id] === null" class="file-empty">尚未取得檔案清單</p>
              <p v-else-if="workspaceFiles[sandbox.id].length === 0" class="file-empty">/workspace 目前沒有檔案</p>
              <ul v-else>
                <li v-for="name in workspaceFiles[sandbox.id]" :key="name" :title="name">
                  <span aria-hidden="true">📄</span><span>{{ name }}</span>
                </li>
              </ul>
            </div>
          </section>

          <section v-if="results[sandbox.id]" class="panel result-panel">
            <div class="panel-heading"><span class="panel-icon">›_</span><h4>Execution Result</h4></div>
            <p v-if="results[sandbox.id].error" class="error">{{ results[sandbox.id].error }}</p>
            <template v-else>
              <p class="exit-code">Exit code: <strong :class="{ error: results[sandbox.id].exit_code !== 0 }">{{ results[sandbox.id].exit_code }}</strong></p>
              <div class="output-label">stdout</div>
              <pre>{{ results[sandbox.id].stdout || '(empty)' }}</pre>
              <div class="output-label">stderr</div>
              <pre>{{ results[sandbox.id].stderr || '(empty)' }}</pre>
            </template>
          </section>
        </div>

        <footer class="card-footer">
          <button class="btn btn-danger-outline"
            :disabled="running[sandbox.id] || generating[sandbox.id] || uploading[sandbox.id]"
            @click="deleteSandbox(sandbox.id)">Delete Sandbox</button>
        </footer>
      </article>
    </div>
  </main>
</template>

<style scoped>
:global(*) { box-sizing: border-box; }
:global(body) { margin: 0; background: #f5f7fb; }
:global(#app) { max-width: none; margin: 0; padding: 0; text-align: left; }
.dashboard { width: min(100%, 1560px); margin: 0 auto; padding: 32px clamp(16px, 3vw, 44px) 64px; font-family: Inter, ui-sans-serif, system-ui, -apple-system, 'Segoe UI', sans-serif; color: #203047; }
.page-header { display: flex; gap: 20px; align-items: center; justify-content: space-between; flex-wrap: wrap; padding-bottom: 24px; border-bottom: 1px solid #e2e8f0; }
.eyebrow { font-size: 11px; font-weight: 800; letter-spacing: 1.5px; color: #4776c3; }
h1 { font-size: clamp(26px, 3vw, 36px); letter-spacing: -1px; margin: 5px 0 4px; color: #14243b; }
.subtitle { margin: 0; color: #64748b; font-size: 14px; }
.section-heading { display: flex; align-items: baseline; justify-content: space-between; flex-wrap: wrap; gap: 8px; margin: 26px 0 16px; }
h2 { margin: 0; font-size: 18px; }
.count { background: #e8efff; color: #2b58ae; padding: 2px 9px; font-size: 13px; border-radius: 99px; }
.section-tip { color: #64748b; font-size: 12px; }
.global-message { padding: 11px 16px; border-radius: 10px; background: #eaf2ff; color: #234d89; }
.empty { border: 1px dashed #cad5e6; border-radius: 15px; padding: 56px 20px; color: #64748b; text-align: center; }
.sandbox-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 20px; align-items: start; }
.sandbox-card { min-width: 0; background: white; border: 1px solid #e1e8f2; border-radius: 16px; box-shadow: 0 3px 17px #1c345709; overflow: hidden; }
.card-header { display: flex; align-items: center; justify-content: space-between; gap: 10px; padding: 18px 20px; border-bottom: 1px solid #e8edf5; }
.card-title-wrap, .file-title { display: flex; align-items: center; gap: 10px; min-width: 0; }
.sandbox-icon { display: grid; place-items: center; flex: 0 0 36px; width: 36px; height: 36px; border-radius: 10px; background: #edf3ff; color: #3166bb; font-weight: 800; }
.card-title { min-width: 0; }
.card-title h3 { margin: 0 0 4px; font-size: 15px; }
.sandbox-id { color: #8291a6; font-size: 11px; overflow-wrap: anywhere; line-height: 1.2; }
.status { display: inline-flex; gap: 6px; align-items: center; flex-shrink: 0; color: #16834d; background: #e8f8ef; padding: 5px 9px; border-radius: 99px; font-size: 12px; font-weight: 700; }
.status-dot { width: 7px; height: 7px; background: currentColor; border-radius: 99px; }
.status.stopped { color: #a36918; background: #fff3df; }
.card-body { display: grid; gap: 16px; padding: 18px 20px; }
.panel { min-width: 0; }
.panel-heading { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }
.panel-heading h4 { margin: 0; font-size: 14px; color: #243653; }
.panel-icon { display: inline-flex; align-items: center; justify-content: center; color: #4669ac; background: #eaf1ff; width: 27px; height: 27px; border-radius: 7px; font-size: 14px; font-weight: 800; }
.ai-panel { background: #f1f5ff; padding: 14px; border: 1px solid #e0e9ff; border-radius: 12px; }
label { display: block; font-size: 12px; color: #54647a; margin-bottom: 7px; font-weight: 600; }
textarea { width: 100%; border: 1px solid #d7e0ee; background: white; color: #1e293b; border-radius: 8px; padding: 11px; font: 13px/1.5 ui-monospace, 'Cascadia Code', Consolas, monospace; resize: vertical; }
textarea:focus { outline: 2px solid #acc6ff; border-color: #6594e4; }
.code-editor { min-height: 130px; max-height: 260px; }
.btn { border: 0; border-radius: 8px; padding: 10px 13px; font-weight: 700; font-size: 12px; line-height: 1.3; cursor: pointer; transition: filter .15s; white-space: nowrap; }
.btn:hover:not(:disabled) { filter: brightness(.94); }
.btn:disabled { opacity: .48; cursor: not-allowed; }
.btn-primary { background: #2563eb; color: white; }
.btn-purple { background: #7444cf; color: white; margin-top: 10px; }
.btn-green { background: #169754; color: white; margin-top: 10px; }
.btn-secondary { background: #edf2f8; color: #40516b; }
.btn-danger-outline { color: #bf3636; background: #fff4f4; border: 1px solid #ffdada; }
.sandbox-message { color: #3c5684; background: #f0f6ff; border: 1px solid #dce9fc; padding: 10px 12px; border-radius: 8px; margin: 0; font-size: 12px; overflow-wrap: anywhere; }
.files-panel { border: 1px solid #dde5f1; border-radius: 12px; padding: 14px; }
.files-heading { justify-content: space-between; }
.files-heading h4 small { font-weight: 500; font-size: 11px; color: #8190a6; margin-left: 3px; }
.file-count { color: #6f7f97; font-size: 11px; white-space: nowrap; }
.hidden-file-input, .sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0, 0, 0, 0); white-space: nowrap; border: 0; }
.file-actions { display: flex; flex-wrap: wrap; gap: 8px; }
.file-hint { margin: 10px 0; color: #8390a3; font-size: 11px; line-height: 1.5; }
.file-list { background: #f8faff; border-radius: 8px; border: 1px solid #edf1f7; min-height: 48px; max-height: 150px; overflow-y: auto; }
.file-list ul { margin: 0; padding: 6px 10px; list-style: none; }
.file-list li { display: flex; gap: 8px; font-size: 12px; padding: 7px 2px; border-bottom: 1px solid #edf1f7; overflow-wrap: anywhere; }
.file-list li:last-child { border-bottom: 0; }
.file-empty { font-size: 12px; text-align: center; color: #92a0b0; padding: 12px; margin: 0; }
.result-panel { border: 1px solid #dde5f1; border-radius: 12px; padding: 14px; }
.exit-code { color: #64748b; margin: 0 0 10px; font-size: 12px; }
.output-label { font-size: 11px; color: #63748c; font-weight: 800; margin: 9px 0 5px; }
pre { background: #1d2c41; color: #e6eef9; border-radius: 8px; margin: 0; padding: 11px; font: 12px/1.55 ui-monospace, Consolas, monospace; white-space: pre-wrap; overflow-wrap: anywhere; max-height: 200px; overflow-y: auto; }
.error { color: #c83535; }
.card-footer { padding: 13px 20px; border-top: 1px solid #ecf0f6; display: flex; justify-content: flex-end; }
@media (max-width: 980px) { .sandbox-grid { grid-template-columns: 1fr; } }
@media (max-width: 600px) { .dashboard { padding: 18px 12px 40px; } .card-header { padding: 14px; } .card-body { padding: 14px; } .page-header .create { width: 100%; } }
</style>
