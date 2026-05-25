'use client';
import { Alert, AlertTitle, List, ListItem, ListItemText, Typography } from '@mui/material';
import { ChatResponse } from '@/lib/types';

interface Props {
  chat: ChatResponse;
}

export default function ErrorCard({ chat }: Props) {
  if (chat.status === 'no_template') {
    return (
      <Alert severity="info" sx={{ borderRadius: 2 }}>
        <AlertTitle>No matching template</AlertTitle>
        This question isn&apos;t covered by available data templates. Try rephrasing or ask about AFE budgets, actuals, or master data.
      </Alert>
    );
  }

  if (chat.status === 'invalid_params') {
    const fieldErrors = chat.error?.split(';').map((e) => e.trim()).filter(Boolean) ?? [];
    return (
      <Alert severity="warning" sx={{ borderRadius: 2 }}>
        <AlertTitle>
          Invalid parameters — {chat.tool_name} / {chat.template_key}
        </AlertTitle>
        <List dense disablePadding>
          {fieldErrors.map((err, i) => (
            <ListItem key={i} disableGutters>
              <ListItemText primary={err} slotProps={{ primary: { variant: 'body2' } }} />
            </ListItem>
          ))}
        </List>
      </Alert>
    );
  }

  return (
    <Alert severity="error" sx={{ borderRadius: 2 }}>
      <AlertTitle>Error</AlertTitle>
      <Typography variant="body2">{chat.error}</Typography>
    </Alert>
  );
}
