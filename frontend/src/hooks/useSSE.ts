import { useCallback, useRef, useState } from 'react';
import type {
  AgentName,
  CompleteEvent,
  ErrorEvent,
  SSEEventType,
  TokenEvent,
  ValidationEvent,
} from '@/types';
import { parseSSEData } from '@/lib/utils';
import { useChatStore } from '@/stores/chatStore';

interface UseSSEOptions {
  onComplete?: (event: CompleteEvent) => void;
  onError?: (error: string) => void;
}

interface UseSSEReturn {
  sendMessage: (message: string) => Promise<void>;
  cancel: () => void;
  isConnected: boolean;
}

export function useSSE(options: UseSSEOptions = {}): UseSSEReturn {
  const { onComplete, onError } = options;
  const [isConnected, setIsConnected] = useState(false);
  const abortControllerRef = useRef<AbortController | null>(null);

  const {
    addUserMessage,
    addAssistantMessage,
    updateStreamingContent,
    setLoading,
    setError,
    updateAgentStatus,
    setCurrentAgent,
    resetWorkflow,
  } = useChatStore();

  const cancel = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsConnected(false);
    setLoading(false);
  }, [setLoading]);

  const sendMessage = useCallback(
    async (message: string) => {
      // Cancel any existing connection
      cancel();

      // Reset workflow and add user message
      resetWorkflow();
      addUserMessage(message);
      setLoading(true);
      setError(null);

      // Create new abort controller
      abortControllerRef.current = new AbortController();
      const { signal } = abortControllerRef.current;

      try {
        const response = await fetch('/api/chat', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ message }),
          signal,
        });

        if (!response.ok) {
          throw new Error(`HTTP error: ${response.status}`);
        }

        if (!response.body) {
          throw new Error('No response body');
        }

        setIsConnected(true);
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let streamedContent = '';

        while (true) {
          const { done, value } = await reader.read();

          if (done) {
            break;
          }

          buffer += decoder.decode(value, { stream: true });

          // Process complete SSE events
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6);
              if (data === '[DONE]') {
                continue;
              }

              const parsed = parseSSEData<{ event: SSEEventType; data: string }>(data);
              if (!parsed) continue;

              const eventData = parseSSEData<Record<string, unknown>>(parsed.data);
              if (!eventData) continue;

              // Handle different event types
              switch (parsed.event) {
                case 'agent_start': {
                  const agent = eventData.agent as AgentName;
                  setCurrentAgent(agent);
                  updateAgentStatus(agent, 'running');
                  break;
                }

                case 'tool_result': {
                  const agent = eventData.agent as AgentName;
                  updateAgentStatus(agent, 'completed');
                  break;
                }

                case 'validation': {
                  const validation = eventData as unknown as ValidationEvent;
                  updateAgentStatus(
                    'critic',
                    validation.revision_needed ? 'running' : 'completed',
                    `Iteration ${validation.iteration}`
                  );
                  break;
                }

                case 'token': {
                  const token = eventData as unknown as TokenEvent;
                  streamedContent += token.content;
                  updateStreamingContent(streamedContent);
                  break;
                }

                case 'complete': {
                  const complete = eventData as unknown as CompleteEvent;
                  addAssistantMessage(complete.content, {
                    queryType: complete.query_type,
                    iterations: complete.iterations,
                  });
                  onComplete?.(complete);
                  break;
                }

                case 'error': {
                  const error = eventData as unknown as ErrorEvent;
                  setError(error.error);
                  onError?.(error.error);
                  break;
                }

                case 'done': {
                  setIsConnected(false);
                  setLoading(false);
                  setCurrentAgent(null);
                  break;
                }

                case 'heartbeat':
                  // Ignore heartbeats
                  break;

                default:
                  console.log('Unknown event:', parsed.event);
              }
            }
          }
        }
      } catch (error) {
        if (error instanceof Error && error.name === 'AbortError') {
          // Request was cancelled
          return;
        }

        const errorMessage =
          error instanceof Error ? error.message : 'Unknown error';
        setError(errorMessage);
        onError?.(errorMessage);
      } finally {
        setIsConnected(false);
        setLoading(false);
        abortControllerRef.current = null;
      }
    },
    [
      cancel,
      resetWorkflow,
      addUserMessage,
      addAssistantMessage,
      updateStreamingContent,
      setLoading,
      setError,
      updateAgentStatus,
      setCurrentAgent,
      onComplete,
      onError,
    ]
  );

  return {
    sendMessage,
    cancel,
    isConnected,
  };
}
