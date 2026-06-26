import { apiGet, apiPost, apiPut, apiUpload } from './client'
import type { BlueprintState, SessionMetadata, SessionState, SourceFile, TargetFile } from '../types/session'

const BASE = '/api/v1'

export async function createSession(metadata?: Partial<SessionMetadata>): Promise<SessionState> {
  return apiPost(`${BASE}/session`, { metadata })
}

export async function getSession(sessionId: string): Promise<SessionState> {
  return apiGet(`${BASE}/session/${sessionId}`)
}

export async function updateMetadata(sessionId: string, metadata: SessionMetadata): Promise<SessionState> {
  return apiPut(`${BASE}/session/${sessionId}/metadata`, { metadata })
}

export async function uploadSource(sessionId: string, file: File): Promise<SourceFile> {
  const result = await apiUpload<{ source: SourceFile }>(`${BASE}/session/${sessionId}/sources`, file)
  return result.source
}

export async function uploadTarget(
  sessionId: string,
  file: File,
): Promise<{ target: TargetFile; warning?: string }> {
  const result = await apiUpload<{ target: TargetFile; warning?: string }>(
    `${BASE}/session/${sessionId}/targets`,
    file,
  )
  return result
}

export async function updateSourceAlias(sessionId: string, sourceId: string, alias: string): Promise<SourceFile> {
  const response = await fetch(`${BASE}/session/${sessionId}/sources/${sourceId}?alias=${encodeURIComponent(alias)}`, {
    method: 'PUT',
  })
  if (!response.ok) {
    throw new Error('Failed to update source alias')
  }
  const result = (await response.json()) as { source: SourceFile }
  return result.source
}

export async function updateBlueprint(
  sessionId: string,
  blueprintId: string,
  blueprint: BlueprintState,
): Promise<SessionState> {
  return apiPut(`${BASE}/session/${sessionId}/blueprints/${blueprintId}`, { blueprint })
}

export async function validateConfig(config: Record<string, unknown>): Promise<{ valid: boolean; message: string }> {
  return apiPost(`${BASE}/config/validate`, { config })
}

export async function generateConfig(sessionId: string): Promise<Record<string, unknown>> {
  const result = await apiPost<{ config: Record<string, unknown> }>(`${BASE}/config/generate`, { session_id: sessionId })
  return result.config
}

export async function importConfig(config: Record<string, unknown>): Promise<SessionState> {
  const result = await apiPost<{ session: SessionState }>(`${BASE}/config/import`, { config })
  return result.session
}
