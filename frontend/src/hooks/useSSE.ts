/**
 * Custom hook for Server-Sent Events (SSE) streaming with the chat API.
 *
 * Handles connection lifecycle, event parsing, and state updates
 * for real-time agent workflow streaming.
 *
 * @module useSSE
 */

import { useCallback, useRef, useState } from 'react';
import type {
  AgentName,
  AgentStartEvent,
  CompleteEvent,
  ErrorEvent,
  SSEEventType,
  TokenEvent,
  ToolResultEvent,
  ValidationEvent,
} from '@/types';
import { parseSSEData } from '@/lib/utils';
import { useChatStore } from '@/stores/chatStore';

/**
 * Type guard to check if event data is an AgentStartEvent.
 */
function isAgentStartEvent(data: Record<string, unknown>): data is AgentStartEvent {
  return (
    typeof data.agent === 'string' &&
    data.status === 'running'
  );
}

/**
 * Type guard to check if event data is a ToolResultEvent.
 */
function isToolResultEvent(data: Record<string, unknown>): data is ToolResultEvent {
  return typeof data.agent === 'string';
}

/**
 * Type guard to check if event data is a ValidationEvent.
 */
function isValidationEvent(data: Record<string, unknown>): data is ValidationEvent {
  return (
    typeof data.status === 'string' &&
    typeof data.iteration === 'number' &&
    typeof data.revision_needed === 'boolean'
  );
}

/**
 * Type guard to check if event data is a TokenEvent.
 */
function isTokenEvent(data: Record<string, unknown>): data is TokenEvent {
  return typeof data.content === 'string';
}

/**
 * Type guard to check if event data is a CompleteEvent.
 */
function isCompleteEvent(data: Record<string, unknown>): data is CompleteEvent {
  return (
    typeof data.content === 'string' &&
    typeof data.query_type === 'string' &&
    typeof data.iterations === 'number'
  );
}

/**
 * Type guard to check if event data is an ErrorEvent.
 */
function isErrorEvent(data: Record<string, unknown>): data is ErrorEvent {
  return (
    typeof data.error === 'string' &&
    typeof data.type === 'string'
  );
}

/**
 * Options for configuring the useSSE hook behavior.
 */
interface UseSSEOptions {
  /**
   * Callback invoked when the streaming completes successfully.
   * @param event - The complete event containing the final response.
   */
  onComplete?: (event: CompleteEvent) => void;

  /**
   * Callback invoked when an error occurs during streaming.
   * @param error - The error message string.
   */
  onError?: (error: string) => void;
}

/**
 * Return type of the useSSE hook.
 */
interface UseSSEReturn {
  /**
   * Send a message to the chat API and stream the response.
   * @param message - The user's message to send.
   */
  sendMessage: (message: string) => Promise<void>;

  /**
   * Cancel the current streaming connection.
   */
  cancel: () => void;

  /**
   * Whether there is an active SSE connection.
   */
  isConnected: boolean;
}

/**
 * Hook for managing SSE streaming connections to the chat API.
 *
 * @param options - Configuration options for callbacks.
 * @returns Object with sendMessage, cancel, and isConnected.
 *
 * @example
 * ```tsx
 * const { sendMessage, cancel, isConnected } = useSSE({
 *   onComplete: (event) => console.log('Done:', event.content),
 *   onError: (error) => console.error('Error:', error),
 * });
 *
 * await sendMessage('What are my top products?');
 * ```
 */
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

              // Handle different event types with type guards
              switch (parsed.event) {
                case 'agent_start': {
                  if (isAgentStartEvent(eventData)) {
                    const agent = eventData.agent as AgentName;
                    setCurrentAgent(agent);
                    updateAgentStatus(agent, 'running');
                  }
                  break;
                }

                case 'tool_result': {
                  if (isToolResultEvent(eventData)) {
                    const agent = eventData.agent as AgentName;
                    updateAgentStatus(agent, 'completed');
                  }
                  break;
                }

                case 'validation': {
                  if (isValidationEvent(eventData)) {
                    updateAgentStatus(
                      'critic',
                      eventData.revision_needed ? 'running' : 'completed',
                      `Iteration ${eventData.iteration}`
                    );
                  }
                  break;
                }

                case 'token': {
                  if (isTokenEvent(eventData)) {
                    streamedContent += eventData.content;
                    updateStreamingContent(streamedContent);
                  }
                  break;
                }

                case 'complete': {
                  if (isCompleteEvent(eventData)) {
                    addAssistantMessage(eventData.content, {
                      queryType: eventData.query_type,
                      iterations: eventData.iterations,
                    });
                    onComplete?.(eventData);
                  }
                  break;
                }

                case 'error': {
                  if (isErrorEvent(eventData)) {
                    setError(eventData.error);
                    onError?.(eventData.error);
                  }
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
