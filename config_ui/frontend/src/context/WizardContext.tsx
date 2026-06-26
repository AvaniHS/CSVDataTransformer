import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { ApiClientError } from '../api/client'
import * as sessionApi from '../api/session'
import type { BlueprintState, SessionMetadata, SessionState } from '../types/session'
import { WIZARD_STEPS } from '../types/session'

interface WizardContextValue {
  session: SessionState | null
  currentStep: number
  completedThrough: number
  loading: boolean
  error: string | null
  notice: string | null
  setStep: (step: number) => void
  nextStep: () => void
  prevStep: () => void
  refreshSession: () => Promise<void>
  updateMetadata: (metadata: SessionMetadata) => Promise<void>
  importConfig: (config: Record<string, unknown>) => Promise<void>
  saveBlueprint: (blueprint: BlueprintState) => Promise<void>
  setNotice: (message: string | null) => void
}

const WizardContext = createContext<WizardContextValue | null>(null)

const defaultMetadata: SessionMetadata = {
  migration_id: 'mig_config_ui',
  client_id: 'client_default',
  version: '1.0.0',
  connection_ref: 'local_file_system',
  base_path: null,
  target_path: null,
  source_count: 1,
  target_count: 1,
}

export function WizardProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<SessionState | null>(null)
  const [currentStep, setCurrentStep] = useState(0)
  const [completedThrough, setCompletedThrough] = useState(-1)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const handleError = useCallback((err: unknown) => {
    if (err instanceof ApiClientError) {
      setError(err.body.message)
    } else if (err instanceof Error) {
      setError(err.message)
    } else {
      setError('An unexpected error occurred')
    }
  }, [])

  const bootstrap = useCallback(async () => {
    if (session) return
    setLoading(true)
    setError(null)
    try {
      const created = await sessionApi.createSession(defaultMetadata)
      setSession(created)
    } catch (err) {
      handleError(err)
    } finally {
      setLoading(false)
    }
  }, [handleError, session])

  useEffect(() => {
    void bootstrap()
  }, [bootstrap])

  const refreshSession = useCallback(async () => {
    if (!session) return
    setLoading(true)
    setError(null)
    try {
      const latest = await sessionApi.getSession(session.session_id)
      setSession(latest)
    } catch (err) {
      handleError(err)
    } finally {
      setLoading(false)
    }
  }, [handleError, session])

  const updateMetadata = useCallback(
    async (metadata: SessionMetadata) => {
      if (!session) return
      setLoading(true)
      setError(null)
      try {
        const updated = await sessionApi.updateMetadata(session.session_id, metadata)
        setSession(updated)
        setNotice('Setup saved')
      } catch (err) {
        handleError(err)
      } finally {
        setLoading(false)
      }
    },
    [handleError, session],
  )

  const importConfig = useCallback(
    async (config: Record<string, unknown>) => {
      setLoading(true)
      setError(null)
      try {
        const imported = await sessionApi.importConfig(config)
        setSession(imported)
        setCompletedThrough(WIZARD_STEPS.length - 1)
        setCurrentStep(WIZARD_STEPS.length - 1)
        setNotice('Config imported — review and download')
      } catch (err) {
        handleError(err)
      } finally {
        setLoading(false)
      }
    },
    [handleError],
  )

  const saveBlueprint = useCallback(
    async (blueprint: BlueprintState) => {
      if (!session) return
      setLoading(true)
      setError(null)
      try {
        const updated = await sessionApi.updateBlueprint(session.session_id, blueprint.blueprint_id, blueprint)
        setSession(updated)
      } catch (err) {
        handleError(err)
      } finally {
        setLoading(false)
      }
    },
    [handleError, session],
  )

  const setStep = useCallback((step: number) => {
    setCurrentStep(Math.max(0, Math.min(WIZARD_STEPS.length - 1, step)))
    setError(null)
  }, [])

  const nextStep = useCallback(() => {
    setCompletedThrough((prev) => Math.max(prev, currentStep))
    setCurrentStep((prev) => Math.min(WIZARD_STEPS.length - 1, prev + 1))
    setError(null)
    setNotice(null)
  }, [currentStep])

  const prevStep = useCallback(() => {
    setCurrentStep((prev) => Math.max(0, prev - 1))
    setError(null)
  }, [])

  const value: WizardContextValue = {
    session,
    currentStep,
    completedThrough,
    loading,
    error,
    notice,
    setStep,
    nextStep,
    prevStep,
    refreshSession,
    updateMetadata,
    importConfig,
    saveBlueprint,
    setNotice,
  }

  return <WizardContext.Provider value={value}>{children}</WizardContext.Provider>
}

export function useWizard() {
  const context = useContext(WizardContext)
  if (!context) {
    throw new Error('useWizard must be used within WizardProvider')
  }
  return context
}
