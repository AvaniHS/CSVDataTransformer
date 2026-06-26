import { useState } from 'react'
import { Button } from '../../components/Button'
import { Card } from '../../components/Card'
import { FormField } from '../../components/FormField'
import { useWizard } from '../../context/WizardContext'
import { TRANSFORM_TYPES, type BlueprintState } from '../../types/session'

export function DerivationsStep() {
  const { session, saveBlueprint } = useWizard()
  const [blueprintIndex, setBlueprintIndex] = useState(0)
  const [variableName, setVariableName] = useState('')
  const [transformType, setTransformType] = useState<(typeof TRANSFORM_TYPES)[number]>('EXPRESSION')
  const [expression, setExpression] = useState('')
  const [source, setSource] = useState('')
  const [pattern, setPattern] = useState('')
  const [replacement, setReplacement] = useState('')

  const blueprint = session?.blueprints[blueprintIndex]
  if (!session || !blueprint) {
    return <Card title="Derivations">Configure blueprints first.</Card>
  }

  const columnOptions = session.sources.flatMap((item) =>
    item.columns.map((column) => `${item.alias}.${column.name}`),
  )

  const addDerivation = async () => {
    if (!variableName) return
    let payload: Record<string, unknown>
    if (transformType === 'EXPRESSION') {
      payload = { variable_name: variableName, transform_type: 'EXPRESSION', expression }
    } else if (transformType === 'REGEXP_REPLACE') {
      payload = {
        variable_name: variableName,
        transform_type: 'REGEXP_REPLACE',
        source,
        pattern,
        replacement,
      }
    } else {
      payload = {
        variable_name: variableName,
        transform_type: 'CASE',
        branches: [
          {
            when: { left: columnOptions[0] ?? '', operator: 'IS_NOT_NULL', right_type: 'literal' },
            then: expression || 'value',
          },
        ],
        else: null,
      }
    }
    const next: BlueprintState = {
      ...blueprint,
      derivations: [...blueprint.derivations, payload],
    }
    await saveBlueprint(next)
    setVariableName('')
    setExpression('')
  }

  return (
    <>
      {session.blueprints.length > 1 ? (
        <Card title="Blueprint">
          <select value={blueprintIndex} onChange={(event) => setBlueprintIndex(Number(event.target.value))}>
            {session.blueprints.map((item, index) => (
              <option key={item.blueprint_id} value={index}>
                {item.blueprint_id}
              </option>
            ))}
          </select>
        </Card>
      ) : null}

      <Card title="Add derivation">
        <FormField label="Variable name">
          <input value={variableName} onChange={(event) => setVariableName(event.target.value)} />
        </FormField>
        <FormField label="Transform type">
          <select value={transformType} onChange={(event) => setTransformType(event.target.value as typeof transformType)}>
            {TRANSFORM_TYPES.map((type) => (
              <option key={type} value={type}>
                {type}
              </option>
            ))}
          </select>
        </FormField>

        {transformType === 'EXPRESSION' ? (
          <FormField label="Expression" hint="Use alias.column references">
            <textarea rows={3} value={expression} onChange={(event) => setExpression(event.target.value)} />
          </FormField>
        ) : null}

        {transformType === 'REGEXP_REPLACE' ? (
          <>
            <FormField label="Source column">
              <select value={source} onChange={(event) => setSource(event.target.value)}>
                <option value="">Select column</option>
                {columnOptions.map((column) => (
                  <option key={column} value={column}>
                    {column}
                  </option>
                ))}
              </select>
            </FormField>
            <FormField label="Pattern">
              <input value={pattern} onChange={(event) => setPattern(event.target.value)} />
            </FormField>
            <FormField label="Replacement">
              <input value={replacement} onChange={(event) => setReplacement(event.target.value)} />
            </FormField>
          </>
        ) : null}

        {transformType === 'CASE' ? (
          <FormField label="Then value (simple CASE)">
            <input value={expression} onChange={(event) => setExpression(event.target.value)} />
          </FormField>
        ) : null}

        <Button variant="primary" onClick={() => void addDerivation()}>
          Add derivation
        </Button>
      </Card>

      <Card title="Configured derivations">
        <ul>
          {blueprint.derivations.map((derivation, index) => (
            <li key={index}>
              <code>{JSON.stringify(derivation)}</code>
            </li>
          ))}
        </ul>
      </Card>
    </>
  )
}

export function useDerivationContext(session: ReturnType<typeof useWizard>['session'], blueprintIndex = 0) {
  const blueprint = session?.blueprints[blueprintIndex]
  const columns =
    session?.sources.flatMap((source) =>
      source.columns.map((column) => `${source.alias}.${column.name}`),
    ) ?? []
  const derivs =
    blueprint?.derivations
      .map((item) => (typeof item.variable_name === 'string' ? `deriv.${item.variable_name}` : null))
      .filter((item): item is string => Boolean(item)) ?? []
  return [...columns, ...derivs]
}
