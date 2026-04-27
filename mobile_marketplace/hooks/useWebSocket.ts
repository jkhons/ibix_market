import { useEffect, useRef, useCallback, useState } from 'react';
import ENV from '@/constants/config';
import { secureStorage } from '@/utils/storage';
import { STORAGE_KEYS } from '@/constants/config';

type MessageHandler = (data: unknown) => void;

interface UseWebSocketOptions {
  autoConnect?: boolean;
  reconnectAttempts?: number;
  reconnectInterval?: number;
}

export function useWebSocket(
  path: string,
  onMessage: MessageHandler,
  options: UseWebSocketOptions = {},
) {
  const {
    autoConnect = true,
    reconnectAttempts = 5,
    reconnectInterval = 3000,
  } = options;

  const wsRef = useRef<WebSocket | null>(null);
  const attemptsRef = useRef(0);
  const [connected, setConnected] = useState(false);

  const connect = useCallback(async () => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const token = await secureStorage.get(STORAGE_KEYS.ACCESS_TOKEN);
    if (!token) return;

    const url = `${ENV.WS_BASE_URL}${path}?token=${encodeURIComponent(token)}`;
    const ws = new WebSocket(url);

    ws.onopen = () => {
      setConnected(true);
      attemptsRef.current = 0;
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onMessage(data);
      } catch {
        // malformed message
      }
    };

    ws.onclose = () => {
      setConnected(false);
      if (attemptsRef.current < reconnectAttempts) {
        attemptsRef.current++;
        setTimeout(connect, reconnectInterval * attemptsRef.current);
      }
    };

    ws.onerror = () => {
      ws.close();
    };

    wsRef.current = ws;
  }, [path, onMessage, reconnectAttempts, reconnectInterval]);

  const disconnect = useCallback(() => {
    attemptsRef.current = reconnectAttempts;
    wsRef.current?.close();
    wsRef.current = null;
    setConnected(false);
  }, [reconnectAttempts]);

  const send = useCallback((data: unknown) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  }, []);

  useEffect(() => {
    if (autoConnect) connect();
    return () => disconnect();
  }, [autoConnect, connect, disconnect]);

  return { connected, connect, disconnect, send };
}
