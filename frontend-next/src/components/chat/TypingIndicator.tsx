'use client';
import { Box, Avatar } from '@mui/material';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import { keyframes } from '@mui/system';

const bounce = keyframes`
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
  40% { transform: scale(1); opacity: 1; }
`;

export default function TypingIndicator() {
  return (
    <Box sx={{ display: 'flex', mb: 2, gap: 1, alignItems: 'center' }}>
      <Avatar sx={{ width: 32, height: 32, bgcolor: 'secondary.dark' }}>
        <SmartToyIcon fontSize="small" />
      </Avatar>
      <Box sx={{ display: 'flex', gap: 0.5, px: 2, py: 1.5, bgcolor: 'background.paper', borderRadius: '16px 16px 16px 4px' }}>
        {[0, 1, 2].map((i) => (
          <Box
            key={i}
            sx={{
              width: 8, height: 8, borderRadius: '50%', bgcolor: 'primary.main',
              animation: `${bounce} 1.2s ease-in-out ${i * 0.2}s infinite`,
            }}
          />
        ))}
      </Box>
    </Box>
  );
}
