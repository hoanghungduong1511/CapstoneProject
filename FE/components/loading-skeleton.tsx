import { cn } from '@/lib/utils';

interface LoadingSkeletonProps {
  className?: string;
}

export function LoadingSkeleton({ className }: LoadingSkeletonProps) {
  return (
    <div
      className={cn(
        'animate-pulse rounded-lg bg-muted',
        className
      )}
    />
  );
}

export function CardSkeleton() {
  return (
    <div className="rounded-xl border border-border bg-card p-6 shadow-sm">
      <LoadingSkeleton className="mb-4 h-6 w-1/3" />
      <LoadingSkeleton className="mb-2 h-4 w-full" />
      <LoadingSkeleton className="mb-2 h-4 w-5/6" />
      <LoadingSkeleton className="h-4 w-4/6" />
    </div>
  );
}

export function ImageSkeleton() {
  return (
    <div className="aspect-square w-full overflow-hidden rounded-xl border border-border bg-card">
      <LoadingSkeleton className="h-full w-full" />
    </div>
  );
}

export function ChatMessageSkeleton() {
  return (
    <div className="flex gap-3 p-4">
      <LoadingSkeleton className="h-8 w-8 flex-shrink-0 rounded-full" />
      <div className="flex-1 space-y-2">
        <LoadingSkeleton className="h-4 w-1/4" />
        <LoadingSkeleton className="h-4 w-full" />
        <LoadingSkeleton className="h-4 w-5/6" />
      </div>
    </div>
  );
}

export function AnalyzingLoader() {
  return (
    <div className="flex flex-col items-center justify-center py-12">
      <div className="relative h-24 w-24">
        {/* Outer ring */}
        <div className="absolute inset-0 animate-spin rounded-full border-4 border-primary/20 border-t-primary" />
        {/* Inner ring */}
        <div
          className="absolute inset-3 animate-spin rounded-full border-4 border-accent/20 border-t-accent"
          style={{ animationDirection: 'reverse', animationDuration: '1.5s' }}
        />
        {/* Center dot */}
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="h-4 w-4 animate-pulse rounded-full bg-primary" />
        </div>
      </div>
      <p className="mt-6 text-lg font-medium text-foreground">Analyzing your image...</p>
      <p className="mt-2 text-sm text-muted-foreground">
        Our AI is processing the skin image
      </p>
    </div>
  );
}
