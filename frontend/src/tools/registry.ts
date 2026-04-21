import type { Component } from 'vue'
import ServiceIdRegistryPanel from '@/components/tool-detail/ServiceIdRegistryPanel.vue'
import MosIntegrationToolboxPanel from '@/components/tool-detail/MosIntegrationToolboxPanel.vue'
import ServiceIdRegistryManageTab from '@/components/tool-manage/ServiceIdRegistryManageTab.vue'
import MosIntegrationToolboxManageTab from '@/components/tool-manage/MosIntegrationToolboxManageTab.vue'

export type ManageTabSpec = {
  name: string
  label: string
  component: Component
}

/** Keys equal `Tool.name` from the API and backend `tool.manifest.json` tool_key */
const toolDetailByKey: Record<string, Component> = {
  'service-id-registry': ServiceIdRegistryPanel,
  'mos-integration-toolbox': MosIntegrationToolboxPanel,
}

const toolManageExtraTabsByKey: Record<string, ManageTabSpec[]> = {
  'service-id-registry': [
    {
      name: 'service-id-registry',
      label: '服务 ID 治理',
      component: ServiceIdRegistryManageTab,
    },
  ],
  'mos-integration-toolbox': [
    {
      name: 'mos-toolbox-manage',
      label: 'MOS 工具配置',
      component: MosIntegrationToolboxManageTab,
    },
  ],
}

export function resolveToolDetailPanel(toolName: string | undefined): Component | null {
  if (!toolName) return null
  return toolDetailByKey[toolName] ?? null
}

export function resolveManageExtraTabs(toolName: string | undefined): ManageTabSpec[] {
  if (!toolName) return []
  return toolManageExtraTabsByKey[toolName] ?? []
}
