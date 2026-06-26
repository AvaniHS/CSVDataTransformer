export type CastType = 'str' | 'int64' | 'float64' | 'datetime64[ns]'
export type JoinType = 'LEFT' | 'INNER' | 'RIGHT' | 'OUTER'
export type SourceType = 'DIRECT' | 'DERIVED' | 'EXPRESSION'
export type TransformType = 'EXPRESSION' | 'REGEXP_REPLACE' | 'CASE'

export interface ColumnSchema {
  name: string
  inferred_cast: CastType
  sample_values: string[]
}

export interface SourceFile {
  source_id: string
  file_name: string
  alias: string
  columns: ColumnSchema[]
  sample_rows: Record<string, string>[]
  row_count: number
}

export interface TargetFile {
  target_id: string
  file_name: string
  headers: string[]
}

export interface JoinState {
  source_id: string
  join_type: JoinType
  conditions: Record<string, unknown>[]
  pre_filters: Record<string, unknown>[]
}

export interface MappingState {
  target_column: string
  source_type: SourceType
  source_value: string
  cast_to: CastType
  is_nullable: boolean
  default_value?: unknown
}

export interface BlueprintState {
  blueprint_id: string
  sequence_order: number
  target_id: string
  root_source_id: string
  joins: JoinState[]
  pre_filters: Record<string, unknown>[]
  pending_join_pre_filters: Record<string, Record<string, unknown>[]>
  derivations: Record<string, unknown>[]
  post_filters: Record<string, unknown>[]
  mappings: MappingState[]
  comment?: string | null
}

export interface SessionMetadata {
  migration_id: string
  client_id: string
  version: string
  connection_ref: string
  base_path?: string | null
  target_path?: string | null
  source_count: number
  target_count: number
}

export interface SessionState {
  session_id: string
  metadata: SessionMetadata
  sources: SourceFile[]
  targets: TargetFile[]
  blueprints: BlueprintState[]
}

export interface ApiError {
  error: string
  message: string
  gate?: string
  blueprint_id?: string
  details?: { path?: string; message: string }[]
}

export const OPERATORS = [
  '==',
  '!=',
  '<',
  '<=',
  '>',
  '>=',
  'IN',
  'NOT_IN',
  'LIKE',
  'NOT_LIKE',
  'IS_NULL',
  'IS_NOT_NULL',
] as const

export const JOIN_TYPES: JoinType[] = ['LEFT', 'INNER', 'RIGHT', 'OUTER']
export const CAST_TYPES: CastType[] = ['str', 'int64', 'float64', 'datetime64[ns]']
export const SOURCE_TYPES: SourceType[] = ['DIRECT', 'DERIVED', 'EXPRESSION']
export const TRANSFORM_TYPES: TransformType[] = ['EXPRESSION', 'REGEXP_REPLACE', 'CASE']

export const WIZARD_STEPS = [
  { id: 'setup', label: 'Setup' },
  { id: 'upload', label: 'Upload' },
  { id: 'filters', label: 'Pre-filters' },
  { id: 'joins', label: 'Joins' },
  { id: 'derive', label: 'Derivations' },
  { id: 'post', label: 'Post-filters' },
  { id: 'map', label: 'Mappings' },
  { id: 'review', label: 'Review' },
] as const
