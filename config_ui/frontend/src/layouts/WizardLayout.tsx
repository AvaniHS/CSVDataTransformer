import styles from './wizard.module.css'
import { Button } from '../components/Button'
import { ColumnContextPanel } from '../components/ColumnContextPanel'
import { SettingsDrawer } from '../components/SettingsDrawer'
import { Stepper } from '../components/Stepper'
import { ValidationBanner } from '../components/ValidationBanner'
import { useWizard } from '../context/WizardContext'
import { WIZARD_STEPS } from '../types/session'

interface WizardLayoutProps {
  children: React.ReactNode
  contextColumns?: string[]
  showContext?: boolean
}

export function WizardLayout({ children, contextColumns = [], showContext = false }: WizardLayoutProps) {
  const { currentStep, completedThrough, error, notice, prevStep, nextStep, loading } = useWizard()
  const step = WIZARD_STEPS[currentStep]

  return (
    <div className={styles.shell}>
      <header className={styles.header}>
        <div>
          <h1>Config Builder</h1>
          <p className={styles.subtitle}>
            Step {currentStep + 1} of {WIZARD_STEPS.length} — {step.label}
          </p>
        </div>
        <SettingsDrawer />
      </header>

      {error ? <ValidationBanner tone="error" message={error} /> : null}
      {notice ? <ValidationBanner tone="success" message={notice} /> : null}

      <div className={styles.body}>
        <aside className={styles.sidebar}>
          <Stepper currentStep={currentStep} completedThrough={completedThrough} />
          {showContext ? <ColumnContextPanel title="Available columns" items={contextColumns} /> : null}
        </aside>

        <main className={styles.main}>{children}</main>
      </div>

      <footer className={styles.footer}>
        <Button onClick={prevStep} disabled={currentStep === 0 || loading}>
          ← Back
        </Button>
        <Button variant="primary" onClick={nextStep} disabled={currentStep === WIZARD_STEPS.length - 1 || loading}>
          Continue →
        </Button>
      </footer>
    </div>
  )
}
