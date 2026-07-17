'use client';

import { useState } from 'react';
import { Eye, EyeOff, Layers } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Slider } from '@/components/ui/slider';

interface SegmentationOverlayProps {
  originalImage: string;
  segmentationMask: string;
  className?: string;
}

export function SegmentationOverlay({
  originalImage,
  segmentationMask,
  className,
}: SegmentationOverlayProps) {
  const [showMask, setShowMask] = useState(true);
  const [maskOpacity, setMaskOpacity] = useState([0.5]);

  return (
    <div className={cn('space-y-4', className)}>
      <div className="relative aspect-square overflow-hidden rounded-xl border border-border bg-card shadow-sm">
        {/* Original Image */}
        <img
          src={originalImage}
          alt="Original skin image"
          className="absolute inset-0 h-full w-full object-cover"
        />

        {/* Segmentation Mask Overlay */}
        {showMask && (
          <div
            className="absolute inset-0"
            style={{ opacity: maskOpacity[0] }}
          >
            {/* In production, this would be the actual segmentation mask */}
            {/* For demo, we'll show a semi-transparent colored overlay */}
            <div className="absolute inset-0 bg-gradient-to-br from-primary/40 via-transparent to-accent/30" />
            <img
              src={segmentationMask}
              alt="Segmentation mask"
              className="h-full w-full object-cover mix-blend-multiply"
              style={{ filter: 'hue-rotate(180deg) saturate(2)' }}
            />
          </div>
        )}

        {/* Mask Toggle Button */}
        <div className="absolute right-3 top-3">
          <Button
            variant={showMask ? 'default' : 'secondary'}
            size="sm"
            className="gap-2 shadow-lg"
            onClick={() => setShowMask(!showMask)}
          >
            {showMask ? (
              <>
                <Eye className="h-4 w-4" />
                Mask On
              </>
            ) : (
              <>
                <EyeOff className="h-4 w-4" />
                Mask Off
              </>
            )}
          </Button>
        </div>

        {/* Legend */}
        <div className="absolute bottom-3 left-3 rounded-lg bg-card/90 p-2 shadow-lg backdrop-blur-sm">
          <div className="flex items-center gap-2 text-xs">
            <Layers className="h-3 w-3 text-primary" />
            <span className="font-medium text-foreground">Segmentation View</span>
          </div>
        </div>
      </div>

      {/* Opacity Slider */}
      {showMask && (
        <div className="flex items-center gap-4 rounded-lg bg-muted/50 p-3">
          <span className="text-sm font-medium text-foreground">Mask Opacity</span>
          <Slider
            value={maskOpacity}
            onValueChange={setMaskOpacity}
            min={0}
            max={1}
            step={0.1}
            className="flex-1"
          />
          <span className="w-12 text-right text-sm text-muted-foreground">
            {Math.round(maskOpacity[0] * 100)}%
          </span>
        </div>
      )}
    </div>
  );
}
