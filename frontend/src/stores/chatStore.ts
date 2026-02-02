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

interface ChatState {
  // Conversation
  messages: ChatMessage[];
  isLoading: boolean;
  error: string | null;
  conversationId: string | null;

  // Workflow visualization
  workflowSteps: WorkflowStep[];
  currentAgent: AgentName | null;

  // Streaming
  streamingContent: string;

  // Actions
  addUserMessage: (content: string) => void;
  addAssistantMessage: (
    content: string,
    metadata?: ChatMessage['metadata']
  ) => void;
  updateStreamingContent: (content: string) => void;
  setLoading: (isLoading: boolean) => void;
  setError: (error: string | null) => void;
  updateAgentStatus: (agent: AgentName, status: AgentStatus, details?: string) => void;
  setCurrentAgent: (agent: AgentName | null) => void;
  resetWorkflow: () => void;
  clearConversation: () => void;
}

const initialWorkflowSteps: WorkflowStep[] = [
  { agent: 'router', status: 'idle' },
  { agent: 'researcher', status: 'idle' },
  { agent: 'analyst', status: 'idle' },
  { agent: 'critic', status: 'idle' },
];

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
