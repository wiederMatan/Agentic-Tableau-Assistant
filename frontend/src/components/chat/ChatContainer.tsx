'use client';

import { useEffect, useRef } from 'react';
import { Bot, Loader2, MessageSquare } from 'lucide-react';
import { ChatMessage } from './ChatMessage';
import { ChatInput } from './ChatInput';
import { AgentWorkflow } from '@/components/agents/AgentWorkflow';
import { useChatStore } from '@/stores/chatStore';
import { useSSE } from '@/hooks/useSSE';

export function ChatContainer() {
  const { messages, isLoading, error, streamingContent } = useChatStore();
  const { sendMessage, cancel } = useSSE();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent]);

  return (
    <div className="flex h-full">
      {/* Main chat area */}
      <div className="flex-1 flex flex-col">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center p-8">
              <div className="w-16 h-16 rounded-full bg-tableau-blue/10 flex items-center justify-center mb-4">
                <MessageSquare className="w-8 h-8 text-tableau-blue" />
              </div>
              <h2 className="text-xl font-semibold text-gray-900 mb-2">
                Tableau Analytics Agent
              </h2>
              <p className="text-gray-500 max-w-md">
                Ask questions about your Tableau dashboards and data. I can help
                you find insights, analyze trends, and answer questions.
              </p>
              <div className="mt-6 flex flex-wrap gap-2 justify-center">
                {[
                  'What are my top-selling products?',
                  'Show sales by region',
                  'Find revenue trends',
                ].map((suggestion) => (
                  <button
                    key={suggestion}
                    onClick={() => sendMessage(suggestion)}
                    className="px-3 py-1.5 text-sm bg-gray-100 hover:bg-gray-200 rounded-full text-gray-700 transition-colors"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="divide-y divide-gray-200">
              {messages.map((message) => (
                <ChatMessage key={message.id} message={message} />
              ))}

              {/* Streaming content */}
              {streamingContent && (
                <div className="flex gap-3 p-4 bg-white">
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-tableau-blue flex items-center justify-center">
                    <Bot className="w-4 h-4 text-white" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-sm font-medium text-gray-900">
                        Agent
                      </span>
                      <Loader2 className="w-3 h-3 text-tableau-blue animate-spin" />
                    </div>
                    <div className="text-sm text-gray-700 whitespace-pre-wrap">
                      {streamingContent}
                    </div>
                  </div>
                </div>
              )}

              {/* Loading indicator */}
              {isLoading && !streamingContent && (
                <div className="flex gap-3 p-4 bg-white">
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-tableau-blue flex items-center justify-center">
                    <Bot className="w-4 h-4 text-white" />
                  </div>
                  <div className="flex items-center gap-2">
                    <Loader2 className="w-4 h-4 text-tableau-blue animate-spin" />
                    <span className="text-sm text-gray-500">Thinking...</span>
                  </div>
                </div>
              )}

              {/* Error message */}
              {error && (
                <div className="p-4 bg-red-50 border-l-4 border-red-500">
                  <p className="text-sm text-red-700">{error}</p>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input */}
        <ChatInput
          onSend={sendMessage}
          onCancel={cancel}
          isLoading={isLoading}
        />
      </div>

      {/* Workflow sidebar */}
      <div className="w-64 border-l border-gray-200 p-4 bg-white hidden lg:block">
        <AgentWorkflow />
      </div>
    </div>
  );
}
