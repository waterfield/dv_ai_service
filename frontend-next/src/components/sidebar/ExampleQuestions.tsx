'use client';
import { List, ListItemButton, ListItemText, Typography, Box, Divider } from '@mui/material';

const EXAMPLES = [
  'Show me budget vs actuals for 2024',
  'Which cost centers are over budget?',
  'List all overdue AFEs',
  'Full picture for top 10 AFEs by % consumed',
  'Show rejected AFEs with reasons',
  'Budget trend by year',
  'Upcoming completions in the next 60 days',
  'Actual spend by region',
];

interface Props {
  onSelect: (q: string) => void;
  disabled?: boolean;
}

export default function ExampleQuestions({ onSelect, disabled }: Props) {
  return (
    <Box>
      <Typography variant="overline" sx={{ px: 2, color: 'text.secondary', fontSize: 10 }}>
        Example Questions
      </Typography>
      <Divider sx={{ mb: 1 }} />
      <List dense disablePadding>
        {EXAMPLES.map((q) => (
          <ListItemButton
            key={q}
            onClick={() => onSelect(q)}
            disabled={disabled}
            sx={{ borderRadius: 1, mx: 1, mb: 0.5 }}
          >
            <ListItemText
              primary={q}
              slotProps={{ primary: { variant: 'body2', sx: { fontSize: 12 } } }}
            />
          </ListItemButton>
        ))}
      </List>
    </Box>
  );
}
