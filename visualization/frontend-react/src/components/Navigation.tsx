/**
 * Navigation component for switching between trace viewer and job management
 */

import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { 
  Box, 
  Breadcrumbs, 
  Typography, 
  Button,
  AppBar,
  Toolbar,
  Container
} from '@mui/material';
import { 
  Activity as TimelineIcon,
  Briefcase as JobsIcon,
  FileText as DocsIcon
} from 'lucide-react';

export const Navigation: React.FC = () => {
  const location = useLocation();
  // Treat root path '/' the same as '/jobs' so the highlighted tab matches
  // the default route content rendered at '/'.
  const isJobsPath = location.pathname === '/' || location.pathname.startsWith('/jobs');
  const isTracesPath = location.pathname.startsWith('/traces');
  const isSopDocsPath = location.pathname.startsWith('/sop-docs');

  return (
    <AppBar position="static" elevation={1} sx={{ backgroundColor: 'white', color: 'text.primary' }}>
      <Container maxWidth="lg">
        <Toolbar sx={{ justifyContent: 'space-between', py: 1 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 3 }}>
            <Typography variant="h5" component="h1" sx={{ fontWeight: 600, color: 'primary.main' }}>
              Doc Flow Agent
            </Typography>
            
            <Box sx={{ display: 'flex', gap: 1 }}>
              <Button
                component={Link}
                to="/jobs"
                variant={isJobsPath ? 'contained' : 'text'}
                startIcon={<JobsIcon size={18} />}
                sx={{ textTransform: 'none' }}
              >
                Jobs
              </Button>
              <Button
                component={Link}
                to="/traces"
                variant={isTracesPath ? 'contained' : 'text'}
                startIcon={<TimelineIcon size={18} />}
                sx={{ textTransform: 'none' }}
              >
                Trace Viewer
              </Button>
              <Button
                component={Link}
                to="/sop-docs"
                variant={isSopDocsPath ? 'contained' : 'text'}
                startIcon={<DocsIcon size={18} />}
                sx={{ textTransform: 'none' }}
              >
                SOP Docs
              </Button>
            </Box>
          </Box>

          {/* Breadcrumbs for current path */}
          <Box>
            <Breadcrumbs aria-label="breadcrumb">
              {location.pathname.split('/').filter(Boolean).map((segment, index, arr) => {
                const path = '/' + arr.slice(0, index + 1).join('/');
                const isLast = index === arr.length - 1;
                
                return isLast ? (
                  <Typography key={path} color="text.primary" sx={{ textTransform: 'capitalize' }}>
                    {segment}
                  </Typography>
                ) : (
                  <Link
                    key={path}
                    to={path}
                    style={{ 
                      textDecoration: 'none', 
                      color: 'inherit',
                      textTransform: 'capitalize'
                    }}
                  >
                    {segment}
                  </Link>
                );
              })}
            </Breadcrumbs>
          </Box>
        </Toolbar>
      </Container>
    </AppBar>
  );
};