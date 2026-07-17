'use client';

import * as React from 'react';
import { format } from 'date-fns';
import { vi } from 'date-fns/locale';
import { CalendarIcon } from 'lucide-react';

import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Calendar } from '@/components/ui/calendar';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';

interface DatePickerProps {
  value?: Date;
  onChange?: (date: Date | undefined) => void;
  placeholder?: string;
  disabled?: boolean;
  maxDate?: Date;
  minDate?: Date;
  className?: string;
}

export function DatePicker({
  value,
  onChange,
  placeholder = 'Chọn ngày',
  disabled = false,
  maxDate,
  minDate,
  className,
}: DatePickerProps) {
  const [open, setOpen] = React.useState(false);

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          disabled={disabled}
          className={cn(
            'w-full justify-between text-left font-normal h-auto py-3 px-4 rounded-xl bg-secondary border-border hover:bg-secondary/80',
            !value && 'text-muted-foreground',
            className,
          )}
        >
          {value ? (
            format(value, 'dd/MM/yyyy', { locale: vi })
          ) : (
            <span>{placeholder}</span>
          )}
          <CalendarIcon className="h-4 w-4 shrink-0 opacity-60" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[var(--radix-popover-trigger-width)] min-w-[280px] p-0" align="start" side="bottom">
        <Calendar
          mode="single"
          selected={value}
          onSelect={(date) => {
            onChange?.(date);
            setOpen(false);
          }}
          disabled={(date) => {
            if (maxDate && date > maxDate) return true;
            if (minDate && date < minDate) return true;
            return false;
          }}
          captionLayout="dropdown"
          defaultMonth={value || new Date(2000, 0)}
          fromYear={1920}
          toYear={new Date().getFullYear()}
          locale={vi}
          initialFocus
        />
      </PopoverContent>
    </Popover>
  );
}
