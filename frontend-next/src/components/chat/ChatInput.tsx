'use client';
import { useState, KeyboardEvent } from 'react';
import { Box, TextField, IconButton, CircularProgress } from '@mui/material';
import SendIcon from '@mui/icons-material/Send';

interface Props {
  onSend: (query: string) => void;
  disabled?: boolean;
  loading?: boolean;
}

export default function ChatInput({ onSend, disabled, loading }: Props) {
  const [value, setValue] = useState('');

  const submit = () => {
    const q = value.trim();
    if (!q || disabled || loading) return;
    onSend(q);
    setValue('');
  };

  const onKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <Box
      sx={{
        display: 'flex', gap: 1, p: 2,
        borderTop: '1px solid', borderColor: 'divider',
        bgcolor: 'background.paper',
      }}
    >
      <TextField
        fullWidth
        multiline
        maxRows={4}
        placeholder="Ask a question about AFE data..."
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={onKeyDown}
        disabled={disabled || loading}
        variant="outlined"
        size="small"
        sx={{ '& .MuiOutlinedInput-root': { borderRadius: 3 } }}
      />
      <IconButton
        color="primary"
        onClick={submit}
        disabled={!value.trim() || disabled || loading}
        sx={{ bgcolor: 'primary.main', color: '#fff', '&:hover': { bgcolor: 'primary.dark' }, borderRadius: 2 }}
      >
        {loading ? <CircularProgress size={20} color="inherit" /> : <SendIcon />}
      </IconButton>
    </Box>
  );
}
