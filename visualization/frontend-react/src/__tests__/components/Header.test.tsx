import { describe, it, expect } from 'vitest'
import { screen } from '@testing-library/react'
import { render } from '../../test/test-utils'
import { Header } from '../../components/common/Header'

describe('Header', () => {
  it('renders with default title and subtitle', () => {
    render(<Header />)
    
    expect(screen.getByText('Doc Flow Trace Viewer')).toBeInTheDocument()
    expect(screen.getByText('Real-time visualization of task execution traces')).toBeInTheDocument()
  })

  it('renders with custom title and subtitle', () => {
    const customTitle = 'Custom Title'
    const customSubtitle = 'Custom subtitle'
    
    render(<Header title={customTitle} subtitle={customSubtitle} />)
    
    expect(screen.getByText(customTitle)).toBeInTheDocument()
    expect(screen.getByText(customSubtitle)).toBeInTheDocument()
  })

  it('renders without subtitle when not provided', () => {
    render(<Header title="Test Title" subtitle="" />)
    
    expect(screen.getByText('Test Title')).toBeInTheDocument()
    expect(screen.queryByText('Real-time visualization of task execution traces')).not.toBeInTheDocument()
  })

  it('has proper semantic structure', () => {
    render(<Header />)
    
    const header = screen.getByRole('banner')
    const heading = screen.getByRole('heading', { level: 1 })
    
    expect(header).toBeInTheDocument()
    expect(heading).toBeInTheDocument()
  })
})
