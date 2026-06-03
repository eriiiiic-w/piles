import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

interface LayerChartProps {
  layers: string[];
  predictedTops: number[];
  predictedBottoms: number[];
  measuredTops?: (number | null)[];
}

const LayerChart: React.FC<LayerChartProps> = ({ layers, predictedTops, predictedBottoms, measuredTops }) => {
  const data = layers.map((name, i) => ({
    name,
    '预测顶标高': parseFloat(predictedTops[i]?.toFixed(2)),
    '预测底标高': parseFloat(predictedBottoms[i]?.toFixed(2)),
    ...(measuredTops && measuredTops[i] != null ? { '实测顶标高': parseFloat(measuredTops[i]!.toFixed(2)) } : {}),
  }));

  return (
    <ResponsiveContainer width="100%" height={400}>
      <BarChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="name" angle={-30} textAnchor="end" height={80} fontSize={11} />
        <YAxis label={{ value: '标高(m)', angle: -90, position: 'insideLeft' }} />
        <Tooltip />
        <Legend />
        <Bar dataKey="预测顶标高" fill="#3498db" />
        <Bar dataKey="预测底标高" fill="#2980b9" />
        {measuredTops && <Bar dataKey="实测顶标高" fill="#e74c3c" />}
      </BarChart>
    </ResponsiveContainer>
  );
};

export default LayerChart;
