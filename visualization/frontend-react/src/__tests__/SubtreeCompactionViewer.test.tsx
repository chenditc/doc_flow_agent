/// <reference types="vitest" />
import { describe, it, expect } from 'vitest';
import { render, screen } from '../test/test-utils';
import { SubtreeCompactionViewer } from '../components/enhanced/SubtreeCompactionViewer';
import type { SubtreeCompactionPhase } from '../types/trace';

const mockCompactionPhase: SubtreeCompactionPhase = {
  start_time: '2025-09-26T03:40:48.058336Z',
  end_time: '2025-09-26T03:41:39.979644Z',
  status: 'completed',
  root_task_id: 'af74b9f93640057a',
  subtree_task_ids: ['af74b9f93640057a'],
  aggregated_outputs: {
    '$.message_collected_for_use_az_cli_to_create_a_ubuntu_22_04_vm': {
      question: 'Current task needs your help...',
      user_reply: 'use sensible defaults'
    }
  },
  llm_calls: [
    {
      tool_call_id: '319c49bd-48fa-412f-8b8e-990642ffb315',
      prompt: 'You are evaluating whether a completed task subtree...',
      response: '',
      start_time: '2025-09-26T03:41:22.295445Z',
      end_time: '2025-09-26T03:41:22.295460Z',
      model: 'gpt-5',
      token_usage: null,
      tool_calls: [
        {
          id: 'call_KJ4DuEeFO32kHxbZLQiRp7QD',
          name: 'evaluate_and_summarize_subtree',
          arguments: {
            requirements_met: false,
            useful_output_path: ['$.message_collected_for_use_az_cli_to_create_a_ubuntu_22_04_vm']
          }
        }
      ]
    }
  ]
};

describe('SubtreeCompactionViewer', () => {
  it('renders basic phase information', () => {
    render(<SubtreeCompactionViewer phaseData={mockCompactionPhase} />);
    
    // Check root task ID is displayed
    expect(screen.getByText('Root Task ID:')).toBeInTheDocument();
    expect(screen.getByText('af74b9f93640057a')).toBeInTheDocument();
    
    // Check subtree task count
    expect(screen.getByText('Subtree Tasks:')).toBeInTheDocument();
    expect(screen.getByText('1')).toBeInTheDocument();
  });

  it('renders aggregated outputs with correct count', () => {
    render(<SubtreeCompactionViewer phaseData={mockCompactionPhase} />);
    
    // Check aggregated outputs section
    expect(screen.getByText('Aggregated Outputs (1)')).toBeInTheDocument();
    expect(screen.getByText('$.message_collected_for_use_az_cli_to_create_a_ubuntu_22_04_vm')).toBeInTheDocument();
  });

  it('renders useful output paths as badges', () => {
    render(<SubtreeCompactionViewer phaseData={mockCompactionPhase} />);
    
    // Check useful output paths section
    expect(screen.getByText('Useful Output Paths')).toBeInTheDocument();
    expect(screen.getByText('$.message_collected_for_use_az_cli_to_create_a_ubuntu_22_04_vm')).toBeInTheDocument();
  });

  it('renders LLM calls with correct count and model', () => {
    render(<SubtreeCompactionViewer phaseData={mockCompactionPhase} />);
    
    // Check LLM calls section
    expect(screen.getByText('LLM Calls (1)')).toBeInTheDocument();
    
    // Check model name is displayed (part of ContextualLLMCall component)
    expect(screen.getByText('Model:')).toBeInTheDocument();
    expect(screen.getByText('gpt-5')).toBeInTheDocument();
  });

  it('renders tuning button', () => {
    render(<SubtreeCompactionViewer phaseData={mockCompactionPhase} />);
    
    // Check that the tuning button is present (from ContextualLLMCall)
    // We need to expand the LLM call first
    const showButton = screen.getByText('Show Prompt & Response');
    showButton.click();
    
    expect(screen.getByText('🔧 Tune in LLM Tuning Page')).toBeInTheDocument();
  });

  it('handles empty phase data gracefully', () => {
    const emptyPhase: SubtreeCompactionPhase = {
      start_time: '2025-09-26T03:40:48.058336Z',
      end_time: '2025-09-26T03:41:39.979644Z',
      status: 'completed',
      root_task_id: 'empty-task',
      subtree_task_ids: [],
      aggregated_outputs: {},
      llm_calls: []
    };

    render(<SubtreeCompactionViewer phaseData={emptyPhase} />);
    
    // Should show 0 counts
    expect(screen.getByText('Subtree Tasks:')).toBeInTheDocument();
    expect(screen.getByText('0')).toBeInTheDocument();
    expect(screen.getByText('Aggregated Outputs (0)')).toBeInTheDocument();
    expect(screen.getByText('LLM Calls (0)')).toBeInTheDocument();
    expect(screen.getByText('No LLM calls recorded')).toBeInTheDocument();
  });
});