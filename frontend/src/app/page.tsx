'use client';

import { ChatContainer } from '@/components/chat/ChatContainer';
import { BarChart3, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { useChatStore } from '@/stores/chatStore';

export default function Home() {
  const { clearConversation, messages } = useChatStore();

  return (
    <main className="h-screen flex flex-col bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between max-w-7xl mx-auto">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-tableau-blue flex items-center justify-center">
              <BarChart3 className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-lg font-semibold text-gray-900">
                Tableau Analytics Agent
              </h1>
              <p className="text-sm text-gray-500">
                Powered by Gemini 1.5 Pro
              </p>
            </div>
          </div>
          {messages.length > 0 && (
            <Button
              variant="ghost"
              size="sm"
              onClick={clearConversation}
              className="text-gray-500"
            >
              <RefreshCw className="w-4 h-4 mr-2" />
              New Chat
            </Button>
          )}
        </div>
      </header>

      {/* Chat area */}
      <div className="flex-1 overflow-hidden">
        <div className="h-full max-w-7xl mx-auto bg-white border-x border-gray-200">
          <ChatContainer />
        </div>
      </div>
    </main>
  );
}
