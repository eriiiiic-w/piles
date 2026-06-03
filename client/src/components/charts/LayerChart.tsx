import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell } from 'recharts';

interface LayerChartProps {
  layers: string[];
  predictedTops: number[];
  predictedBottoms: number[];
  measuredTops?: (number | null)[];
  pileTop?: number;
  pileBottom?: number;
}

const LayerChart: React.FC<LayerChartProps> = ({
  layers, predictedTops, predictedBottoms, measuredTops,
  pileTop, pileBottom
}) => {
  const data = layers.map((name, i) => {
    const top = parseFloat(predictedTops[i]?.toFixed(2)) || 0;
    const bottom = parseFloat(predictedBottoms[i]?.toFixed(2)) || 0;
    const height = parseFloat((top - bottom).toFixed(2));
    const meas = measuredTops && measuredTops[i] != null
      ? parseFloat(measuredTops[i]!.toFixed(2)) : null;
    const measHeight = meas != null ? parseFloat((meas - bottom).toFixed(2)) : null;

    return {
      name,
      '底基(隐)': bottom,
      '预测厚度': Math.max(height, 0.01),
      '实测底基(隐)': meas != null ? bottom : 0,
      '实测厚度': measHeight != null ? Math.max(measHeight, 0.01) : 0,
    };
  });

  if (pileTop != null && pileBottom != null && pileTop > pileBottom) {
    const pileHeight = parseFloat((pileTop - pileBottom).toFixed(2));
    data.push({
      name: '桩体',
      '底基(隐)': pileBottom,
      '预测厚度': Math.max(pileHeight, 0.01),
      '实测底基(隐)': 0,
      '实测厚度': 0,
    } as any);
  }

  const isPileEntry = (entry: any) => entry.name === '桩体';

  return (
    <ResponsiveContainer width="100%" height={550}>
      <BarChart data={data} margin={{ top: 30, right: 30, left: 20, bottom: 5 }}
        barCategoryGap={3} barGap={2}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="name" angle={-30} textAnchor="end" height={80} fontSize={11} />
        <YAxis label={{ value: '标高(m)', angle: -90, position: 'insideLeft' }} />
        <Tooltip
          formatter={(value: any, name: any, _props: any) => {
            if (name === '底基(隐)' || name === '实测底基(隐)') return null;
            return [value, name === '预测厚度' ? '预测土层' : name === '实测厚度' ? '实测土层' : name];
          }}
        />
        <Legend />
        {/* 预测土层 */}
        <Bar dataKey="底基(隐)" stackId="pred" fill="transparent" name=" " />
        <Bar dataKey="预测厚度" stackId="pred" name="预测土层"
          label={({ x, y, width, value, index }: any) => {
            if (!value || value <= 0.01) return null;
            const entry = data[index ?? 0];
            if (!entry || isPileEntry(entry)) return null;
            const base = entry['底基(隐)'] || 0;
            const top = base + (typeof value === 'number' ? value : 0);
            // 靠近图表顶部的柱体，标签放在柱内避免被裁切
            const labelY = y < 18 ? y + 14 : y - 4;
            return (
              <text x={x + width / 2} y={labelY} textAnchor="middle" fontSize={10} fill="#2980b9" fontWeight={600}>
                {top.toFixed(2)}
              </text>
            );
          }}
        >
          {data.map((entry, i) =>
            isPileEntry(entry) ? <Cell key={i} fill="#e67e22" /> : <Cell key={i} fill="#3498db" />
          )}
        </Bar>
        {/* 实测土层 */}
        <Bar dataKey="实测底基(隐)" stackId="meas" fill="transparent" name="  " />
        <Bar dataKey="实测厚度" stackId="meas" fill="#e74c3c" name="实测土层"
          label={({ x, y, width, value, index }: any) => {
            if (!value || value <= 0.01) return null;
            const entry = data[index ?? 0];
            if (!entry || isPileEntry(entry)) return null;
            const base = entry['实测底基(隐)'] || 0;
            const top = base + (typeof value === 'number' ? value : 0);
            const labelY = y < 18 ? y + 14 : y - 4;
            return (
              <text x={x + width / 2} y={labelY} textAnchor="middle" fontSize={10} fill="#c0392b" fontWeight={600}>
                {top.toFixed(2)}
              </text>
            );
          }}
        />
      </BarChart>
    </ResponsiveContainer>
  );
};

export default LayerChart;
