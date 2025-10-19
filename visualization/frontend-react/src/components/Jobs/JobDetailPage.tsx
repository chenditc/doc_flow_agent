/**
 * Job detail page with tabs for summary, logs, traces, and context
 */

import React, { useState } from 'react';
import {
  Box,
  Card,
  Typography,
  Tabs,
  Tab,
  Button,
  Alert,
  CircularProgress,
  Paper,
  List,
  ListItem,
  ListItemText,
  ListItemButton,
  TextField,
  MenuItem,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent
} from '@mui/material';
import {
  ArrowLeft as BackIcon,
  RefreshCw as RefreshIcon,
  X as CancelIcon,
  ExternalLink as ExternalLinkIcon,
  Play as RerunIcon,
  Download as DownloadIcon
} from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useParams, useNavigate } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import { JsonViewer } from '../common/JsonViewer';
import { jobService } from '../../services';
import { JobStatusChip } from './JobStatusChip';
import { JobSubmitForm } from './JobSubmitForm';


interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

const TabPanel: React.FC<TabPanelProps> = ({ children, value, index, ...other }) => {
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`job-tabpanel-${index}`}
      aria-labelledby={`job-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
};

export const JobDetailPage: React.FC = () => {
  const { jobId } = useParams<{ jobId: string }>();
  const [activeTab, setActiveTab] = useState(0);
  const [logTailLines, setLogTailLines] = useState(500);
  const [showRerunForm, setShowRerunForm] = useState(false);
  const [showSuccessAlert, setShowSuccessAlert] = useState(false);
  
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  // Helper function to check if content is JSON parsable
  const isJsonParsable = (content: any): boolean => {
    if (typeof content === 'object' && content !== null) {
      return true; // Already a parsed object
    }
    if (typeof content === 'string') {
      try {
        JSON.parse(content);
        return true;
      } catch {
        return false;
      }
    }
    return false;
  };

  // Fetch job details
  const {
    data: job,
    isLoading,
    error,
    refetch
  } = useQuery({
    queryKey: ['job', jobId],
    queryFn: () => jobService.getJob(jobId!),
    enabled: !!jobId,
    refetchInterval: 3000 // Simple 3 second polling for now
  });

  // Fetch job logs
  const {
    data: logsData,
    isLoading: logsLoading,
    refetch: refetchLogs
  } = useQuery({
    queryKey: ['job-logs', jobId, logTailLines],
    queryFn: () => jobService.getJobLogs(jobId!, logTailLines),
    enabled: !!jobId && activeTab === 1,
    refetchInterval: 2000 // Simple 2 second polling for logs
  });

  // Fetch job context
  const {
    data: contextData,
    isLoading: contextLoading
  } = useQuery({
    queryKey: ['job-context', jobId],
    queryFn: () => jobService.getJobContext(jobId!),
    enabled: !!jobId && (activeTab === 3 || activeTab === 4)
  });

  // Cancel job mutation
  const cancelJobMutation = useMutation({
    mutationFn: () => jobService.cancelJob(jobId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['job', jobId] });
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
    }
  });

  const handleCancelJob = () => {
    if (window.confirm('Are you sure you want to cancel this job?')) {
      cancelJobMutation.mutate();
    }
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

  const handleTraceClick = (traceFile: string) => {
    // Normalize trace id: backend provides filenames (possibly with .json); viewer expects raw session id
    const normalized = traceFile.endsWith('.json') ? traceFile.replace(/\.json$/,'') : traceFile;
    navigate(`/traces?trace=${encodeURIComponent(normalized)}`);
  };

  const handleDownloadLogs = () => {
    const logs = (logsData as any)?.logs || 'No logs available';
    const blob = new Blob([logs], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `job_${jobId}_logs.txt`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">
          Failed to load job: {(error as Error).message}
          <Button onClick={() => refetch()} sx={{ ml: 2 }}>
            Retry
          </Button>
        </Alert>
      </Box>
    );
  }

  if (!job) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="warning">Job not found</Alert>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      {/* Success Alert */}
      {showSuccessAlert && (
        <Alert 
          severity="success" 
          onClose={() => setShowSuccessAlert(false)}
          sx={{ mb: 3 }}
        >
          New job submitted successfully! You are now viewing the new job.
        </Alert>
      )}

      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <IconButton onClick={() => navigate('/jobs')} sx={{ mr: 2 }}>
          <BackIcon />
        </IconButton>
        
        <Box sx={{ flexGrow: 1 }}>
          <Typography variant="h4" component="h1">
            Job {job.job_id}
          </Typography>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mt: 1 }}>
            <JobStatusChip status={job.status} />
            {job.status === 'RUNNING' && (
              <Typography variant="body2" color="text.secondary">
                Live updates enabled
              </Typography>
            )}
          </Box>
        </Box>
        
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Tooltip title="Refresh">
            <IconButton onClick={() => refetch()} disabled={isLoading}>
              <RefreshIcon />
            </IconButton>
          </Tooltip>
          
          <Button
            variant="outlined"
            color="primary"
            startIcon={<RerunIcon />}
            onClick={() => setShowRerunForm(true)}
          >
            Rerun Job
          </Button>
          
          {['QUEUED', 'STARTING', 'RUNNING'].includes(job.status) && (
            <Button
              variant="outlined"
              color="error"
              startIcon={<CancelIcon />}
              onClick={handleCancelJob}
              disabled={cancelJobMutation.isPending}
            >
              Cancel Job
            </Button>
          )}
        </Box>
      </Box>

      {/* Error display */}
      {job.error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          <Typography variant="subtitle2">Job Error:</Typography>
          <pre style={{ margin: '8px 0 0 0', fontSize: '0.875rem' }}>
            {JSON.stringify(job.error, null, 2)}
          </pre>
        </Alert>
      )}

      {/* Tabs */}
      <Card>
        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs value={activeTab} onChange={(_, newValue) => setActiveTab(newValue)}>
            <Tab label="Summary" />
            <Tab label="Logs" />
            <Tab label={`Traces (${job.trace_files.length})`} />
            <Tab label="Context" />
            <Tab label="Last Task Output" />
          </Tabs>
        </Box>

        {/* Summary Tab */}
        <TabPanel value={activeTab} index={0}>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            <Box sx={{ display: 'flex', gap: 3, flexWrap: 'wrap' }}>
              <Paper sx={{ p: 2, flex: 1, minWidth: 300 }}>
                <Typography variant="h6" gutterBottom>Job Details</Typography>
                <List dense>
                  <ListItem>
                    <ListItemText 
                      primary="Job ID" 
                      secondary={job.job_id} 
                    />
                  </ListItem>
                  <ListItem>
                    <ListItemText 
                      primary="Status" 
                      secondary={<JobStatusChip status={job.status} />} 
                    />
                  </ListItem>
                  <ListItem>
                    <ListItemText 
                      primary="Max Tasks" 
                      secondary={job.max_tasks || 'Not specified'} 
                    />
                  </ListItem>
                </List>
              </Paper>
              
              <Paper sx={{ p: 2, flex: 1, minWidth: 300 }}>
                <Typography variant="h6" gutterBottom>Timing</Typography>
                <List dense>
                  <ListItem>
                    <ListItemText 
                      primary="Created" 
                      secondary={new Date(job.created_at).toLocaleString()} 
                    />
                  </ListItem>
                  <ListItem>
                    <ListItemText 
                      primary="Started" 
                      secondary={job.started_at ? new Date(job.started_at).toLocaleString() : 'Not started'} 
                    />
                  </ListItem>
                  <ListItem>
                    <ListItemText 
                      primary="Finished" 
                      secondary={job.finished_at ? new Date(job.finished_at).toLocaleString() : 'Not finished'} 
                    />
                  </ListItem>
                  <ListItem>
                    <ListItemText 
                      primary="Duration" 
                      secondary={formatDuration(job.started_at, job.finished_at)} 
                    />
                  </ListItem>
                </List>
              </Paper>
            </Box>
            
            <Paper sx={{ p: 2 }}>
              <Typography variant="h6" gutterBottom>Task Description</Typography>
              <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                {job.task_description}
              </Typography>
            </Paper>

            <Paper sx={{ p: 2 }}>
              <Typography variant="h6" gutterBottom>Environment Variables</Typography>
              {job.env_vars && Object.keys(job.env_vars).length > 0 ? (
                <List dense>
                  {Object.entries(job.env_vars)
                    .sort(([a], [b]) => a.localeCompare(b))
                    .map(([key, value]) => (
                      <ListItem key={key} disablePadding>
                        <ListItemText
                          primary={key}
                          secondary={value ?? ''}
                          primaryTypographyProps={{ sx: { fontFamily: 'monospace' } }}
                          secondaryTypographyProps={{
                            sx: { fontFamily: 'monospace', whiteSpace: 'pre-wrap' }
                          }}
                        />
                      </ListItem>
                    ))}
                </List>
              ) : (
                <Typography variant="body2" color="text.secondary">
                  No environment variables configured
                </Typography>
              )}
            </Paper>
          </Box>
        </TabPanel>

        {/* Logs Tab */}
        <TabPanel value={activeTab} index={1}>
          <Box sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 2 }}>
            <TextField
              select
              size="small"
              label="Tail Lines"
              value={logTailLines}
              onChange={(e) => setLogTailLines(Number(e.target.value))}
              sx={{ width: 150 }}
            >
              <MenuItem value={100}>100 lines</MenuItem>
              <MenuItem value={500}>500 lines</MenuItem>
              <MenuItem value={1000}>1000 lines</MenuItem>
              <MenuItem value={0}>All lines</MenuItem>
            </TextField>
            
            <Button
              variant="outlined"
              startIcon={<RefreshIcon />}
              onClick={() => refetchLogs()}
              disabled={logsLoading}
            >
              Refresh
            </Button>
            
            <Button
              variant="outlined"
              startIcon={<DownloadIcon />}
              onClick={handleDownloadLogs}
              disabled={logsLoading || !(logsData as any)?.logs}
            >
              Download
            </Button>
          </Box>
          
          {logsLoading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
              <CircularProgress />
            </Box>
          ) : (
            <Paper sx={{ p: 2, backgroundColor: '#000', color: '#fff', maxHeight: 600, overflow: 'auto' }}>
              <pre style={{ margin: 0, fontSize: '0.875rem', fontFamily: 'monospace' }}>
                {(logsData as any)?.logs || 'No logs available'}
              </pre>
            </Paper>
          )}
        </TabPanel>

        {/* Traces Tab */}
        <TabPanel value={activeTab} index={2}>
          {job.trace_files.length === 0 ? (
            <Typography color="text.secondary">
              No trace files available yet
            </Typography>
          ) : (
            <List>
              {job.trace_files.map((traceFile, index) => (
                <ListItem key={index} disablePadding>
                  <ListItemButton
                    onClick={() => handleTraceClick(traceFile)}
                    sx={{ borderRadius: 1 }}
                  >
                    <ListItemText
                      primary={traceFile}
                      secondary="Click to view in trace viewer"
                    />
                    <ExternalLinkIcon size={16} />
                  </ListItemButton>
                </ListItem>
              ))}
            </List>
          )}
        </TabPanel>

        {/* Context Tab */}
        <TabPanel value={activeTab} index={3}>
          {contextLoading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
              <CircularProgress />
            </Box>
          ) : contextData ? (
            <Box sx={{ '& .json-viewer': { fontSize: '14px' } }}>
              <JsonViewer value={contextData.context} label="Context" collapsed={false} />
            </Box>
          ) : (
            <Typography color="text.secondary">
              No context data available
            </Typography>
          )}
        </TabPanel>

        {/* Last Task Output Tab */}
        <TabPanel value={activeTab} index={4}>
          {contextLoading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
              <CircularProgress />
            </Box>
          ) : contextData?.context?.last_task_output ? (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
              {(() => {
                const lastTaskOutput = contextData.context.last_task_output;
                
                // If last_task_output is a dict/object, display each key as a separate block
                if (typeof lastTaskOutput === 'object' && lastTaskOutput !== null && !Array.isArray(lastTaskOutput)) {
                  return Object.entries(lastTaskOutput).map(([key, value]) => (
                    <Paper key={key} sx={{ p: 2 }}>
                      <Typography variant="h6" gutterBottom sx={{ 
                        fontFamily: 'monospace', 
                        backgroundColor: 'action.hover', 
                        px: 1, 
                        py: 0.5, 
                        borderRadius: 1,
                        display: 'inline-block'
                      }}>
                        {key}
                      </Typography>
                      <Box sx={{ mt: 2 }}>
                        {isJsonParsable(value) ? (
                          <JsonViewer 
                            value={value} 
                            collapsed={false} 
                            maxHeight={300}
                          />
                        ) : (
                          <Box sx={{ 
                            border: '1px solid var(--mui-palette-divider)',
                            borderRadius: 1,
                            p: 2,
                            backgroundColor: 'background.paper',
                            '& .markdown-content': {
                              fontFamily: 'inherit',
                              '& ul, & ol': {
                                margin: '0.5em 0',
                                paddingLeft: '1.5rem'
                              },
                              '& ul': {
                                listStyle: 'disc outside'
                              },
                              '& ol': {
                                listStyle: 'decimal outside'
                              },
                              '& li': {
                                marginBottom: '0.25em'
                              },
                              '& pre': {
                                backgroundColor: 'action.hover',
                                padding: '8px',
                                borderRadius: 1,
                                overflow: 'auto'
                              },
                              '& code': {
                                backgroundColor: 'action.hover',
                                padding: '2px 4px',
                                borderRadius: 1,
                                fontFamily: 'monospace'
                              }
                            }
                          }}>
                            <div className="markdown-content">
                              <ReactMarkdown>
                                {typeof value === 'string' ? value : String(value)}
                              </ReactMarkdown>
                            </div>
                          </Box>
                        )}
                      </Box>
                    </Paper>
                  ));
                } else {
                  // If last_task_output is not a dict, display it as a single block
                  return (
                    <Paper sx={{ p: 2 }}>
                      <Typography variant="h6" gutterBottom>
                        Last Task Output
                      </Typography>
                      <Box sx={{ mt: 2 }}>
                        {isJsonParsable(lastTaskOutput) ? (
                          <JsonViewer 
                            value={lastTaskOutput} 
                            collapsed={false} 
                            maxHeight={400}
                          />
                        ) : (
                          <Box sx={{ 
                            border: '1px solid var(--mui-palette-divider)',
                            borderRadius: 1,
                            p: 2,
                            backgroundColor: 'background.paper',
                            '& ul, & ol': {
                              margin: '0.5em 0',
                              paddingLeft: '1.5rem'
                            },
                            '& ul': {
                              listStyle: 'disc outside'
                            },
                            '& ol': {
                              listStyle: 'decimal outside'
                            },
                            '& li': {
                              marginBottom: '0.25em'
                            }
                          }}>
                            <ReactMarkdown>
                              {typeof lastTaskOutput === 'string' ? lastTaskOutput : String(lastTaskOutput)}
                            </ReactMarkdown>
                          </Box>
                        )}
                      </Box>
                    </Paper>
                  );
                }
              })()}
            </Box>
          ) : (
            <Typography color="text.secondary">
              No last task output available
            </Typography>
          )}
        </TabPanel>
      </Card>

      {/* Rerun job dialog */}
      <Dialog
        open={showRerunForm}
        onClose={() => setShowRerunForm(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          Rerun Job
        </DialogTitle>
        <DialogContent>
          <JobSubmitForm
            onCancel={() => setShowRerunForm(false)}
            onSuccess={(newJobId) => {
              setShowRerunForm(false);
              setShowSuccessAlert(true);
              navigate(`/jobs/${newJobId}`);
              // Auto-hide alert after 5 seconds
              setTimeout(() => setShowSuccessAlert(false), 5000);
            }}
            initialTaskDescription={job?.task_description || ''}
            initialMaxTasks={job?.max_tasks || 50}
            initialEnvVars={job?.env_vars || null}
          />
        </DialogContent>
      </Dialog>
    </Box>
  );
};