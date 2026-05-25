'use client';
import { useRef, useState } from 'react';
import { Box, Drawer, Toolbar, AppBar, Typography, Divider } from '@mui/material';
import { v4 as uuidv4 } from 'uuid';

import ChatInput from '@/components/chat/ChatInput';
import ChatMessage from '@/components/chat/ChatMessage';
import TypingIndicator from '@/components/chat/TypingIndicator';
import ExampleQuestions from '@/components/sidebar/ExampleQuestions';
import ConnectionStatus from '@/components/shared/ConnectionStatus';
import { apiChat, apiExecute, apiAnalyze } from '@/lib/api';
import { ConversationEntry, QueryResult } from '@/lib/types';

const DRAWER_WIDTH = 280;
const SESSION_ID = uuidv4();

export default function Home() {
  const [entries, setEntries] = useState<ConversationEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [analyzingId, setAnalyzingId] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () =>
    setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: 'smooth' }), 100);

  const handleQuery = async (userQuery: string) => {
    if (loading) return;
    setLoading(true);

    const id = uuidv4();
    const placeholder: ConversationEntry = {
      id, userQuery, timestamp: new Date().toISOString(),
      result: { chat: { query_id: id, status: 'sql_generated', user_query: userQuery, timestamp: '' } },
    };
    setEntries((prev) => [...prev, placeholder]);
    scrollToBottom();

    try {
      const chat = await apiChat({ user_query: userQuery, session_id: SESSION_ID });

      if (['invalid_params', 'no_template', 'error'].includes(chat.status)) {
        setEntries((prev) => prev.map((e) => e.id === id ? { ...e, result: { chat } } : e));
        setLoading(false);
        scrollToBottom();
        return;
      }

      const execute = await apiExecute({
        sql_query: chat.sql_query!,
        params: chat.params ?? {},
        user_query: userQuery,
        session_id: SESSION_ID,
      });

      const result: QueryResult = { chat, execute };
      setEntries((prev) => prev.map((e) => e.id === id ? { ...e, result } : e));
      setLoading(false);
      scrollToBottom();

      if (execute.status === 'success' && execute.rows.length > 0) {
        setAnalyzingId(id);
        try {
          const analyze = await apiAnalyze({
            user_query: userQuery,
            columns: execute.columns,
            rows: execute.rows,
            row_count: execute.row_count,
            session_id: SESSION_ID,
          });
          setEntries((prev) =>
            prev.map((e) => e.id === id ? { ...e, result: { ...e.result, analyze } } : e)
          );
        } catch {
          // analyze failure is non-fatal
        } finally {
          setAnalyzingId(null);
        }
      }
    } catch (err) {
      const errMsg = err instanceof Error ? err.message : 'Unknown error';
      setEntries((prev) =>
        prev.map((e) =>
          e.id === id
            ? { ...e, result: { chat: { query_id: id, status: 'error', user_query: userQuery, error: errMsg, timestamp: '' } } }
            : e
        )
      );
      setLoading(false);
    }
  };

  return (
    <Box sx={{ display: 'flex', height: '100vh' }}>
      <Drawer
        variant="permanent"
        sx={{
          width: DRAWER_WIDTH,
          flexShrink: 0,
          '& .MuiDrawer-paper': {
            width: DRAWER_WIDTH, boxSizing: 'border-box',
            borderRight: '1px solid', borderColor: 'divider',
          },
        }}
      >
        <Toolbar sx={{ px: 2, gap: 1 }}>
          <Typography variant="h6" noWrap sx={{ flex: 1, fontSize: 15 }}>
            W AI Reporting
          </Typography>
          <ConnectionStatus />
        </Toolbar>
        <Divider />
        <Box sx={{ overflow: 'auto', py: 1 }}>
          <ExampleQuestions onSelect={handleQuery} disabled={loading} />
        </Box>
      </Drawer>

      <Box sx={{ display: 'flex', flexDirection: 'column', flex: 1, overflow: 'hidden' }}>
        <AppBar
          position="static"
          elevation={0}
          sx={{ bgcolor: 'background.paper', borderBottom: '1px solid', borderColor: 'divider' }}
        >
          <Toolbar>
            <Typography variant="subtitle1" sx={{ color: 'text.primary' }}>
              AFE Analytics Chat
            </Typography>
          </Toolbar>
        </AppBar>

        <Box sx={{ flex: 1, overflow: 'auto', p: 3 }}>
          {entries.length === 0 && (
            <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '60%' }}>
              <Typography color="text.secondary">Ask a question to get started</Typography>
            </Box>
          )}
          {entries.map((entry) => (
            <ChatMessage
              key={entry.id}
              entry={entry}
              analyzeLoading={analyzingId === entry.id}
            />
          ))}
          {loading && <TypingIndicator />}
          <div ref={bottomRef} />
        </Box>

        <ChatInput onSend={handleQuery} loading={loading} />
      </Box>
    </Box>
  );
}
