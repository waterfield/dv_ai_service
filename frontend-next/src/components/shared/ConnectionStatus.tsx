'use client';
import { useEffect, useState } from 'react';
import { Box, Typography } from '@mui/material';
import CircleIcon from '@mui/icons-material/Circle';
import { apiHealth } from '@/lib/api';

export default function ConnectionStatus() {
  const [connected, setConnected] = useState<boolean | null>(null);

  useEffect(() => {
    apiHealth()
      .then((r) => setConnected(r.database_connected))
      .catch(() => setConnected(false));
  }, []);

  if (connected === null) return null;

  return (
    <Box
      sx={{
        display: 'flex', alignItems: 'center', gap: 0.75, px: 1.5, py: 0.5,
        bgcolor: connected ? 'rgba(34,197,94,0.15)' : 'rgba(239,68,68,0.15)',
        borderRadius: 2,
      }}
    >
      <CircleIcon sx={{ fontSize: 8, color: connected ? '#22c55e' : '#ef4444' }} />
      <Typography variant="caption" sx={{ color: connected ? '#22c55e' : '#ef4444', fontWeight: 600, fontSize: 11 }}>
        {connected ? 'Connected to database' : 'Database offline'}
      </Typography>
    </Box>
  );
}
