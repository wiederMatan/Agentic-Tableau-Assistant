/**
 * Zustand store for managing chat state and workflow visualization.
 *
 * @module chatStore
 */

import { create } from 'zustand';
import type {
  AgentName,
  AgentStatus,
  ChatMessage,
  QueryType,
  ValidationStatus,
  WorkflowStep,
} from '@/types';
import { generateId } from '@/lib/utils';

/**
 * Chat state interface defining the store shape.
 */
interface ChatState {
  // Conversation
  /** List of all chat messages in the conversation. */
  messages: ChatMessage[];
  /** Whether a request is currently in progress. */
  isLoading: boolean;
  /** Current error message, if any. */
  error: string | null;
  /** Unique identifier for the current conversation. */
  conversationId: string | null;

  // Workflow visualization
  /** Current workflow step status for each agent. */
  workflowSteps: WorkflowStep[];
  /** The currently active agent in the workflow. */
  currentAgent: AgentName | null;

  // Streaming
  /** Content being streamed from the current response. */
  streamingContent: string;

  // Actions
  /**
   * Add a user message to the conversation.
   * @param content - The message content.
   */
  addUserMessage: (content: string) => void;

  /**
   * Add an assistant message to the conversation.
   * @param content - The message content.
   * @param metadata - Optional metadata about the response.
   */
  addAssistantMessage: (
    content: string,
    metadata?: ChatMessage['metadata']
  ) => void;

  /**
   * Update the streaming content buffer.
   * @param content - The accumulated streamed content.
   */
  updateStreamingContent: (content: string) => void;

  /**
   * Set the loading state.
   * @param isLoading - Whether a request is in progress.
   */
  setLoading: (isLoading: boolean) => void;

  /**
   * Set or clear the error state.
   * @param error - Error message or null to clear.
   */
  setError: (error: string | null) => void;

  /**
   * Update the status of a specific agent in the workflow.
   * @param agent - The agent to update.
   * @param status - The new status.
   * @param details - Optional status details.
   */
  updateAgentStatus: (agent: AgentName, status: AgentStatus, details?: string) => void;

  /**
   * Set the currently active agent.
   * @param agent - The agent name or null if none active.
   */
  setCurrentAgent: (agent: AgentName | null) => void;

  /**
   * Reset the workflow steps to initial state.
   */
  resetWorkflow: () => void;

  /**
   * Clear the entire conversation and reset all state.
   */
  clearConversation: () => void;
}

/** Initial workflow steps with all agents in idle state. */
const initialWorkflowSteps: WorkflowStep[] = [
  { agent: 'router', status: 'idle' },
  { agent: 'researcher', status: 'idle' },
  { agent: 'analyst', status: 'idle' },
  { agent: 'critic', status: 'idle' },
];

/**
 * Zustand store for chat state management.
 *
 * @example
 * ```tsx
 * const { messages, isLoading, addUserMessage } = useChatStore();
 *
 * // Add a message
 * addUserMessage('What are my top products?');
 *
 * // Access state
 * console.log(messages.length, isLoading);
 * ```
 */
export const useChatStore = create<ChatState>((set, get) => ({
  // Initial state
  messages: [],
  isLoading: false,
  error: null,
  conversationId: null,
  workflowSteps: [...initialWorkflowSteps],
  currentAgent: null,
  streamingContent: '',

  // Actions
  addUserMessage: (content: string) => {
    const message: ChatMessage = {
      id: generateId(),
      role: 'user',
      content,
      timestamp: new Date(),
    };
    set((state) => ({
      messages: [...state.messages, message],
      streamingContent: '',
    }));
  },

  addAssistantMessage: (content: string, metadata?: ChatMessage['metadata']) => {
    const message: ChatMessage = {
      id: generateId(),
      role: 'assistant',
      content,
      timestamp: new Date(),
      metadata,
    };
    set((state) => ({
      messages: [...state.messages, message],
      streamingContent: '',
    }));
  },

  updateStreamingContent: (content: string) => {
    set({ streamingContent: content });
  },

  setLoading: (isLoading: boolean) => {
    set({ isLoading });
  },

  setError: (error: string | null) => {
    set({ error, isLoading: false });
  },

  updateAgentStatus: (agent: AgentName, status: AgentStatus, details?: string) => {
    set((state) => ({
      workflowSteps: state.workflowSteps.map((step) =>
        step.agent === agent
          ? {
              ...step,
              status,
              details,
              startTime: status === 'running' ? new Date() : step.startTime,
              endTime: status === 'completed' || status === 'error' ? new Date() : step.endTime,
            }
          : step
      ),
    }));
  },

  setCurrentAgent: (agent: AgentName | null) => {
    set({ currentAgent: agent });
  },

  resetWorkflow: () => {
    set({
      workflowSteps: [...initialWorkflowSteps],
      currentAgent: null,
    });
  },

  clearConversation: () => {
    set({
      messages: [],
      isLoading: false,
      error: null,
      conversationId: null,
      workflowSteps: [...initialWorkflowSteps],
      currentAgent: null,
      streamingContent: '',
    });
  },
}));
