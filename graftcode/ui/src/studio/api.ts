import { callGraft } from '../graft'
import type {
  Catalog, Idea, PlanItem, Pipeline, PromptPreview, Rulebook, Run, SecretInfo, SeoReport, Template, WorkspaceDetail, WorkspaceSummary,
} from './types'

// Every call goes through the generated Graft to the Python receiver. Python methods are snake_case;
// the Graft exposes them in camelCase.
async function call<T>(method: string, ...args: unknown[]): Promise<T> {
  const { data } = await callGraft(method, ...args)
  return data as T
}

export const studio = {
  catalog: () => call<Catalog>('studioCatalog'),
  workspaces: () => call<WorkspaceSummary[]>('studioListWorkspaces'),
  createWorkspace: (name: string, siteUrl: string, niche: string, template: 'demo' | 'live') =>
    call<WorkspaceDetail>('studioCreateWorkspace', name, siteUrl, niche, template),
  workspace: (ws: string) => call<WorkspaceDetail>('studioGetWorkspace', ws),
  deleteWorkspace: (ws: string) => call<{ deleted: string }>('studioDeleteWorkspace', ws),
  saveConfig: (ws: string, patch: Record<string, unknown>) => call('studioSaveConfig', ws, JSON.stringify(patch)),
  templates: (ws: string) => call<Template[]>('studioListTemplates', ws),
  saveTemplate: (ws: string, template: Partial<Template> & Pick<Template, 'name' | 'kind' | 'payload'>) => call<Template>('studioSaveTemplate', ws, JSON.stringify(template)),
  deleteTemplate: (ws: string, id: string) => call<Template[]>('studioDeleteTemplate', ws, id),
  setSecret: (ws: string, slot: string, provider: string, key: string) => call<SecretInfo[]>('studioSetSecret', ws, slot, provider, key),
  testKey: (ws: string, provider: string, slot: string) =>
    call<{ ok: boolean | null; message: string }>('studioTestKey', ws, provider, slot),
  deleteSecret: (ws: string, slot: string) => call<SecretInfo[]>('studioDeleteSecret', ws, slot),

  pipeline: (ws: string, id: string) => call<Pipeline>('studioGetPipeline', ws, id),
  savePipeline: (ws: string, p: Pipeline) => call<Pipeline>('studioSavePipeline', ws, JSON.stringify(p)),
  newPipeline: (ws: string, name: string, live: boolean) => call<Pipeline>('studioNewPipeline', ws, name, live),
  deletePipeline: (ws: string, id: string) => call<{ id: string; name: string }[]>('studioDeletePipeline', ws, id),
  previewPrompt: (ws: string, pipelineId: string, nodeId: string, runId: string) =>
    call<PromptPreview>('studioPreviewPrompt', ws, pipelineId, nodeId, runId),

  ideas: (ws: string) => call<Idea[]>('studioListIdeas', ws),
  addIdea: (ws: string, title: string, keyword: string, category: string) => call<Idea[]>('studioAddIdea', ws, title, keyword, category),
  deleteIdea: (ws: string, id: string) => call<Idea[]>('studioDeleteIdea', ws, id),
  plan: (ws: string) => call<PlanItem[]>('studioListPlan', ws),
  savePlanItem: (ws: string, item: Partial<PlanItem>) => call<PlanItem>('studioSavePlanItem', ws, JSON.stringify(item)),
  deletePlanItem: (ws: string, id: string) => call<PlanItem[]>('studioDeletePlanItem', ws, id),

  rulebook: (ws: string) => call<Rulebook>('studioGetRulebook', ws),
  saveRulebook: (ws: string, rb: Rulebook) => call<Rulebook>('studioSaveRulebook', ws, JSON.stringify(rb)),
  addRule: (ws: string, text: string, kind: string, phrases: string) => call<Rulebook>('studioAddCustomRule', ws, text, kind, phrases),

  startRun: (ws: string, pipelineId: string, item: Record<string, string>) =>
    call<Run>('studioStartRun', ws, pipelineId, JSON.stringify(item)),
  startRunForPlanItem: (ws: string, pipelineId: string, itemId: string) =>
    call<Run>('studioStartRunForPlanItem', ws, pipelineId, itemId),
  runNode: (ws: string, runId: string, nodeId: string) => call<Run>('studioRunNode', ws, runId, nodeId),
  runAll: (ws: string, runId: string) => call<Run>('studioRunAll', ws, runId),
  run: (ws: string, runId: string) => call<Run>('studioGetRun', ws, runId),
  runs: (ws: string) => call<Pick<Run, 'id' | 'pipeline_id' | 'status' | 'title'>[]>('studioListRuns', ws),
  resetFrom: (ws: string, runId: string, nodeId: string) => call<Run>('studioResetFrom', ws, runId, nodeId),
  review: (ws: string, runId: string, nodeId: string, decision: 'approve' | 'reject', notes: string, markdown: string) =>
    call<Run>('studioReview', ws, runId, nodeId, decision, notes, markdown),
  saveDraft: (ws: string, runId: string, markdown: string) =>
    call<{ markdown: string; seo: SeoReport }>('studioSaveDraft', ws, runId, markdown),
  draft: (ws: string, runId: string) => call<{ markdown: string; seo: SeoReport }>('studioGetDraft', ws, runId),

  runDue: (ws: string) => call<{ item: string; ok: boolean; error?: string; run_id?: string }[]>('studioRunDue', ws),
  exportWorkflow: (ws: string, cron: string) =>
    call<{ path: string; yaml: string; secrets_needed: { name: string; for: string }[]; cron: string; steps: string[] }>('studioExportWorkflow', ws, cron),
  exportBundle: (ws: string) => call<{ files: { path: string; content: string }[] }>('studioExportBundle', ws),
}

export const errorText = (e: unknown): string => {
  const raw = e instanceof Error ? e.message : String(e)
  // The gateway prefixes errors with "Error: ValueError: ..." and appends a stack trace; show only the message.
  const first = raw.split('\n')[0]
  return first.replace(/^Error:\s*/, '').replace(/^[A-Za-z]+Error:\s*/, '').trim() || 'Something went wrong.'
}
