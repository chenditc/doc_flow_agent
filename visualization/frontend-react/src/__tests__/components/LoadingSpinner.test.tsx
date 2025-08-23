import { describe, it, expect } from 'vitest'
import { render } from '../../test/test-utils'
import { LoadingSpinner } from '../../components/common/LoadingStates'

describe('LoadingSpinner', () => {
  it('renders without crashing', () => {
    const { container } = render(<LoadingSpinner />)
    const svg = container.querySelector('svg')
    
    expect(svg).toBeTruthy()
    expect(svg).toHaveClass('animate-spin')
  })

  it('renders with custom size', () => {
    const { container } = render(<LoadingSpinner size="lg" />)
    const svg = container.querySelector('svg')
    
    expect(svg).toHaveClass('h-8', 'w-8')
  })

  it('applies custom className', () => {
    const customClass = 'custom-spinner'
    const { container } = render(<LoadingSpinner className={customClass} />)
    const svg = container.querySelector('svg')
    
    expect(svg).toHaveClass(customClass)
  })
})
