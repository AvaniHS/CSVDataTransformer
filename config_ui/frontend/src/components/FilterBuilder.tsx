import { OPERATORS } from '../types/session'
import { FormField } from './FormField'
import styles from './filter.module.css'

export interface PredicateDraft {
  left: string
  operator: string
  right?: string | number | boolean
  right_type?: 'literal' | 'column'
}

interface FilterBuilderProps {
  columns: string[]
  value: PredicateDraft
  onChange: (value: PredicateDraft) => void
}

export function FilterBuilder({ columns, value, onChange }: FilterBuilderProps) {
  const nullOperator = value.operator === 'IS_NULL' || value.operator === 'IS_NOT_NULL'

  return (
    <div className={styles.row}>
      <FormField label="Column">
        <select
          value={value.left}
          onChange={(event) => onChange({ ...value, left: event.target.value })}
        >
          <option value="">Select column</option>
          {columns.map((column) => (
            <option key={column} value={column}>
              {column}
            </option>
          ))}
        </select>
      </FormField>

      <FormField label="Operator">
        <select
          value={value.operator}
          onChange={(event) => onChange({ ...value, operator: event.target.value })}
        >
          {OPERATORS.map((operator) => (
            <option key={operator} value={operator}>
              {operator}
            </option>
          ))}
        </select>
      </FormField>

      {!nullOperator ? (
        <FormField label="Value type">
          <select
            value={value.right_type ?? 'literal'}
            onChange={(event) =>
              onChange({ ...value, right_type: event.target.value as 'literal' | 'column' })
            }
          >
            <option value="literal">Literal</option>
            <option value="column">Column</option>
          </select>
        </FormField>
      ) : null}

      {!nullOperator ? (
        value.right_type === 'column' ? (
          <FormField label="Compare to">
            <select
              value={String(value.right ?? '')}
              onChange={(event) => onChange({ ...value, right: event.target.value })}
            >
              <option value="">Select column</option>
              {columns.map((column) => (
                <option key={column} value={column}>
                  {column}
                </option>
              ))}
            </select>
          </FormField>
        ) : (
          <FormField label="Value">
            <input
              value={String(value.right ?? '')}
              onChange={(event) => onChange({ ...value, right: event.target.value })}
            />
          </FormField>
        )
      ) : null}
    </div>
  )
}
