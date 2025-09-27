/**
 * Jobs list page with filtering and auto-refresh
 */

import React, { useState } from 'react';
import {
  Box,
  Button,
  Card,
  CardContent,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  IconButton,
  Tooltip,
  Alert,
  CircularProgress,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  Link
} from '@mui/material';
import {
  Plus as AddIcon,
  RefreshCw as RefreshIcon,
  X as CancelIcon,
  Eye as ViewIcon
} from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate, Link as RouterLink } from 'react-router-dom';
import { jobService } from '../../services';
import { JobStatusChip } from './JobStatusChip';
import { JobSubmitForm } from './JobSubmitForm';
import type { JobStatus } from '../../types';

export const JobsListPage: React.FC = () => {
  const [statusFilter, setStatusFilter] = useState<JobStatus | 'ALL'>('ALL');
  const [showSubmitForm, setShowSubmitForm] = useState(false);
  
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  // Fetch jobs with auto-refresh
  const {
    data: jobs = [],
    isLoading,
    error,
    refetch
  } = useQuery<Awaited<ReturnType<typeof jobService.listJobs>>, Error>({
    queryKey: ['jobs', statusFilter === 'ALL' ? undefined : statusFilter],
    queryFn: () => jobService.listJobs(statusFilter === 'ALL' ? {} : { status: statusFilter }),
    // Use a fixed short interval; we'll dynamically pause via enabled flag logic below if desired
    // but keep this simple: no direct reference to 'jobs' during initialization to avoid TDZ errors.
    refetchInterval: 3000
  });

  // Optional dynamic throttling: if no active jobs, we can manually stop polling.
  // Simpler approach: if there are no active jobs, schedule a one-off refetch far later instead of constant polling.
  React.useEffect(() => {
    if (!jobs || (jobs as any[]).length === 0) return; // nothing to decide
    const hasActiveJobs = (jobs as any[]).some((job: any) => ['QUEUED', 'STARTING', 'RUNNING'].includes(job.status));
    if (!hasActiveJobs) {
      // Perform one final refetch in 10s to catch late transitions, then rely on manual refresh or user actions.
      const t = setTimeout(() => {
        refetch();
      }, 10000);
      return () => clearTimeout(t);
    }
  }, [jobs, refetch]);

  // Cancel job mutation
  const cancelJobMutation = useMutation({
    mutationFn: (jobId: string) => jobService.cancelJob(jobId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
    }
  });

  const handleCancelJob = (jobId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (window.confirm('Are you sure you want to cancel this job?')) {
      cancelJobMutation.mutate(jobId);
    }
  };

  const handleRowClick = (jobId: string) => {
    navigate(`/jobs/${jobId}`);
  };

  const formatDuration = (startTime?: string | null, endTime?: string | null) => {
    if (!startTime) return '-';
    
    const start = new Date(startTime);
    const end = endTime ? new Date(endTime) : new Date();
    const durationMs = end.getTime() - start.getTime();
    
    if (durationMs < 1000) return '< 1s';
    if (durationMs < 60000) return `${Math.floor(durationMs / 1000)}s`;
    if (durationMs < 3600000) return `${Math.floor(durationMs / 60000)}m`;
    return `${Math.floor(durationMs / 3600000)}h ${Math.floor((durationMs % 3600000) / 60000)}m`;
  };

  const truncateText = (text: string, maxLength: number = 80) => {
    return text.length > maxLength ? `${text.substring(0, maxLength)}...` : text;
  };

  if (error) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">
          Failed to load jobs: {(error as Error).message}
          <Button onClick={() => refetch()} sx={{ ml: 2 }}>
            Retry
          </Button>
        </Alert>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" component="h1">
          Jobs
        </Typography>
        
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>Status</InputLabel>
            <Select
              value={statusFilter}
              label="Status"
              onChange={(e) => setStatusFilter(e.target.value as JobStatus | 'ALL')}
            >
              <MenuItem value="ALL">All</MenuItem>
              <MenuItem value="QUEUED">Queued</MenuItem>
              <MenuItem value="STARTING">Starting</MenuItem>
              <MenuItem value="RUNNING">Running</MenuItem>
              <MenuItem value="COMPLETED">Completed</MenuItem>
              <MenuItem value="FAILED">Failed</MenuItem>
              <MenuItem value="CANCELLED">Cancelled</MenuItem>
            </Select>
          </FormControl>
          
          <Tooltip title="Refresh">
            <IconButton onClick={() => refetch()} disabled={isLoading}>
              <RefreshIcon />
            </IconButton>
          </Tooltip>
          
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setShowSubmitForm(true)}
          >
            New Job
          </Button>
        </Box>
      </Box>

      {isLoading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
          <CircularProgress />
        </Box>
      )}

      {!isLoading && (
        <Card>
          <CardContent sx={{ p: 0 }}>
            <TableContainer component={Paper} elevation={0}>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Job ID</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Task Description</TableCell>
                    <TableCell>Created</TableCell>
                    <TableCell>Duration</TableCell>
                    <TableCell>Traces</TableCell>
                    <TableCell align="center">Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {jobs.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={7} align="center" sx={{ py: 4 }}>
                        <Typography color="text.secondary">
                          {statusFilter === 'ALL' ? 'No jobs found' : `No ${statusFilter.toLowerCase()} jobs found`}
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ) : (
                    (jobs as any[]).map((job: any) => (
                      <TableRow
                        key={job.job_id}
                        hover
                        sx={{ cursor: 'pointer' }}
                        onClick={() => handleRowClick(job.job_id)}
                      >
                        <TableCell>
                          <Link
                            component={RouterLink}
                            to={`/jobs/${job.job_id}`}
                            underline="hover"
                            onClick={(e) => e.stopPropagation()}
                          >
                            {job.job_id}
                          </Link>
                        </TableCell>
                        <TableCell>
                          <JobStatusChip status={job.status} />
                        </TableCell>
                        <TableCell>
                          <Tooltip title={job.task_description}>
                            <Typography variant="body2">
                              {truncateText(job.task_description)}
                            </Typography>
                          </Tooltip>
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2">
                            {new Date(job.created_at).toLocaleString()}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2">
                            {formatDuration(job.started_at, job.finished_at)}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Chip 
                            label={job.trace_files.length} 
                            size="small" 
                            variant="outlined"
                          />
                        </TableCell>
                        <TableCell align="center">
                          <Tooltip title="View Details">
                            <IconButton
                              size="small"
                              onClick={(e) => {
                                e.stopPropagation();
                                navigate(`/jobs/${job.job_id}`);
                              }}
                            >
                              <ViewIcon />
                            </IconButton>
                          </Tooltip>
                          
                          {['QUEUED', 'STARTING', 'RUNNING'].includes(job.status) && (
                            <Tooltip title="Cancel Job">
                              <IconButton
                                size="small"
                                color="error"
                                onClick={(e) => handleCancelJob(job.job_id, e)}
                                disabled={cancelJobMutation.isPending}
                              >
                                <CancelIcon />
                              </IconButton>
                            </Tooltip>
                          )}
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        </Card>
      )}

      {/* Submit job dialog */}
      <Dialog
        open={showSubmitForm}
        onClose={() => setShowSubmitForm(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          Submit New Job
        </DialogTitle>
        <DialogContent>
          <JobSubmitForm
            onCancel={() => setShowSubmitForm(false)}
            onSuccess={() => setShowSubmitForm(false)}
          />
        </DialogContent>
      </Dialog>
    </Box>
  );
};