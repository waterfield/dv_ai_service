'use client';
import { useEffect, useState } from 'react';
import { Chip } from '@mui/material';
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
    <Chip
      size="small"
      label={connected ? 'DB Connected' : 'DB Offline'}
      color={connected ? 'success' : 'error'}
      variant="outlined"
      sx={{ fontSize: 11 }}
    />
  );
}
