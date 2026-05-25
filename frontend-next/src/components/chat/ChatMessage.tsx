'use client';
import { Box, Typography, Avatar } from '@mui/material';
import PersonIcon from '@mui/icons-material/Person';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import ResultCard from '@/components/results/ResultCard';
import ErrorCard from '@/components/shared/ErrorCard';
import { ConversationEntry } from '@/lib/types';

interface UserBubbleProps { text: string }
function UserBubble({ text }: UserBubbleProps) {
  return (
    <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: 2, gap: 1 }}>
      <Box
        sx={{
          maxWidth: '70%', px: 2, py: 1.5,
          bgcolor: 'primary.main', borderRadius: '16px 16px 4px 16px',
        }}
      >
        <Typography variant="body2" sx={{ color: '#fff' }}>{text}</Typography>
      </Box>
      <Avatar sx={{ width: 32, height: 32, bgcolor: 'primary.dark', alignSelf: 'flex-end' }}>
        <PersonIcon fontSize="small" />
      </Avatar>
    </Box>
  );
}

interface AssistantBubbleProps { entry: ConversationEntry; analyzeLoading?: boolean }
function AssistantBubble({ entry, analyzeLoading }: AssistantBubbleProps) {
  const { result } = entry;
  const { chat } = result;
  const isError = ['invalid_params', 'no_template', 'error'].includes(chat.status);

  return (
    <Box sx={{ display: 'flex', mb: 2, gap: 1 }}>
      <Avatar sx={{ width: 32, height: 32, bgcolor: 'secondary.dark', alignSelf: 'flex-start', mt: 0.5 }}>
        <SmartToyIcon fontSize="small" />
      </Avatar>
      <Box sx={{ flex: 1, maxWidth: '90%' }}>
        {isError ? (
          <ErrorCard chat={chat} />
        ) : (
          <ResultCard result={result} analyzeLoading={analyzeLoading} />
        )}
      </Box>
    </Box>
  );
}

interface Props {
  entry: ConversationEntry;
  analyzeLoading?: boolean;
}

export default function ChatMessage({ entry, analyzeLoading }: Props) {
  return (
    <>
      <UserBubble text={entry.userQuery} />
      <AssistantBubble entry={entry} analyzeLoading={analyzeLoading} />
    </>
  );
}
