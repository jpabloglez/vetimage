import React from 'react';
import { LucideIcon } from 'lucide-react';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  leftIcon?: LucideIcon;
  rightIcon?: LucideIcon;
  helper?: string;
  required?: boolean;
}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  (
    {
      label,
      error,
      leftIcon: LeftIcon,
      rightIcon: RightIcon,
      helper,
      required,
      className = '',
      id,
      ...props
    },
    ref
  ) => {
    const inputId = id || `input-${Math.random().toString(36).substr(2, 9)}`;

    const baseInputClasses = [
      'medical-input',
      'transition-all duration-200',
    ];

    const iconInputClasses = [
      LeftIcon && 'pl-10',
      RightIcon && 'pr-10',
    ].filter(Boolean);

    const errorClasses = error
      ? [
          'border-error-500 focus:border-error-500 focus:ring-error-500',
          'dark:border-error-400 dark:focus:border-error-400 dark:focus:ring-error-400',
        ]
      : [];

    const inputClasses = [
      ...baseInputClasses,
      ...iconInputClasses,
      ...errorClasses,
      className,
    ].join(' ');

    return (
      <div className="w-full">
        {label && (
          <label
            htmlFor={inputId}
            className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2"
          >
            {label}
            {required && <span className="text-error-500 ml-1">*</span>}
          </label>
        )}

        <div className="relative">
          {LeftIcon && (
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <LeftIcon className="h-5 w-5 text-slate-400 dark:text-slate-500" />
            </div>
          )}

          <input
            ref={ref}
            id={inputId}
            className={inputClasses}
            {...props}
          />

          {RightIcon && (
            <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
              <RightIcon className="h-5 w-5 text-slate-400 dark:text-slate-500" />
            </div>
          )}
        </div>

        {(error || helper) && (
          <div className="mt-2">
            {error ? (
              <p className="text-sm text-error-600 dark:text-error-400">
                {error}
              </p>
            ) : helper ? (
              <p className="text-sm text-slate-500 dark:text-slate-400">
                {helper}
              </p>
            ) : null}
          </div>
        )}
      </div>
    );
  }
);

Input.displayName = 'Input';

export default Input;