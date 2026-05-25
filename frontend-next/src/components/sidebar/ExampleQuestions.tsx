'use client';
import { Typography, Box } from '@mui/material';
import BoltIcon from '@mui/icons-material/Bolt';
import BarChartIcon from '@mui/icons-material/BarChart';
import ListAltIcon from '@mui/icons-material/ListAlt';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import GroupsIcon from '@mui/icons-material/Groups';
import CalendarMonthIcon from '@mui/icons-material/CalendarMonth';
import PieChartIcon from '@mui/icons-material/PieChart';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';

const EXAMPLES = [
  { q: 'Show me budget vs actuals for 2024', icon: BarChartIcon, color: '#f5a623' },
  { q: 'Which cost centers are over budget?', icon: WarningAmberIcon, color: '#ef4444' },
  { q: 'List all overdue AFEs', icon: ListAltIcon, color: '#6b7280' },
  { q: 'Full picture for top 10 AFEs by % consumed', icon: BoltIcon, color: '#f5a623' },
  { q: 'Show rejected AFEs with reasons', icon: WarningAmberIcon, color: '#8b5cf6' },
  { q: 'Budget trend by year', icon: TrendingUpIcon, color: '#22c55e' },
  { q: 'Upcoming completions in the next 60 days', icon: CalendarMonthIcon, color: '#3b82f6' },
  { q: 'Actual spend by region', icon: PieChartIcon, color: '#f5a623' },
];

interface Props {
  onSelect: (q: string) => void;
  disabled?: boolean;
}

export default function ExampleQuestions({ onSelect, disabled }: Props) {
  return (
    <Box>
      <Typography
        variant="overline"
        sx={{ px: 2, color: 'rgba(255,255,255,0.5)', fontSize: 10, display: 'block', mb: 0.5 }}
      >
        Suggested Questions
      </Typography>
      <Box sx={{ px: 1, display: 'flex', flexDirection: 'column', gap: 0.5 }}>
        {EXAMPLES.map(({ q, icon: Icon, color }) => (
          <Box
            key={q}
            onClick={() => !disabled && onSelect(q)}
            sx={{
              display: 'flex', alignItems: 'flex-start', gap: 1.25, p: 1.25,
              borderRadius: 1.5,
              cursor: disabled ? 'default' : 'pointer',
              opacity: disabled ? 0.5 : 1,
              transition: 'background 0.15s',
              '&:hover': { bgcolor: disabled ? 'transparent' : 'rgba(255,255,255,0.08)' },
            }}
          >
            <Box
              sx={{
                width: 26, height: 26, borderRadius: 1, flexShrink: 0,
                bgcolor: `${color}22`,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}
            >
              <Icon sx={{ fontSize: 15, color }} />
            </Box>
            <Typography variant="body2" sx={{ fontSize: 12, color: 'rgba(255,255,255,0.85)', lineHeight: 1.4, pt: 0.25 }}>
              {q}
            </Typography>
          </Box>
        ))}
      </Box>
    </Box>
  );
}
