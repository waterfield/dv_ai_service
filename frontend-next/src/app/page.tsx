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
            bgcolor: '#0d3344', color: '#fff',
            borderRight: 'none',
          },
        }}
      >
        {/* Logo / branding */}
        <Box sx={{ px: 2, py: 2, display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <Box
            sx={{
              width: 36, height: 36, borderRadius: '50%',
              bgcolor: '#f5a623',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontWeight: 900, fontSize: 18, color: '#fff', flexShrink: 0,
            }}
          >
            W
          </Box>
          <Typography variant="h6" noWrap sx={{ fontSize: 15, color: '#fff', lineHeight: 1.2 }}>
            W ChatSQL
          </Typography>
        </Box>

        {/* Connection status */}
        <Box sx={{ px: 2, pb: 1.5 }}>
          <ConnectionStatus />
        </Box>

        <Divider sx={{ borderColor: 'rgba(255,255,255,0.12)' }} />

        <Box sx={{ overflow: 'auto', py: 1, flex: 1 }}>
          <ExampleQuestions onSelect={handleQuery} disabled={loading} />
        </Box>

        {/* Footer */}
        <Box sx={{ px: 2, py: 1.5, borderTop: '1px solid rgba(255,255,255,0.12)' }}>
          <Typography variant="caption" sx={{ color: '#f5a623', fontWeight: 600, fontSize: 10 }}>
            Powered by Wenergy AI
          </Typography>
        </Box>
      </Drawer>

      <Box sx={{ display: 'flex', flexDirection: 'column', flex: 1, overflow: 'hidden' }}>
        <AppBar
          position="static"
          elevation={0}
          sx={{ bgcolor: '#0d3344', borderBottom: 'none' }}
        >
          <Toolbar sx={{ gap: 1.5 }}>
            <Box
              sx={{
                width: 30, height: 30, borderRadius: '50%',
                bgcolor: '#f5a623',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontWeight: 900, fontSize: 15, color: '#fff', flexShrink: 0,
              }}
            >
              W
            </Box>
            <Typography variant="subtitle1" sx={{ color: '#fff', fontWeight: 600 }}>
              AFE Analytics Chat
            </Typography>
            <Box
              sx={{
                ml: 1, px: 1, py: 0.25,
                bgcolor: 'rgba(245,166,35,0.2)',
                border: '1px solid rgba(245,166,35,0.4)',
                borderRadius: 1,
              }}
            >
              <Typography variant="caption" sx={{ color: '#f5a623', fontSize: 10, fontWeight: 600 }}>
                Read-only
              </Typography>
            </Box>
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
