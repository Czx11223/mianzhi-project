<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '@/api'
import type { ModelSettings } from '@/types'
import AppCard from '@/components/AppCard.vue'
import AppButton from '@/components/AppButton.vue'
import AppTag from '@/components/AppTag.vue'

const form = ref<ModelSettings>({
  modelName: 'qwen-plus',
  apiKey: '',
  baseUrl: 'https://maas.qianwenaiapi.com/compatible-mode/v1',
  temperature: 0.7,
  maxTokens: 2048
})
const saved = ref(false)
const testing = ref(false)
const testResult = ref<'' | 'ok' | 'fail'>('')
const testMessage = ref('')

onMounted(async () => {
  form.value = await api.getSettings()
})

async function save() {
  await api.saveSettings(form.value)
  form.value = await api.getSettings()
  saved.value = true
  setTimeout(() => (saved.value = false), 2000)
}

// 真实连接测试：先保存当前配置，再由后端用它实际调用一次大模型
async function test() {
  testing.value = true
  testResult.value = ''
  testMessage.value = ''
  try {
    await api.saveSettings(form.value)
    const res = await api.testSettings()
    testResult.value = res.ok ? 'ok' : 'fail'
    testMessage.value = res.message + (res.latencyMs ? `（${res.latencyMs}ms）` : '')
  } catch (e: any) {
    testResult.value = 'fail'
    testMessage.value = '测试请求失败：' + (e?.message || '网络错误')
  } finally {
    testing.value = false
  }
}
</script>

<template>
  <div class="max-w-2xl">
    <div class="mb-6">
      <h1 class="text-h1 text-ink-primary">模型设置</h1>
      <p class="text-body text-ink-secondary mt-1.5">配置用于 AI 点评与出题的大模型。密钥保存在服务端，语音识别会自动复用这里的密钥。</p>
    </div>

    <AppCard title="大模型 API 配置">
      <div class="space-y-5">
        <div class="flex flex-col gap-1.5">
          <label class="text-caption text-ink-secondary">模型名称</label>
          <input
            v-model="form.modelName"
            placeholder="例如 qwen-plus"
            class="h-11 px-3 bg-card border border-line rounded-md text-body text-ink-primary"
          />
          <p class="text-caption text-ink-tertiary">填写服务商实际支持的模型名，写错会返回「Model not exist」。</p>
        </div>

        <div class="flex flex-col gap-1.5">
          <label class="text-caption text-ink-secondary">API 密钥</label>
          <input v-model="form.apiKey" type="password" placeholder="sk-xxxxxxxxxxxxxxxx" class="h-11 px-3 bg-card border border-line rounded-md text-body text-ink-primary" />
          <p class="text-caption text-ink-tertiary">此密钥同时用于 AI 点评与语音识别（内置模型 paraformer-8k-v2）。</p>
        </div>

        <div class="flex flex-col gap-1.5">
          <label class="text-caption text-ink-secondary">Base URL</label>
          <input v-model="form.baseUrl" placeholder="https://maas.qianwenaiapi.com/compatible-mode/v1" class="h-11 px-3 bg-card border border-line rounded-md text-body text-ink-primary" />
        </div>

        <div class="flex flex-col gap-1.5">
          <label class="text-caption text-ink-secondary flex justify-between">
            <span>温度 (Temperature)</span><span class="text-ink-primary tabular-nums">{{ form.temperature }}</span>
          </label>
          <input v-model.number="form.temperature" type="range" min="0" max="1" step="0.1" class="w-full accent-[#007AFF]" />
          <p class="text-caption text-ink-tertiary">越低越稳定保守，越高越发散有创意。点评建议 0.3–0.7。</p>
        </div>

        <div class="flex flex-col gap-1.5">
          <label class="text-caption text-ink-secondary">最大 Token 数</label>
          <input v-model.number="form.maxTokens" type="number" min="256" max="8192" step="256" class="h-11 px-3 bg-card border border-line rounded-md text-body text-ink-primary" />
        </div>
      </div>

      <div class="flex items-center gap-3 mt-6">
        <AppButton variant="primary" @click="save">保存设置</AppButton>
        <AppButton variant="secondary" :disabled="testing" @click="test">{{ testing ? '测试中…' : '连接测试' }}</AppButton>
        <AppTag v-if="saved" tone="success">已保存</AppTag>
        <AppTag v-if="testResult === 'ok'" tone="success">连接正常</AppTag>
        <AppTag v-if="testResult === 'fail'" tone="warning">连接失败</AppTag>
      </div>
      <p v-if="testMessage" class="text-caption text-ink-secondary mt-2 break-all">{{ testMessage }}</p>
    </AppCard>
  </div>
</template>
