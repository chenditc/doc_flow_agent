/**
 * Job submission form component
 */

import React, { useState } from 'react';
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
}

export const JobSubmitForm: React.FC<JobSubmitFormProps> = ({ 
  onCancel, 
  onSuccess,
  initialTaskDescription = '',
  initialMaxTasks = 50
}) => {
  const [taskDescription, setTaskDescription] = useState(initialTaskDescription);
  const [maxTasks, setMaxTasks] = useState<number>(initialMaxTasks);
  const [errors, setErrors] = useState<Record<string, string>>({});
  
  const navigate = useNavigate();
  const queryClient = useQueryClient();

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

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!taskDescription.trim()) {
      newErrors.taskDescription = 'Task description is required';
    } else if (taskDescription.length > 10000) {
      newErrors.taskDescription = 'Task description must be less than 10,000 characters';
    }

    if (maxTasks < 1 || maxTasks > 1000) {
      newErrors.maxTasks = 'Max tasks must be between 1 and 1000';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }

    submitJobMutation.mutate({
      task_description: taskDescription.trim(),
      max_tasks: maxTasks
    });
  };

  const handleReset = () => {
    setTaskDescription(initialTaskDescription);
    setMaxTasks(initialMaxTasks);
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