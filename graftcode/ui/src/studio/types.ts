export type FieldType = 'text' | 'textarea' | 'number' | 'bool' | 'select' | 'llm_provider' | 'model' | 'key_slot'

export interface NodeField {
  key: string
  label: string
  type: FieldType
  help?: string
  default?: string
  options?: [string, string][]
  keyProvider?: string
  keyProviderFrom?: string
}

export interface NodeTypeInfo {
  type: string
  label: string
  group: string
  description: string
  defaults: Record<string, unknown>
  fields: NodeField[]
  ai: boolean
}

export interface LlmProvider {
  id: string
  label: string
  default_model: string
  needs_key: boolean
  models: string[]
}

export interface Catalog {
  nodes: NodeTypeInfo[]
  llm: LlmProvider[]
  keywords: { id: string; label: string; needs_key: boolean }[]
  scrape: { id: string; label: string; needs_key: boolean }[]
  key_providers: string[]
  plan_statuses: string[]
}

export interface WorkspaceSummary {
  id: string
  name: string
  site_url: string
  niche: string
}

export interface WorkspaceConfig {
  name: string
  site_url: string
  niche: string
  voice_prompt: string
  default_provider: string
  default_model: string
  default_key_slot: string
  categories: string[]
  reddit_playbook: string
  github: { repo: string; base_branch: string; path_template: string }
  schedule: { cron: string }
}

export interface SecretInfo {
  slot: string
  provider: string
  masked: string
  updated_at: string
}

export interface WorkspaceDetail {
  id: string
  config: WorkspaceConfig
  secrets: SecretInfo[]
  pipelines: { id: string; name: string; nodes: number }[]
  rule_count: number
  plan_count: number
}

export interface PipelineNode {
  id: string
  type: string
  position: { x: number; y: number }
  config: Record<string, any>
}

export interface PipelineEdge {
  id: string
  source: string
  target: string
}

export interface Pipeline {
  id: string
  name: string
  nodes: PipelineNode[]
  edges: PipelineEdge[]
}

export type NodeStatus = 'pending' | 'running' | 'done' | 'error' | 'awaiting_review'

export interface NodeState {
  status: NodeStatus
  output: Record<string, any> | null
  error: string
  logs: string[]
  started_at: string
  finished_at: string
}

export interface Run {
  id: string
  pipeline_id: string
  title: string
  item: { id?: string; title?: string; keyword?: string; category?: string; notes?: string }
  status: 'ready' | 'running' | 'awaiting_review' | 'done' | 'error'
  order: string[]
  nodes: Record<string, NodeState>
}

export interface PlanItem {
  id: string
  title: string
  category: string
  keyword: string
  notes: string
  source: string
  scheduled_for: string
  pipeline_id: string
  status: string
  run_id: string
}

export interface Idea {
  id: string
  title: string
  source: string
  keyword: string
  category: string
  note: string
}

export interface Rule {
  id: string
  kind: string
  text: string
  evidence: string
  params: Record<string, any>
  enabled: boolean
  source: 'learned' | 'custom'
  edited?: boolean
}

export interface Rulebook {
  rules: Rule[]
  stats: Record<string, any>
  sources: { url: string; title: string }[]
  updated_at: string
}

export interface SeoCheck {
  id: string
  label: string
  ok: boolean
  detail: string
  severity: string
  fix: string
}

export interface SeoReport {
  score: number
  checks: SeoCheck[]
  keyword: string
  keyword_uses: number
  words: number
  title: string
  slug: string
  meta_description: string
  faq_schema: unknown
  faq_script: string
  rules: { rule_id: string; text: string; ok: boolean; detail: string }[]
}

export interface PromptPreview {
  system: string
  user: string
  provider: string
  model: string
  key_slot: string
  missing_inputs: string[]
}
