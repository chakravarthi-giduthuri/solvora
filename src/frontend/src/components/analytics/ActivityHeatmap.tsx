'use client';

import { cn } from '@/lib/utils';
import type { ActivityHeatmapCell } from '@/types';

const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const HOURS = Array.from({ length: 24 }, (_, i) => {
  if (i === 0) return '12a';
  if (i < 12) return `${i}a`;
  if (i === 12) return '12p';
  return `${i - 12}p`;
});

function getIntensityClass(value: number, max: number): string {
  if (max === 0 || value === 0)
    return 'bg-muted';
  const ratio = value / max;
  if (ratio < 0.2) return 'bg-primary/20';
  if (ratio < 0.4) return 'bg-primary/40';
  if (ratio < 0.6) return 'bg-primary/60';
  if (ratio < 0.8) return 'bg-primary/80';
  return 'bg-primary';
}

interface ActivityHeatmapProps {
  data: ActivityHeatmapCell[];
}

export function ActivityHeatmap({ data }: ActivityHeatmapProps) {
  // Build a 7x24 lookup
  const cellMap = new Map<string, number>();
  data.forEach(({ day, hour, count }) => {
    cellMap.set(`${day}-${hour}`, count);
  });

  const maxCount = Math.max(...data.map((d) => d.count), 1);

  return (
    <div className="overflow-x-auto">
      <div className="min-w-[600px]">
        {/* Hour labels */}
        <div className="flex mb-1 ml-10">
          {HOURS.filter((_, i) => i % 3 === 0).map((label, i) => (
            <div
              key={i}
              className="flex-1 text-xs text-muted-foreground text-center"
              style={{ minWidth: 0 }}
            >
              {label}
            </div>
          ))}
        </div>

        {/* Grid rows */}
        <div className="space-y-1">
          {DAYS.map((dayLabel, day) => (
            <div key={day} className="flex items-center gap-1">
              {/* Day label */}
              <span className="text-xs text-muted-foreground w-9 shrink-0 text-right pr-2">
                {dayLabel}
              </span>

              {/* Hour cells */}
              <div className="flex flex-1 gap-0.5">
                {HOURS.map((_, hour) => {
                  const count = cellMap.get(`${day}-${hour}`) ?? 0;
                  return (
                    <div
                      key={hour}
                      title={`${dayLabel} ${HOURS[hour]}: ${count} problems`}
                      aria-label={`${dayLabel} ${HOURS[hour]}: ${count} problems`}
                      className={cn(
                        'flex-1 rounded-sm aspect-square transition-colors',
                        getIntensityClass(count, maxCount),
                      )}
                      role="cell"
                    />
                  );
                })}
              </div>
            </div>
          ))}
        </div>

        {/* Legend */}
        <div className="flex items-center gap-2 mt-3 justify-end">
          <span className="text-xs text-muted-foreground">Less</span>
          {[0, 0.2, 0.4, 0.6, 0.8, 1].map((ratio, i) => (
            <div
              key={i}
              className={cn(
                'h-3 w-3 rounded-sm',
                ratio === 0 ? 'bg-muted' :
                ratio < 0.2 ? 'bg-primary/20' :
                ratio < 0.4 ? 'bg-primary/40' :
                ratio < 0.6 ? 'bg-primary/60' :
                ratio < 0.8 ? 'bg-primary/80' :
                'bg-primary',
              )}
            />
          ))}
          <span className="text-xs text-muted-foreground">More</span>
        </div>
      </div>
    </div>
  );
}
