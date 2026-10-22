import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { errorText, studio } from './api'
import type { Catalog, WorkspaceDetail, WorkspaceSummary } from './types'

interface Toast {
  id: number
  text: string
  kind: 'error' | 'info'
}

interface StudioState {
  catalog: Catalog | null
  workspaces: WorkspaceSummary[]
  wsId: string
  detail: WorkspaceDetail | null
  loading: boolean
  connected: boolean
  toasts: Toast[]
  selectWorkspace: (id: string) => void
  refreshWorkspaces: () => Promise<WorkspaceSummary[]>
  refreshDetail: () => Promise<void>
  notify: (text: string, kind?: 'error' | 'info') => void
  fail: (err: unknown) => void
  dismiss: (id: number) => void
}

const Ctx = createContext<StudioState | null>(null)
const STORAGE_KEY = 'graft-studio-workspace'

function readStored(): string {
  try {
    return localStorage.getItem(STORAGE_KEY) ?? ''
  } catch {
    return ''
  }
}

let toastId = 0

export function StudioProvider({ children }: { children: ReactNode }) {
  const [catalog, setCatalog] = useState<Catalog | null>(null)
  const [workspaces, setWorkspaces] = useState<WorkspaceSummary[]>([])
  const [wsId, setWsId] = useState(readStored())
  const [detail, setDetail] = useState<WorkspaceDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [connected, setConnected] = useState(true)
  const [toasts, setToasts] = useState<Toast[]>([])

  const dismiss = useCallback((id: number) => setToasts(t => t.filter(x => x.id !== id)), [])
  const notify = useCallback((text: string, kind: 'error' | 'info' = 'info') => {
    const id = ++toastId
    setToasts(t => [...t.slice(-3), { id, text, kind }])
    window.setTimeout(() => dismiss(id), kind === 'error' ? 9000 : 4000)
  }, [dismiss])
  const fail = useCallback((err: unknown) => notify(errorText(err), 'error'), [notify])

  const selectWorkspace = useCallback((id: string) => {
    setWsId(id)
    try {
      localStorage.setItem(STORAGE_KEY, id)
    } catch {
      /* storage can be unavailable; the choice just will not persist */
    }
  }, [])

  const refreshWorkspaces = useCallback(async () => {
    const list = await studio.workspaces()
    setWorkspaces(list)
    return list
  }, [])

  const refreshDetail = useCallback(async () => {
    if (!wsId) {
      setDetail(null)
      return
    }
    try {
      setDetail(await studio.workspace(wsId))
    } catch (err) {
      setDetail(null)
      fail(err)
    }
  }, [wsId, fail])

  // First load: catalogue and workspaces. A fresh install gets a demo workspace so there is something to try.
  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const [cat, list] = await Promise.all([studio.catalog(), studio.workspaces()])
        if (cancelled) return
        setCatalog(cat)
        let all = list
        if (all.length === 0) {
          const created = await studio.createWorkspace('Demo blog', '', 'Product analytics for SaaS teams', 'demo')
          all = await studio.workspaces()
          selectWorkspace(created.id)
        }
        setWorkspaces(all)
        setWsId(prev => (all.some(w => w.id === prev) ? prev : all[0].id))
        setConnected(true)
      } catch (err) {
        if (!cancelled) {
          setConnected(false)
          fail(err)
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => { cancelled = true }
  }, [fail, selectWorkspace])

  useEffect(() => { void refreshDetail() }, [refreshDetail])

  const value = useMemo<StudioState>(() => ({
    catalog, workspaces, wsId, detail, loading, connected, toasts, selectWorkspace, refreshWorkspaces, refreshDetail, notify, fail, dismiss,
  }), [catalog, workspaces, wsId, detail, loading, connected, toasts, selectWorkspace, refreshWorkspaces, refreshDetail, notify, fail, dismiss])

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export function useStudio(): StudioState {
  const ctx = useContext(Ctx)
  if (!ctx) throw new Error('useStudio must be used inside <StudioProvider>')
  return ctx
}
