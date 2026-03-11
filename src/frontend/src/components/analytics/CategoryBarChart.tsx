'use client';

import { useState } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import { Table2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import type { CategoryCount } from '@/types';

const COLORS = [
  '#6366f1', '#8b5cf6', '#ec4899', '#f97316',
  '#eab308', '#22c55e', '#14b8a6', '#3b82f6',
  '#f43f5e', '#a855f7',
];

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{ value: number; payload: CategoryCount }>;
  label?: string;
}

function CustomTooltip({ active, payload, label }: CustomTooltipProps) {
  if (!active || !payload || payload.length === 0) return null;
  const data = payload[0];
  return (
    <div className="rounded-lg border bg-background p-3 shadow-md text-sm">
      <p className="font-semibold mb-1">{label}</p>
      <p className="text-muted-foreground">
        Problems: <span className="text-foreground font-medium">{data.value.toLocaleString()}</span>
      </p>
      <p className="text-muted-foreground">
        Share:{' '}
        <span className="text-foreground font-medium">
          {data.payload.percentage.toFixed(1)}%
        </span>
      </p>
    </div>
  );
}

interface CategoryBarChartProps {
  data: CategoryCount[];
}

export function CategoryBarChart({ data }: CategoryBarChartProps) {
  const [showTable, setShowTable] = useState(false);

  return (
    <div>
      <div className="flex justify-end mb-2">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setShowTable((v) => !v)}
          aria-expanded={showTable}
          aria-controls="category-table"
          className="gap-1.5 text-xs"
        >
          <Table2 className="h-3.5 w-3.5" />
          {showTable ? 'Show chart' : 'Show table'}
        </Button>
      </div>

      {showTable ? (
        <div id="category-table">
          <table className="w-full text-sm" aria-label="Problems by category">
            <thead>
              <tr className="border-b">
                <th className="text-left py-2 font-semibold">Category</th>
                <th className="text-right py-2 font-semibold">Count</th>
                <th className="text-right py-2 font-semibold">Share</th>
              </tr>
            </thead>
            <tbody>
              {data.map((item) => (
                <tr key={item.category} className="border-b last:border-0">
                  <td className="py-2">{item.category}</td>
                  <td className="py-2 text-right tabular-nums">
                    {item.count.toLocaleString()}
                  </td>
                  <td className="py-2 text-right tabular-nums text-muted-foreground">
                    {item.percentage.toFixed(1)}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={300}>
          <BarChart
            data={data}
            margin={{ top: 5, right: 10, left: 0, bottom: 60 }}
          >
            <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
            <XAxis
              dataKey="category"
              tick={{ fontSize: 11 }}
              angle={-35}
              textAnchor="end"
              interval={0}
              className="fill-muted-foreground"
            />
            <YAxis
              tick={{ fontSize: 11 }}
              className="fill-muted-foreground"
              width={40}
            />
            <Tooltip content={<CustomTooltip />} />
            <Bar dataKey="count" radius={[4, 4, 0, 0]}>
              {data.map((_, index) => (
                <Cell
                  key={index}
                  fill={COLORS[index % COLORS.length]}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
