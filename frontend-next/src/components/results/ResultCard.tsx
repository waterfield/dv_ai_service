'use client';
import { useState } from 'react';
import { Card, CardContent, Tabs, Tab, Box, Typography, Skeleton } from '@mui/material';
import TableChartIcon from '@mui/icons-material/TableChart';
import BarChartIcon from '@mui/icons-material/BarChart';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import CodeIcon from '@mui/icons-material/Code';

import ResultTable from './ResultTable';
import ResultChart from './ResultChart';
import ResultSummary from './ResultSummary';
import QueryBadge from './QueryBadge';
import { QueryResult } from '@/lib/types';

interface Props {
  result: QueryResult;
  analyzeLoading?: boolean;
}

export default function ResultCard({ result, analyzeLoading }: Props) {
  const [tab, setTab] = useState(0);
  const { chat, execute, analyze } = result;

  if (!execute) {
    return (
      <Card sx={{ mt: 1 }}>
        <CardContent sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
          <Skeleton variant="rectangular" height={20} width="60%" />
          <Skeleton variant="rectangular" height={20} width="80%" />
          <Skeleton variant="rectangular" height={20} width="40%" />
        </CardContent>
      </Card>
    );
  }

  if (execute.status === 'error') {
    return (
      <Card sx={{ mt: 1 }}>
        <CardContent>
          <Typography variant="body2" color="error">
            {execute.error ?? 'Execution failed'}
          </Typography>
        </CardContent>
      </Card>
    );
  }

  const { columns, rows, row_count } = execute;

  return (
    <Card sx={{ mt: 1, overflow: 'visible' }}>
      <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tabs value={tab} onChange={(_, v) => setTab(v)} variant="scrollable" scrollButtons="auto">
          <Tab icon={<TableChartIcon fontSize="small" />} iconPosition="start" label={`Table (${row_count})`} />
          <Tab icon={<BarChartIcon fontSize="small" />} iconPosition="start" label="Chart" />
          <Tab icon={<AutoAwesomeIcon fontSize="small" />} iconPosition="start" label="Summary" />
          <Tab icon={<CodeIcon fontSize="small" />} iconPosition="start" label="Query" />
        </Tabs>
      </Box>

      {tab === 0 && (
        <ResultTable columns={columns} rows={rows} rowCount={row_count} />
      )}
      {tab === 1 && (
        <Box sx={{ p: 1 }}>
          <ResultChart columns={columns} rows={rows} chartConfig={analyze?.chart} />
        </Box>
      )}
      {tab === 2 && (
        <ResultSummary summary={analyze?.summary} loading={analyzeLoading} />
      )}
      {tab === 3 && (
        <QueryBadge chat={chat} />
      )}
    </Card>
  );
}
