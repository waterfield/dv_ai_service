'use client';
import { Box, Typography, Skeleton } from '@mui/material';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';

interface Props {
  summary?: string;
  loading?: boolean;
}

export default function ResultSummary({ summary, loading }: Props) {
  if (loading) {
    return (
      <Box sx={{ p: 2 }}>
        <Skeleton width="90%" />
        <Skeleton width="75%" />
        <Skeleton width="60%" />
      </Box>
    );
  }
  if (!summary) return null;
  return (
    <Box sx={{ p: 2, display: 'flex', gap: 1.5, alignItems: 'flex-start' }}>
      <AutoAwesomeIcon sx={{ color: 'primary.main', mt: 0.3, fontSize: 18 }} />
      <Typography variant="body2" sx={{ lineHeight: 1.7, color: 'text.primary' }}>
        {summary}
      </Typography>
    </Box>
  );
}
