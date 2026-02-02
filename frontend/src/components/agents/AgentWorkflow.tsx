'use client';

import { CheckCircle2, Circle, Loader2, XCircle } from 'lucide-react';
import { cn, formatAgentName } from '@/lib/utils';
import { useChatStore } from '@/stores/chatStore';
import type { AgentStatus, WorkflowStep } from '@/types';

function StatusIcon({ status }: { status: AgentStatus }) {
  switch (status) {
    case 'running':
      return <Loader2 className="h-5 w-5 text-tableau-blue animate-spin" />;
    case 'completed':
      return <CheckCircle2 className="h-5 w-5 text-tableau-green" />;
    case 'error':
      return <XCircle className="h-5 w-5 text-tableau-red" />;
    default:
      return <Circle className="h-5 w-5 text-gray-300" />;
  }
}

function WorkflowStepItem({
  step,
  isLast,
}: {
  step: WorkflowStep;
  isLast: boolean;
}) {
  return (
    <div className="flex items-start">
      <div className="flex flex-col items-center">
        <StatusIcon status={step.status} />
        {!isLast && (
          <div
            className={cn(
              'w-0.5 h-8 my-1',
              step.status === 'completed' ? 'bg-tableau-green' : 'bg-gray-200'
            )}
          />
        )}
      </div>
      <div className="ml-3 min-w-0 flex-1">
        <p
          className={cn(
            'text-sm font-medium',
            step.status === 'running' && 'text-tableau-blue',
            step.status === 'completed' && 'text-gray-900',
            step.status === 'error' && 'text-tableau-red',
            step.status === 'idle' && 'text-gray-400'
          )}
        >
          {formatAgentName(step.agent)}
        </p>
        {step.details && (
          <p className="text-xs text-gray-500 mt-0.5">{step.details}</p>
        )}
      </div>
    </div>
  );
}

export function AgentWorkflow() {
  const { workflowSteps, isLoading } = useChatStore();

  // Only show if there's activity
  const hasActivity = workflowSteps.some((step) => step.status !== 'idle');

  if (!hasActivity && !isLoading) {
    return null;
  }

  return (
    <div className="bg-gray-50 rounded-lg p-4">
      <h3 className="text-sm font-semibold text-gray-700 mb-3">
        Agent Workflow
      </h3>
      <div className="space-y-0">
        {workflowSteps.map((step, index) => (
          <WorkflowStepItem
            key={step.agent}
            step={step}
            isLast={index === workflowSteps.length - 1}
          />
        ))}
      </div>
    </div>
  );
}
