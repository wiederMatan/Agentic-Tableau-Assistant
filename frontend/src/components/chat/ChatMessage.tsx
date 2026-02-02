'use client';

import { Bot, User } from 'lucide-react';
import { cn, formatTime } from '@/lib/utils';
import type { ChatMessage as ChatMessageType } from '@/types';

interface ChatMessageProps {
  message: ChatMessageType;
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === 'user';

  return (
    <div
      className={cn(
        'flex gap-3 p-4',
        isUser ? 'bg-gray-50' : 'bg-white'
      )}
    >
      {/* Avatar */}
      <div
        className={cn(
          'flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center',
          isUser ? 'bg-gray-200' : 'bg-tableau-blue'
        )}
      >
        {isUser ? (
          <User className="w-4 h-4 text-gray-600" />
        ) : (
          <Bot className="w-4 h-4 text-white" />
        )}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-sm font-medium text-gray-900">
            {isUser ? 'You' : 'Agent'}
          </span>
          <span className="text-xs text-gray-400">
            {formatTime(message.timestamp)}
          </span>
        </div>
        <div className="text-sm text-gray-700 whitespace-pre-wrap">
          {message.content}
        </div>

        {/* Metadata */}
        {message.metadata && !isUser && (
          <div className="flex gap-2 mt-2">
            {message.metadata.queryType && (
              <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-tableau-blue/10 text-tableau-blue">
                {message.metadata.queryType}
              </span>
            )}
            {message.metadata.iterations && message.metadata.iterations > 1 && (
              <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-600">
                {message.metadata.iterations} iterations
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
