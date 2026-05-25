'use client';
import { Box, Typography } from '@mui/material';
import { BarChart } from '@mui/x-charts/BarChart';
import { LineChart } from '@mui/x-charts/LineChart';
import { PieChart } from '@mui/x-charts/PieChart';
import { ChartConfig } from '@/lib/types';

interface Props {
  columns: string[];
  rows: Record<string, unknown>[];
  chartConfig?: ChartConfig;
}

function toNumber(v: unknown): number {
  const n = Number(v);
  return isNaN(n) ? 0 : n;
}

export default function ResultChart({ rows, chartConfig }: Props) {
  if (!chartConfig || !rows.length) {
    return (
      <Box sx={{ p: 3, textAlign: 'center' }}>
        <Typography color="text.secondary">
          {!chartConfig ? 'Analyzing data for best chart...' : 'No data to chart'}
        </Typography>
      </Box>
    );
  }

  const { type, x_col, y_cols, title } = chartConfig;

  if (type === 'table') {
    return (
      <Box sx={{ p: 3, textAlign: 'center' }}>
        <Typography color="text.secondary">This data is best viewed as a table</Typography>
      </Box>
    );
  }

  const xData = rows.map((r) => String(r[x_col] ?? ''));
  const series = y_cols.map((col) => ({
    data: rows.map((r) => toNumber(r[col])),
    label: col,
  }));

  if (type === 'pie') {
    const pieData = rows.map((r, i) => ({
      id: i,
      value: toNumber(r[y_cols[0]]),
      label: String(r[x_col] ?? ''),
    }));
    return (
      <Box>
        <Typography variant="subtitle2" sx={{ mb: 1, px: 1 }}>{title}</Typography>
        <PieChart series={[{ data: pieData, innerRadius: 40 }]} height={300} />
      </Box>
    );
  }

  if (type === 'line') {
    return (
      <Box>
        <Typography variant="subtitle2" sx={{ mb: 1, px: 1 }}>{title}</Typography>
        <LineChart
          xAxis={[{ scaleType: 'band', data: xData }]}
          series={series}
          height={300}
        />
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="subtitle2" sx={{ mb: 1, px: 1 }}>{title}</Typography>
      <BarChart
        xAxis={[{ scaleType: 'band', data: xData }]}
        series={series}
        height={300}
      />
    </Box>
  );
}
