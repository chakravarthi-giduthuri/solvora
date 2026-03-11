'use client';

import { useState } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { format, parseISO, subDays } from 'date-fns';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import type { VolumeDataPoint } from '@/types';

type Range = '7d' | '30d' | '90d';

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{ name: string; value: number; color: string }>;
  label?: string;
}

function CustomTooltip({ active, payload, label }: CustomTooltipProps) {
  if (!active || !payload || !label) return null;
  return (
    <div className="rounded-lg border bg-background p-3 shadow-md text-sm">
      <p className="font-semibold mb-2">{label}</p>
      {payload.map((entry) => (
        <p key={entry.name} className="flex items-center gap-2">
          <span
            className="inline-block h-2.5 w-2.5 rounded-full"
            style={{ backgroundColor: entry.color }}
          />
          <span className="capitalize text-muted-foreground">{entry.name}:</span>
          <span className="font-medium">{entry.value.toLocaleString()}</span>
        </p>
      ))}
    </div>
  );
}

interface VolumeLineChartProps {
  data: VolumeDataPoint[];
}

export function VolumeLineChart({ data }: VolumeLineChartProps) {
  const [range, setRange] = useState<Range>('30d');

  const rangeDays = range === '7d' ? 7 : range === '30d' ? 30 : 90;
  const cutoff = subDays(new Date(), rangeDays);

  const filteredData = data
    .filter((d) => {
      try {
        return parseISO(d.date) >= cutoff;
      } catch {
        return true;
      }
    })
    .map((d) => ({
      ...d,
      formattedDate: (() => {
        try {
          return format(parseISO(d.date), range === '7d' ? 'EEE' : 'MMM d');
        } catch {
          return d.date;
        }
      })(),
    }));

  return (
    <div>
      <div className="flex justify-end mb-3">
        <Tabs
          value={range}
          onValueChange={(v) => setRange(v as Range)}
        >
          <TabsList className="h-8">
            <TabsTrigger value="7d" className="text-xs px-2">7d</TabsTrigger>
            <TabsTrigger value="30d" className="text-xs px-2">30d</TabsTrigger>
            <TabsTrigger value="90d" className="text-xs px-2">90d</TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      <ResponsiveContainer width="100%" height={280}>
        <LineChart
          data={filteredData}
          margin={{ top: 5, right: 10, left: 0, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
          <XAxis
            dataKey="formattedDate"
            tick={{ fontSize: 11 }}
            className="fill-muted-foreground"
            interval="preserveStartEnd"
          />
          <YAxis
            tick={{ fontSize: 11 }}
            className="fill-muted-foreground"
            width={40}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend
            formatter={(value) =>
              value.charAt(0).toUpperCase() + value.slice(1)
            }
          />
          <Line
            type="monotone"
            dataKey="reddit"
            stroke="#FF4500"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4 }}
          />
          <Line
            type="monotone"
            dataKey="hackernews"
            stroke="#14b8a6"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
