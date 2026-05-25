'use client';
import { Box, Chip, Typography, Collapse } from '@mui/material';
import { useState } from 'react';
import CodeIcon from '@mui/icons-material/Code';
import { ChatResponse } from '@/lib/types';

interface Props {
  chat: ChatResponse;
}

export default function QueryBadge({ chat }: Props) {
  const [open, setOpen] = useState(false);

  return (
    <Box sx={{ p: 2 }}>
      <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', alignItems: 'center', mb: 1 }}>
        {chat.tool_name && (
          <Chip label={chat.tool_name} size="small" color="primary" variant="outlined" />
        )}
        {chat.template_key && (
          <Chip label={chat.template_key} size="small" color="secondary" variant="outlined" />
        )}
        <Chip
          icon={<CodeIcon />}
          label="View SQL"
          size="small"
          onClick={() => setOpen(!open)}
          sx={{ cursor: 'pointer' }}
        />
      </Box>
      <Collapse in={open}>
        <Box
          component="pre"
          sx={{
            p: 2, borderRadius: 2, bgcolor: '#0f172a',
            fontSize: 12, overflow: 'auto', maxHeight: 300,
            fontFamily: '"JetBrains Mono", monospace',
            color: '#e2e8f0',
          }}
        >
          {chat.sql_query}
        </Box>
        {chat.params && Object.keys(chat.params).length > 0 && (
          <Box sx={{ mt: 1 }}>
            <Typography variant="caption" color="text.secondary">Bind params:</Typography>
            <Box component="pre" sx={{ fontSize: 11, color: 'text.secondary', mt: 0.5 }}>
              {JSON.stringify(chat.params, null, 2)}
            </Box>
          </Box>
        )}
      </Collapse>
    </Box>
  );
}
