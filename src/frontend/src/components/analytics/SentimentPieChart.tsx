'use client';

import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import type { SentimentDistribution } from '@/types';

const SENTIMENT_CONFIG = [
  { key: 'urgent', label: 'Urgent', color: '#EF4444' },
  { key: 'frustrated', label: 'Frustrated', color: '#F97316' },
  { key: 'curious', label: 'Curious', color: '#3B82F6' },
  { key: 'neutral', label: 'Neutral', color: '#6B7280' },
] as const;

interface CustomLabelProps {
  cx: number;
  cy: number;
  midAngle: number;
  innerRadius: number;
  outerRadius: number;
  percent: number;
}

function CustomLabel({
  cx,
  cy,
  midAngle,
  innerRadius,
  outerRadius,
  percent,
}: CustomLabelProps) {
  if (percent < 0.05) return null;
  const RADIAN = Math.PI / 180;
  const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
  const x = cx + radius * Math.cos(-midAngle * RADIAN);
  const y = cy + radius * Math.sin(-midAngle * RADIAN);

  return (
    <text
      x={x}
      y={y}
      fill="white"
      textAnchor="middle"
      dominantBaseline="central"
      fontSize={12}
      fontWeight="600"
    >
      {`${(percent * 100).toFixed(0)}%`}
    </text>
  );
}

interface TooltipProps {
  active?: boolean;
  payload?: Array<{ name: string; value: number; payload: { percent: number } }>;
}

function CustomTooltip({ active, payload }: TooltipProps) {
  if (!active || !payload || payload.length === 0) return null;
  const entry = payload[0];
  return (
    <div className="rounded-lg border bg-background p-3 shadow-md text-sm">
      <p className="font-semibold">{entry.name}</p>
      <p className="text-muted-foreground">
        Count: <span className="text-foreground font-medium">{entry.value.toLocaleString()}</span>
      </p>
    </div>
  );
}

interface SentimentPieChartProps {
  data: SentimentDistribution;
}

export function SentimentPieChart({ data }: SentimentPieChartProps) {
  const chartData = SENTIMENT_CONFIG.map(({ key, label, color }) => ({
    name: label,
    value: data[key],
    color,
  })).filter((d) => d.value > 0);

  const total = chartData.reduce((sum, d) => sum + d.value, 0);

  return (
    <div>
      <ResponsiveContainer width="100%" height={280}>
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            outerRadius={100}
            dataKey="value"
            labelLine={false}
            label={(props) => (
              <CustomLabel
                {...props}
                percent={props.value / total}
              />
            )}
          >
            {chartData.map((entry, index) => (
              <Cell key={index} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip content={<CustomTooltip />} />
          <Legend
            formatter={(value) => (
              <span className="text-sm text-foreground">{value}</span>
            )}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
