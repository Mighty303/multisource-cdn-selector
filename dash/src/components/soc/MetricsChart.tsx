import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';

interface MetricsLineChartProps {
  data: Record<string, unknown>[];
  lines: { key: string; color: string }[];
  yLabel?: string;
}

export function MetricsLineChart({ data, lines, yLabel }: MetricsLineChartProps) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={data} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="hsl(150, 20%, 15%)" />
        <XAxis dataKey="time" tick={{ fontSize: 9, fill: 'hsl(150, 5%, 50%)', fontFamily: 'JetBrains Mono' }} />
        <YAxis tick={{ fontSize: 9, fill: 'hsl(150, 5%, 50%)', fontFamily: 'JetBrains Mono' }} label={yLabel ? { value: yLabel, angle: -90, position: 'insideLeft', style: { fontSize: 9, fill: 'hsl(150, 5%, 50%)' } } : undefined} />
        <Tooltip
          contentStyle={{ backgroundColor: 'hsl(150, 15%, 7%)', border: '1px solid hsl(150, 20%, 15%)', borderRadius: 4, fontSize: 10, fontFamily: 'JetBrains Mono' }}
          labelStyle={{ color: 'hsl(153, 100%, 50%)' }}
        />
        <Legend wrapperStyle={{ fontSize: 10, fontFamily: 'JetBrains Mono' }} />
        {lines.map(l => (
          <Line key={l.key} type="monotone" dataKey={l.key} stroke={l.color} strokeWidth={1.5} dot={false} />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}

interface MetricsBarChartProps {
  data: Record<string, unknown>[];
  bars: { key: string; color: string }[];
}

export function MetricsBarChart({ data, bars }: MetricsBarChartProps) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={data} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="hsl(150, 20%, 15%)" />
        <XAxis dataKey="name" tick={{ fontSize: 9, fill: 'hsl(150, 5%, 50%)', fontFamily: 'JetBrains Mono' }} />
        <YAxis tick={{ fontSize: 9, fill: 'hsl(150, 5%, 50%)', fontFamily: 'JetBrains Mono' }} />
        <Tooltip
          contentStyle={{ backgroundColor: 'hsl(150, 15%, 7%)', border: '1px solid hsl(150, 20%, 15%)', borderRadius: 4, fontSize: 10, fontFamily: 'JetBrains Mono' }}
        />
        {bars.map(b => (
          <Bar key={b.key} dataKey={b.key} fill={b.color} radius={[2, 2, 0, 0]} />
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
}
