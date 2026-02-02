'use client';

import { forwardRef, type InputHTMLAttributes } from 'react';
import { cn } from '@/lib/utils';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  error?: boolean;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, error, ...props }, ref) => {
    return (
      <input
        ref={ref}
        className={cn(
          'w-full px-4 py-2 text-sm border rounded-lg transition-colors',
          'focus:outline-none focus:ring-2 focus:ring-offset-0',
          'placeholder:text-gray-400',
          error
            ? 'border-red-500 focus:ring-red-500'
            : 'border-gray-300 focus:ring-tableau-blue focus:border-tableau-blue',
          'disabled:bg-gray-50 disabled:text-gray-500',
          className
        )}
        {...props}
      />
    );
  }
);

Input.displayName = 'Input';
