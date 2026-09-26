
<script setup>
import { ref, onMounted } from 'vue'

const sandboxes = ref([])
const message = ref('')
const loading = ref(false)

// 每個 Sandbox 都有自己的程式碼、結果及執行狀態
const codes = ref({})
const results = ref({})
const running = ref({})

async function loadSandboxes() {
  try {
    const response = await fetch('/api/sandboxes')
    if (!response.ok) throw new Error('無法取得 Sandbox 清單')

    sandboxes.value = await response.json()
  } catch (error) {
    message.value = error.message
  }
}

async function createSandbox() {
  loading.value = true
  message.value = '正在建立 Sandbox...'

  try {
    const response = await fetch('/api/sandboxes', {
      method: 'POST',
    })

    if (!response.ok) throw new Error('建立失敗')

    message.value = 'Sandbox 建立成功！'
    await loadSandboxes()
  } catch (error) {
    message.value = error.message
  } finally {
    loading.value = false
  }
}

async function deleteSandbox(id) {
  if (!confirm('確定要刪除這個 Sandbox 嗎？')) return

  try {
    const response = await fetch(
      `/api/sandboxes/${encodeURIComponent(id)}`,
      { method: 'DELETE' }
    )

    if (!response.ok) throw new Error('刪除失敗')

    delete codes.value[id]
    delete results.value[id]
    message.value = 'Sandbox 已刪除'
    await loadSandboxes()
  } catch (error) {
    message.value = error.message
  }
}

// 新增：在指定 Sandbox 執行 Python
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

  try {
    const response = await fetch(
      `/api/sandboxes/${encodeURIComponent(id)}/execute`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ code }),
      }
    )

    const data = await response.json()

    if (!response.ok) {
      throw new Error(data.detail || '執行失敗')
    }

    results.value[id] = data
  } catch (error) {
    results.value[id] = {
      error: error.message,
    }
  } finally {
    running.value[id] = false
  }
}

onMounted(loadSandboxes)
</script>

<template>
  <main class="container">
    <h1>AI Agent Sandbox</h1>
    <p class="subtitle">Vue 3 + FastAPI + Docker</p>

    <button
      class="create"
      :disabled="loading"
      @click="createSandbox"
    >
      {{ loading ? 'Creating...' : '+ Create Sandbox' }}
    </button>

    <p class="message">{{ message }}</p>

    <h2>Sandbox List</h2>

    <p v-if="sandboxes.length === 0">
      目前沒有 Sandbox
    </p>

    <div
      v-for="sandbox in sandboxes"
      :key="sandbox.id"
      class="sandbox"
    >
      <p><strong>ID:</strong> {{ sandbox.id }}</p>

      <p class="status">
        Status: {{ sandbox.status }}
      </p>

      <label :for="'code-' + sandbox.id">
        Python Code
      </label>

      <textarea
        :id="'code-' + sandbox.id"
        v-model="codes[sandbox.id]"
        placeholder="print('Hello from Sandbox!')"
        spellcheck="false"
        rows="6"
        :disabled="sandbox.status !== 'running'"
      ></textarea>

      <div class="actions">
        <button
          class="run"
          :disabled="
            running[sandbox.id] ||
            sandbox.status !== 'running'
          "
          @click="runPython(sandbox.id)"
        >
          {{ running[sandbox.id] ? 'Running...' : '▶ Run Python' }}
        </button>

        <button
          class="delete"
          :disabled="running[sandbox.id]"
          @click="deleteSandbox(sandbox.id)"
        >
          Delete
        </button>
      </div>

      <div
        v-if="results[sandbox.id]"
        class="result"
      >
        <h3>Execution Result</h3>

        <p v-if="results[sandbox.id].error" class="error">
          {{ results[sandbox.id].error }}
        </p>

        <template v-else>
          <p>
            Exit code:
            <strong>{{ results[sandbox.id].exit_code }}</strong>
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

.subtitle {
  color: #64748b;
}

.message {
  color: #475569;
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
  background: #2563eb;
}

.run {
  background: #16a34a;
}

.delete {
  background: #dc2626;
}

.sandbox {
  background: white;
  padding: 18px;
  margin-top: 15px;
  border-radius: 8px;
  box-shadow: 0 2px 8px #00000012;
  overflow-wrap: anywhere;
}

.status {
  color: #15803d;
}

label {
  display: block;
  margin: 20px 0 8px;
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

.actions {
  display: flex;
  gap: 10px;
  margin-top: 12px;
}

.result {
  margin-top: 20px;
  padding: 15px;
  border-radius: 6px;
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
