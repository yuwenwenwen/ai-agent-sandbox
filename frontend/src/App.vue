
<script setup>
import { ref, onMounted } from 'vue'

const sandboxes = ref([])
const message = ref('')
const loading = ref(false)

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

    message.value = 'Sandbox 已刪除'
    await loadSandboxes()
  } catch (error) {
    message.value = error.message
  }
}

onMounted(loadSandboxes)
</script>

<template>
  <main class="container">
    <h1>AI Agent Sandbox</h1>
    <p>Vue 3 + FastAPI + Docker</p>

    <button
      class="create"
      :disabled="loading"
      @click="createSandbox"
    >
      {{ loading ? 'Creating...' : '+ Create Sandbox' }}
    </button>

    <p>{{ message }}</p>

    <h2>Sandbox List</h2>

    <p v-if="sandboxes.length === 0">
      目前沒有 Sandbox
    </p>

    <div
      v-for="sandbox in sandboxes"
      :key="sandbox.id"
      class="sandbox"
    >
      <p>ID: {{ sandbox.id }}</p>
      <p class="status">Status: {{ sandbox.status }}</p>

      <button
        class="delete"
        @click="deleteSandbox(sandbox.id)"
      >
        Delete
      </button>
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

.create, .delete {
  padding: 10px 16px;
  border: none;
  border-radius: 6px;
  color: white;
  cursor: pointer;
}

.create { background: #2563eb; }
.delete { background: #dc2626; }

.sandbox {
  background: white;
  padding: 18px;
  margin-top: 15px;
  border-radius: 8px;
  box-shadow: 0 2px 8px #00000012;
  overflow-wrap: anywhere;
}

.status { color: #15803d; }
</style>
