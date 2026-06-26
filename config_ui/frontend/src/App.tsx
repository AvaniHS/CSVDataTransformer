import { WizardProvider, useWizard } from './context/WizardContext'
import { WizardLayout } from './layouts/WizardLayout'
import { SetupStep } from './features/setup/SetupStep'
import { UploadStep } from './features/upload/UploadStep'
import { PreFiltersStep, usePreFilterContext } from './features/pre-filters/PreFiltersStep'
import { JoinsStep, useJoinContext } from './features/joins/JoinsStep'
import { DerivationsStep, useDerivationContext } from './features/derivations/DerivationsStep'
import { PostFiltersStep } from './features/post-filters/PostFiltersStep'
import { MappingsStep, useMappingContext } from './features/mappings/MappingsStep'
import { ReviewStep } from './features/review/ReviewStep'

function WizardBody() {
  const { currentStep, session } = useWizard()
  const filterContext = usePreFilterContext(session)
  const joinContext = useJoinContext(session)
  const derivContext = useDerivationContext(session)
  const mapContext = useMappingContext(session)

  const showContext = currentStep >= 2 && currentStep <= 6
  const contextColumns =
    currentStep === 2
      ? filterContext
      : currentStep === 3
        ? joinContext
        : currentStep === 4
          ? derivContext
          : currentStep === 6
            ? mapContext
            : []

  const stepViews = [
    <SetupStep key="setup" />,
    <UploadStep key="upload" />,
    <PreFiltersStep key="filters" />,
    <JoinsStep key="joins" />,
    <DerivationsStep key="derive" />,
    <PostFiltersStep key="post" />,
    <MappingsStep key="map" />,
    <ReviewStep key="review" />,
  ]

  return (
    <WizardLayout showContext={showContext} contextColumns={contextColumns}>
      {stepViews[currentStep]}
    </WizardLayout>
  )
}

export default function App() {
  return (
    <WizardProvider>
      <WizardBody />
    </WizardProvider>
  )
}
