import styles from './ui.module.css'
import { WIZARD_STEPS } from '../types/session'

interface StepperProps {
  currentStep: number
  completedThrough: number
}

export function Stepper({ currentStep, completedThrough }: StepperProps) {
  return (
    <nav className={styles.stepper} aria-label="Wizard steps">
      <ol>
        {WIZARD_STEPS.map((step, index) => {
          const status =
            index < completedThrough ? 'done' : index === currentStep ? 'active' : 'pending'
          return (
            <li key={step.id} className={`${styles.step} ${styles[status]}`}>
              <span className={styles.stepIndex}>{status === 'done' ? '✓' : index + 1}</span>
              <span>{step.label}</span>
            </li>
          )
        })}
      </ol>
    </nav>
  )
}
