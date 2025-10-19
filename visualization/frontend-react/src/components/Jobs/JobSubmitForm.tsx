/**
 * Job submission form component
 */

import React, { useEffect, useState } from 'react';
import {
  Box,
  Button,
  TextField,
  Typography,
  Card,
  CardContent,
  CardActions,
  Alert,
  CircularProgress
} from '@mui/material';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { jobService } from '../../services';
import type { SubmitJobRequest } from '../../types';

interface JobSubmitFormProps {
  onCancel?: () => void;
  onSuccess?: (jobId: string) => void;
  initialTaskDescription?: string;
  initialMaxTasks?: number;
  initialEnvVars?: Record<string, string | undefined> | null;
}

const formatEnvVars = (envVars?: Record<string, string | undefined> | null): string => {
  if (!envVars) {
    return '';
  }

  const entries = Object.entries(envVars).filter(([key]) => key);
  if (entries.length === 0) {
    return '';
  }

  return entries.map(([key, value]) => `${key}=${value ?? ''}`).join('\n');
};

const parseEnvVarsInput = (
  input: string
): { envVars: Record<string, string>; error?: string } => {
  const envVars: Record<string, string> = {};

  if (!input.trim()) {
    return { envVars };
  }

  const lines = input.split(/\r?\n/);
  for (let index = 0; index < lines.length; index++) {
    const rawLine = lines[index];
    if (!rawLine?.trim()) {
      continue;
    }

    const equalsIndex = rawLine.indexOf('=');
    if (equalsIndex === -1) {
      return {
        envVars: {},
        error: `Invalid format on line ${index + 1}. Use KEY=VALUE.`
      };
    }

    const key = rawLine.slice(0, equalsIndex).trim();
    const value = rawLine.slice(equalsIndex + 1);

    if (!key) {
      return {
        envVars: {},
        error: `Environment variable name missing on line ${index + 1}.`
      };
    }

    envVars[key] = value;
  }

  return { envVars };
};

