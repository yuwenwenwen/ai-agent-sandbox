
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

  if (running.value[id] || generating.value[id]) {
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
    delete files.value[id]
    delete listingFiles.value[id]

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
  } catch (error) {
    results.value[id] = {
      error: error.message,
    }

    messages.value[id] = '執行時發生錯誤'
  } finally {
    running.value[id] = false
  }
}

const files = ref({})
const listingFiles = ref({})

async function listFiles(id) {
  listingFiles.value[id] = true

  try {
    const response = await fetch(
      `/api/sandboxes/${encodeURIComponent(id)}/files`
    )

    const data = await response.json()

    if (!response.ok) {
      throw new Error(data.detail || '取得檔案失敗')
    }

    files.value[id] = data.files
  } catch (error) {
    message.value = error.message
  } finally {
    listingFiles.value[id] = false
  }
}

// 頁面載入時取得 Sandbox
onMounted(loadSandboxes)
</script>

<template>
  <main class="container">
    <h1>AI Agent Sandbox</h1>

    <p class="subtitle">
      Vue 3 + FastAPI + Docker + Gemini
    </p>

    <button
      class="create"
      :disabled="loading"
      @click="createSandbox"
    >
      {{ loading ? 'Creating...' : '+ Create Sandbox' }}
    </button>

    <p v-if="message" class="message">
      {{ message }}
    </p>

    <h2>Sandbox List</h2>

    <p v-if="sandboxes.length === 0" class="empty">
      目前沒有 Sandbox
    </p>

    <div
      v-for="sandbox in sandboxes"
      :key="sandbox.id"
      class="sandbox"
    >
      <p class="sandbox-id">
        <strong>ID:</strong>
        {{ sandbox.id }}
      </p>

      <p
        class="status"
        :class="{ stopped: sandbox.status !== 'running' }"
      >
        Status: {{ sandbox.status }}
      </p>

      <!-- 每個 Sandbox 獨立的 AI 任務 -->
      <div class="ai-panel">
        <h3>AI Agent</h3>

        <label :for="'task-' + sandbox.id">
          AI Task
        </label>

        <textarea
          :id="'task-' + sandbox.id"
          v-model="aiTasks[sandbox.id]"
          placeholder="例如：請用 Python 計算 1 到 100 的平均"
          rows="3"
        ></textarea>

        <button
          class="generate"
          :disabled="
            generating[sandbox.id] ||
            running[sandbox.id] ||
            sandbox.status !== 'running'
          "
          @click="generateCode(sandbox.id)"
        >
          {{
            generating[sandbox.id]
              ? 'Generating...'
              : '✨ Generate with Gemini'
          }}
        </button>
      </div>

      <!-- 每個 Sandbox 獨立的 Python 程式碼 -->
      <div class="code-panel">
        <label :for="'code-' + sandbox.id">
          Python Code
        </label>

        <textarea
          :id="'code-' + sandbox.id"
          v-model="codes[sandbox.id]"
          placeholder="請輸入 Python 程式碼，或使用 Gemini 產生"
          rows="7"
          spellcheck="false"
        ></textarea>
      </div>

      <p
        v-if="messages[sandbox.id]"
        class="sandbox-message"
      >
        {{ messages[sandbox.id] }}
      </p>

      <div class="actions">
        <button
          class="run"
          :disabled="
            running[sandbox.id] ||
            generating[sandbox.id] ||
            sandbox.status !== 'running'
          "
          @click="runPython(sandbox.id)"
        >
          {{
            running[sandbox.id]
              ? 'Running...'
              : '▶ Run Python'
          }}
        </button>

        <button
          :disabled="listingFiles[sandbox.id] ||
                    sandbox.status !== 'running'"
          @click="listFiles(sandbox.id)"
        >
          {{ listingFiles[sandbox.id] ? 'Loading...' : '📁 List Files' }}
        </button>

        <div v-if="files[sandbox.id]">
          <h3>Files in /tmp</h3>

          <p v-if="files[sandbox.id].length === 0">
            No files found
          </p>

          <ul v-else>
            <li
              v-for="file in files[sandbox.id]"
              :key="file"
            >
              {{ file }}
            </li>
          </ul>
        </div>

        <button
          class="delete"
          :disabled="
            running[sandbox.id] ||
            generating[sandbox.id]
          "
          @click="deleteSandbox(sandbox.id)"
        >
          Delete
        </button>
      </div>

      <!-- 每個 Sandbox 獨立的執行結果 -->
      <div
        v-if="results[sandbox.id]"
        class="result"
      >
        <h3>Execution Result</h3>

        <p
          v-if="results[sandbox.id].error"
          class="error"
        >
          {{ results[sandbox.id].error }}
        </p>

        <template v-else>
          <p>
            Exit code:
            <strong>
              {{ results[sandbox.id].exit_code }}
            </strong>
          </p>

          <h4>stdout</h4>

          <pre>{{ results[sandbox.id].stdout || '(empty)' }}</pre>

          <h4>stderr</h4>

          <pre>{{ results[sandbox.id].stderr || '(empty)' }}</pre>
        </template>
      </div>
    </div>
  </main>
</template>

<style scoped>
.container {
  max-width: 800px;
  margin: 50px auto;
  padding: 0 20px;
  font-family: Arial, sans-serif;
}

h1 {
  margin-bottom: 8px;
  text-align: center;
}

h2 {
  margin-top: 30px;
}

.subtitle {
  color: #64748b;
  text-align: center;
}

.message {
  color: #475569;
}

.empty {
  color: #64748b;
}

button {
  padding: 10px 16px;
  border: none;
  border-radius: 6px;
  color: white;
  cursor: pointer;
}

button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.create {
  display: block;
  margin: 20px auto;
  background: #2563eb;
}

.run {
  background: #16a34a;
}

.delete {
  background: #dc2626;
}

.generate {
  margin-top: 12px;
  background: #7c3aed;
}

.sandbox {
  margin-top: 20px;
  padding: 24px;
  border-radius: 10px;
  background: white;
  box-shadow: 0 2px 12px #00000012;
  overflow-wrap: anywhere;
}

.sandbox-id {
  margin-bottom: 8px;
}

.status {
  color: #15803d;
  font-weight: bold;
}

.status.stopped {
  color: #d97706;
}

.ai-panel {
  margin: 24px 0;
  padding: 20px;
  border-radius: 10px;
  background: #f0f7ff;
}

.ai-panel h3 {
  margin-top: 0;
}

.code-panel {
  margin-top: 24px;
}

label {
  display: block;
  margin: 12px 0 8px;
  font-weight: bold;
}

textarea {
  box-sizing: border-box;
  width: 100%;
  padding: 12px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  font-family: monospace;
  font-size: 14px;
  resize: vertical;
}

textarea:focus {
  outline: 2px solid #93c5fd;
}

.actions {
  display: flex;
  gap: 10px;
  margin-top: 16px;
}

.sandbox-message {
  color: #475569;
  margin: 12px 0;
}

.result {
  margin-top: 20px;
  padding: 20px;
  border-radius: 8px;
  background: #f1f5f9;
}

.result h4 {
  margin-bottom: 6px;
}

pre {
  padding: 12px;
  border-radius: 6px;
  background: #1e293b;
  color: #e2e8f0;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.error {
  color: #dc2626;
}
</style>
