'use client';

import { AlertTriangle, CheckCircle, Info, TrendingUp } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';

interface ResultCardProps {
  predictedDisease: string;
  confidence: number;
  basicInfo: string;
  className?: string;
}

export function ResultCard({
  predictedDisease,
  confidence,
  basicInfo,
  className,
}: ResultCardProps) {
  const confidencePercent = Math.round(confidence * 100);

  const getConfidenceLevel = (conf: number) => {
    if (conf >= 0.8) return { label: 'High', color: 'text-success', bgColor: 'bg-success' };
    if (conf >= 0.6) return { label: 'Moderate', color: 'text-warning', bgColor: 'bg-warning' };
    return { label: 'Low', color: 'text-destructive', bgColor: 'bg-destructive' };
  };

  const confidenceLevel = getConfidenceLevel(confidence);

  return (
    <div className={cn('space-y-4', className)}>
      {/* Diagnosis Result Card */}
      <Card className="border-border bg-card shadow-sm">
        <CardHeader className="pb-3">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/10">
              <CheckCircle className="h-4 w-4 text-primary" />
            </div>
            <CardTitle className="text-lg">Diagnosis Result</CardTitle>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Predicted Disease */}
          <div className="rounded-lg bg-primary/5 p-4">
            <p className="text-sm text-muted-foreground">Predicted Condition</p>
            <p className="mt-1 text-2xl font-bold text-primary">{predictedDisease}</p>
          </div>

          {/* Confidence Score */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <TrendingUp className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm font-medium text-foreground">Confidence Score</span>
              </div>
              <div className="flex items-center gap-2">
                <span className={cn('text-sm font-medium', confidenceLevel.color)}>
                  {confidenceLevel.label}
                </span>
                <span className="text-lg font-bold text-foreground">{confidencePercent}%</span>
              </div>
            </div>
            <Progress value={confidencePercent} className="h-2" />
          </div>

          {/* Confidence Warning for Low Scores */}
          {confidence < 0.6 && (
            <div className="flex items-start gap-2 rounded-lg bg-warning/10 p-3 text-sm">
              <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0 text-warning" />
              <p className="text-warning-foreground">
                The confidence score is relatively low. Consider consulting a healthcare professional
                for accurate diagnosis.
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Basic Information Card */}
      <Card className="border-border bg-card shadow-sm">
        <CardHeader className="pb-3">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-accent/10">
              <Info className="h-4 w-4 text-accent" />
            </div>
            <CardTitle className="text-lg">Basic Information</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <p className="leading-relaxed text-muted-foreground">{basicInfo}</p>
        </CardContent>
      </Card>
    </div>
  );
}
