'use client';
import { DataGrid, GridColDef, GridToolbar } from '@mui/x-data-grid';
import { Box, Typography } from '@mui/material';

interface Props {
  columns: string[];
  rows: Record<string, unknown>[];
  rowCount: number;
}

export default function ResultTable({ columns, rows, rowCount }: Props) {
  if (!rows.length) {
    return (
      <Box sx={{ p: 3, textAlign: 'center' }}>
        <Typography color="text.secondary">No results returned</Typography>
      </Box>
    );
  }

  const gridColumns: GridColDef[] = columns.map((col) => ({
    field: col,
    headerName: col,
    flex: 1,
    minWidth: 120,
    valueFormatter: (value: unknown) => {
      if (typeof value === 'number') {
        return Number.isInteger(value)
          ? value.toLocaleString()
          : value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
      }
      return value;
    },
  }));

  const gridRows = rows.map((row, i) => ({ id: i, ...row }));

  return (
    <Box sx={{ height: 420, width: '100%' }}>
      <DataGrid
        rows={gridRows}
        columns={gridColumns}
        pageSizeOptions={[10, 25, 50]}
        initialState={{ pagination: { paginationModel: { pageSize: 10 } } }}
        slots={{ toolbar: GridToolbar }}
        slotProps={{ toolbar: { showQuickFilter: true } }}
        density="compact"
        disableRowSelectionOnClick
      />
    </Box>
  );
}