export const JobSubmitForm: React.FC<JobSubmitFormProps> = ({
  onCancel,
  onSuccess,
  initialTaskDescription = '',
  initialMaxTasks = 50,
  initialEnvVars = null
}) => {
  const [taskDescription, setTaskDescription] = useState(initialTaskDescription);
  const [maxTasks, setMaxTasks] = useState<number>(initialMaxTasks);
  const [envVarsInput, setEnvVarsInput] = useState<string>(() => formatEnvVars(initialEnvVars));
  const [errors, setErrors] = useState<Record<string, string>>({});

  const navigate = useNavigate();
  const queryClient = useQueryClient();

  useEffect(() => {
    setEnvVarsInput(formatEnvVars(initialEnvVars));
    setErrors(prev => {
      if (!prev.envVars) {
        return prev;
      }
      const updatedErrors = { ...prev };
      delete updatedErrors.envVars;
      return updatedErrors;
    });
  }, [initialEnvVars]);

  const submitJobMutation = useMutation({
    mutationFn: (data: SubmitJobRequest) => jobService.submitJob(data),
    onSuccess: (response) => {
      // Invalidate jobs list to refresh
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
      
      if (onSuccess) {
        onSuccess(response.job_id);
      } else {
        // Navigate to job detail page
        navigate(`/jobs/${response.job_id}`);
      }
    },
    onError: (error) => {
      console.error('Failed to submit job:', error);
    }
  });

  const validateForm = (): { isValid: boolean; envVars?: Record<string, string> } => {
    const newErrors: Record<string, string> = {};

    if (!taskDescription.trim()) {
      newErrors.taskDescription = 'Task description is required';
    } else if (taskDescription.length > 10000) {
      newErrors.taskDescription = 'Task description must be less than 10,000 characters';
    }

    if (maxTasks < 1 || maxTasks > 1000) {
      newErrors.maxTasks = 'Max tasks must be between 1 and 1000';
    }

    const { envVars, error: envVarsError } = parseEnvVarsInput(envVarsInput);
    if (envVarsError) {
      newErrors.envVars = envVarsError;
    }

    setErrors(newErrors);
    const hasEnvVars = Object.keys(envVars).length > 0;
    return {
      isValid: Object.keys(newErrors).length === 0,
      envVars: envVarsError || !hasEnvVars ? undefined : envVars
    };
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    const { isValid, envVars } = validateForm();
    if (!isValid) {
      return;
    }

    const submission: SubmitJobRequest = {
      task_description: taskDescription.trim(),
      max_tasks: maxTasks
    };

    if (envVars) {
      submission.env_vars = envVars;
    }

    submitJobMutation.mutate(submission);
  };

  const handleReset = () => {
    setTaskDescription(initialTaskDescription);
    setMaxTasks(initialMaxTasks);
    setEnvVarsInput(formatEnvVars(initialEnvVars));
    setErrors({});
  };

  return (
    <Card>
      <form onSubmit={handleSubmit}>
        <CardContent>
          <Typography variant="h6" component="h2" gutterBottom>
            Submit New Job
          </Typography>
          
          {submitJobMutation.error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              Failed to submit job: {(submitJobMutation.error as Error).message}
            </Alert>
          )}

          <Box sx={{ mb: 3 }}>
            <TextField
              fullWidth
              multiline
              rows={4}
              label="Task Description"
              placeholder="Describe the task you want to execute..."
              value={taskDescription}
              onChange={(e) => {
                setTaskDescription(e.target.value);
                if (errors.taskDescription) {
                  setErrors(prev => ({ ...prev, taskDescription: '' }));
                }
              }}
              error={!!errors.taskDescription}
              helperText={errors.taskDescription || `${taskDescription.length}/10,000 characters`}
              disabled={submitJobMutation.isPending}
              required
            />
          </Box>

          <Box sx={{ mb: 2 }}>
            <TextField
              type="number"
              label="Max Tasks"
              value={maxTasks}
              onChange={(e) => {
                const value = parseInt(e.target.value, 10);
                setMaxTasks(isNaN(value) ? 50 : value);
                if (errors.maxTasks) {
                  setErrors(prev => ({ ...prev, maxTasks: '' }));
                }
              }}
              error={!!errors.maxTasks}
              helperText={errors.maxTasks || 'Maximum number of tasks to execute (1-1000)'}
              disabled={submitJobMutation.isPending}
              inputProps={{ min: 1, max: 1000 }}
              sx={{ width: 200 }}
              required
            />
          </Box>

          <Box sx={{ mb: 3 }}>
            <TextField
              fullWidth
              multiline
              minRows={3}
              maxRows={10}
              label="Environment Variables"
              placeholder={'OPTIONAL_FLAG=true\nAPI_KEY=example'}
              value={envVarsInput}
              onChange={(e) => {
                setEnvVarsInput(e.target.value);
                if (errors.envVars) {
                  setErrors(prev => {
                    if (!prev.envVars) {
                      return prev;
                    }
                    const updatedErrors = { ...prev };
                    delete updatedErrors.envVars;
                    return updatedErrors;
                  });
                }
              }}
              error={!!errors.envVars}
              helperText={
                errors.envVars || 'Optional. Enter KEY=VALUE pairs, one per line.'
              }
              disabled={submitJobMutation.isPending}
            />
          </Box>
        </CardContent>

        <CardActions sx={{ justifyContent: 'flex-end', gap: 1 }}>
          <Button
            type="button"
            variant="outlined"
            onClick={() => {
              handleReset();
              onCancel?.();
            }}
            disabled={submitJobMutation.isPending}
          >
            {onCancel ? 'Cancel' : 'Reset'}
          </Button>
          
          <Button
            type="submit"
            variant="contained"
            disabled={submitJobMutation.isPending || !taskDescription.trim()}
            startIcon={submitJobMutation.isPending ? <CircularProgress size={16} /> : null}
          >
            {submitJobMutation.isPending ? 'Submitting...' : 'Submit Job'}
          </Button>
        </CardActions>
      </form>
    </Card>
  );
};