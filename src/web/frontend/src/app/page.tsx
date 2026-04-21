"use client";

import React, { useState, useEffect, useCallback, startTransition } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer
} from 'recharts';
import {
  Thermometer,
  DollarSign,
  Activity,
  Power,
  Zap,
  Brain,
  Cpu,
} from 'lucide-react';

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL ?? 'http://localhost:8010';

interface TelemetryRecord {
  time: string;
  indoor_temp: number | null;
  heating_setpoint: number | null;
  cooling_setpoint: number | null;
  latency_ms: number | null;
}

interface SavingsSummary {
  baseline_kwh: number;
  ai_kwh: number;
  kwh_saved: number;
  cad_saved: number;
}

interface EnergyProjection {
  projected_kwh: number;
}

export default function Dashboard() {
  const [telemetryHistory, setTelemetryHistory] = useState<TelemetryRecord[]>([]);
  const [savings, setSavings] = useState<SavingsSummary | null>(null);
  const [projectedEnergy, setProjectedEnergy] = useState<number | null>(null);
  const [isAIActive, setIsAIActive] = useState<boolean>(true);
  const [overrideLoading, setOverrideLoading] = useState<boolean>(false);
  const [mounted, setMounted] = useState(false);
  const [aiReasoning, setAiReasoning] = useState<string>("Waiting for AI insights...");
  const [edgeConnected, setEdgeConnected] = useState<boolean>(false);

  const [manualIndoor, setManualIndoor] = useState<number>(21.5);
  const [manualOutdoor, setManualOutdoor] = useState<number>(15.0);

  // Sync initial state from backend on mount
  useEffect(() => {
    setMounted(true);
    const fetchInitialState = async () => {
      try {
        const [envRes, overrideRes] = await Promise.all([
          fetch(`${BACKEND}/api/environment`),
          fetch(`${BACKEND}/api/override`),
        ]);
        if (envRes.ok) {
          const envData = await envRes.json();
          setManualIndoor(envData.indoor_temp);
          setManualOutdoor(envData.outdoor_temp);
          if (envData.recommendation_reason) {
            setAiReasoning(envData.recommendation_reason);
          }
        }
        if (overrideRes.ok) {
          const ovData = await overrideRes.json();
          setIsAIActive(!ovData.override_active);
        }
      } catch (error) {
        console.error('Initial state fetch error:', error);
      }
    };
    fetchInitialState();
  }, []);

  // Polling loop -- runs every 2 seconds after mount
  useEffect(() => {
    if (!mounted) return;
    const fetchData = async () => {
      try {
        const [telemetryRes, savingsRes, energyRes, envRes] = await Promise.all([
          fetch(`${BACKEND}/api/telemetry/latest`),
          fetch(`${BACKEND}/api/savings_summary`),
          fetch(`${BACKEND}/api/energy/project`),
          fetch(`${BACKEND}/api/environment`),
        ]);

        // Batch all state updates into one render pass using startTransition
        startTransition(() => {
          if (telemetryRes.ok) {
            telemetryRes.json().then((telemetryData: TelemetryRecord[]) => {
              setTelemetryHistory(telemetryData.slice(-30));

              // Heartbeat: check if latest record is less than 10 seconds old
              if (telemetryData.length > 0) {
                const latest = telemetryData[telemetryData.length - 1];
                if (latest.time) {
                  const age = Date.now() - new Date(latest.time).getTime();
                  setEdgeConnected(age < 10_000);
                }
              } else {
                setEdgeConnected(false);
              }
            });
          }
          if (savingsRes.ok) {
            savingsRes.json().then(setSavings);
          }
          if (energyRes.ok) {
            energyRes.json().then((energyData: EnergyProjection) => {
              setProjectedEnergy(energyData.projected_kwh);
            });
          }
          if (envRes.ok) {
            envRes.json().then((envData: { recommendation_reason?: string }) => {
              if (envData.recommendation_reason) {
                setAiReasoning(envData.recommendation_reason);
              }
            });
          }
        });
      } catch (error) {
        console.error('Data polling error:', error);
        startTransition(() => setEdgeConnected(false));
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 2000);
    return () => clearInterval(interval);
  }, [mounted]);

  const handleEnvironmentChange = useCallback(
    async (type: 'indoor' | 'outdoor', value: number) => {
      let newIndoor = manualIndoor;
      let newOutdoor = manualOutdoor;
      if (type === 'indoor') { newIndoor = value; setManualIndoor(value); }
      else { newOutdoor = value; setManualOutdoor(value); }

      try {
        await fetch(`${BACKEND}/api/environment`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ indoor_temp: newIndoor, outdoor_temp: newOutdoor }),
        });
      } catch (e) {
        console.error('Failed to update backend environment', e);
      }
    },
    [manualIndoor, manualOutdoor]
  );

  const handleOverrideToggle = async () => {
    const newAIActive = !isAIActive;
    setOverrideLoading(true);
    try {
      const res = await fetch(`${BACKEND}/api/override`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ active: !newAIActive }),
      });
      if (res.ok) {
        setIsAIActive(newAIActive);
      } else {
        console.error('Override update rejected by backend');
      }
    } catch (e) {
      console.error('Failed to post override state', e);
    } finally {
      setOverrideLoading(false);
    }
  };

  const latestRecord = telemetryHistory.length > 0
    ? telemetryHistory[telemetryHistory.length - 1]
    : null;

  const latencyMs = latestRecord?.latency_ms;

  const formatTime = (timeStr: string) => {
    if (!timeStr) return '';
    return new Date(timeStr).toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-8 font-sans">
      {/* Header with Heartbeat */}
      <header className="mb-8 border-b border-slate-800 pb-4 flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight text-white flex items-center gap-3">
          <Activity className="w-8 h-8 text-blue-500" />
          EcoRetrofit Edge BMS
        </h1>
        <div className="flex items-center gap-3">
          {/* Inference Latency Badge */}
          {latencyMs != null && (
            <div className="flex items-center gap-2 bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5">
              <Cpu className="w-4 h-4 text-violet-400" />
              <span className="text-xs font-mono text-violet-300">
                Inference: {latencyMs.toFixed(1)}ms
              </span>
            </div>
          )}
          {/* Edge Node Heartbeat */}
          <div className="flex items-center gap-2 bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5">
            <div className="relative flex items-center justify-center">
              <span
                className={`absolute inline-flex h-3 w-3 rounded-full opacity-75 ${
                  edgeConnected ? 'bg-emerald-400 animate-ping' : 'bg-red-500'
                }`}
              />
              <span
                className={`relative inline-flex h-3 w-3 rounded-full ${
                  edgeConnected ? 'bg-emerald-400' : 'bg-red-500'
                }`}
              />
            </div>
            <span className={`text-xs font-medium ${edgeConnected ? 'text-emerald-300' : 'text-red-400'}`}>
              {edgeConnected ? 'Edge Node: Connected' : 'Edge Node: Disconnected'}
            </span>
          </div>
        </div>
      </header>

      {/* Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-lg flex items-center gap-4">
          <div className="p-4 bg-slate-800 rounded-lg text-blue-400">
            <Thermometer className="w-8 h-8" />
          </div>
          <div>
            <p className="text-sm text-slate-400 font-medium">Indoor Temp</p>
            <p className="text-3xl font-bold text-white mt-1">
              {latestRecord?.indoor_temp != null
                ? `${latestRecord.indoor_temp.toFixed(1)}°C`
                : '--°C'}
            </p>
          </div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-lg flex items-center gap-4">
          <div className="p-4 bg-slate-800 rounded-lg text-emerald-400">
            <DollarSign className="w-8 h-8" />
          </div>
          <div>
            <p className="text-sm text-slate-400 font-medium">CAD Saved (Daily)</p>
            <p className="text-3xl font-bold text-white mt-1">
              {savings != null ? `$${savings.cad_saved.toFixed(2)}` : '--'}
            </p>
          </div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-lg flex items-center gap-4">
          <div className="p-4 bg-slate-800 rounded-lg text-amber-400">
            <Zap className="w-8 h-8" />
          </div>
          <div>
            <p className="text-sm text-slate-400 font-medium">Projected Load</p>
            <p className="text-3xl font-bold text-white mt-1">
              {projectedEnergy != null ? `${projectedEnergy.toFixed(2)} kWh` : '-- kWh'}
            </p>
          </div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-lg flex items-center gap-4">
          <div className={`p-4 rounded-lg bg-slate-800 ${isAIActive ? 'text-emerald-400' : 'text-amber-400'}`}>
            <Power className="w-8 h-8" />
          </div>
          <div>
            <p className="text-sm text-slate-400 font-medium">System Status</p>
            <p className={`text-2xl font-bold mt-1 ${isAIActive ? 'text-emerald-400' : 'text-amber-400'}`}>
              {isAIActive ? 'AI Active' : 'Manual'}
            </p>
          </div>
        </div>
      </div>

      {/* AI Insights + Controls */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-8">
        {/* Live AI Insights */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-lg">
          <h3 className="text-lg font-semibold text-slate-200 mb-3 flex items-center gap-2">
            <Brain className="w-5 h-5 text-violet-400" />
            Live AI Insights
          </h3>
          <p className="text-sm text-slate-300 leading-relaxed">
            {aiReasoning}
          </p>
        </div>

        {/* Simulation Controls */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-lg">
          <h3 className="text-lg font-semibold text-slate-200 mb-4">Simulation Controls</h3>
          <div className="space-y-6">
            <div>
              <label className="flex justify-between text-sm font-medium text-slate-300 mb-2">
                <span>Indoor Temp Overlay</span>
                <span>{manualIndoor.toFixed(1)}°C</span>
              </label>
              <input
                type="range" min="10" max="35" step="0.5" value={manualIndoor}
                onChange={(e) => handleEnvironmentChange('indoor', parseFloat(e.target.value))}
                className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
              />
            </div>
            <div>
              <label className="flex justify-between text-sm font-medium text-slate-300 mb-2">
                <span>Outdoor Temp Overlay</span>
                <span>{manualOutdoor.toFixed(1)}°C</span>
              </label>
              <input
                type="range" min="-10" max="40" step="0.5" value={manualOutdoor}
                onChange={(e) => handleEnvironmentChange('outdoor', parseFloat(e.target.value))}
                className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
              />
            </div>
          </div>
        </div>

        {/* BACnet Control Panel */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-lg flex flex-col justify-center items-center">
          <h3 className="text-lg font-semibold text-slate-200">BACnet Control Panel</h3>
          <p className="text-sm text-slate-400 mt-1 mb-8">
            {isAIActive
              ? 'AI is actively writing setpoints to the BACnet network.'
              : 'Manual override engaged -- BACnet writes are paused.'}
          </p>
          <button
            onClick={handleOverrideToggle}
            disabled={overrideLoading}
            className={`px-8 py-4 rounded-xl font-bold transition-all w-full max-w-sm disabled:opacity-50 disabled:cursor-not-allowed ${
              isAIActive
                ? 'bg-amber-500 hover:bg-amber-600 text-amber-950'
                : 'bg-emerald-500 hover:bg-emerald-600 text-emerald-950'
            }`}
          >
            {overrideLoading
              ? 'Updating...'
              : isAIActive
              ? 'Engage Manual Override'
              : 'Re-engage AI Control Layer'}
          </button>
        </div>
      </div>

      {/* Chart */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-lg">
        <h2 className="text-xl font-semibold mb-6 text-slate-200">Thermal Control Profile</h2>
        <div className="h-[400px] w-full">
          {mounted ? (
            <ResponsiveContainer width="100%" height={400}>
              <LineChart
                data={telemetryHistory}
                margin={{ top: 5, right: 20, left: -20, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                <XAxis
                  dataKey="time"
                  stroke="#94a3b8"
                  tickFormatter={formatTime}
                  tick={{ fill: '#94a3b8', fontSize: 12 }}
                  dy={10}
                />
                <YAxis
                  stroke="#94a3b8"
                  domain={[10, 32]}
                  tick={{ fill: '#94a3b8', fontSize: 12 }}
                  dx={-10}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#0f172a',
                    borderColor: '#334155',
                    borderRadius: '8px',
                  }}
                  labelFormatter={formatTime}
                />
                <Line
                  type="monotone"
                  dataKey="indoor_temp"
                  name="Indoor Temp"
                  stroke="#f8fafc"
                  strokeWidth={3}
                  dot={false}
                  isAnimationActive={false}
                />
                <Line
                  type="stepAfter"
                  dataKey="heating_setpoint"
                  name="Heating Set"
                  stroke="#ef4444"
                  strokeWidth={2}
                  dot={false}
                  isAnimationActive={false}
                />
                <Line
                  type="stepAfter"
                  dataKey="cooling_setpoint"
                  name="Cooling Set"
                  stroke="#3b82f6"
                  strokeWidth={2}
                  dot={false}
                  isAnimationActive={false}
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="w-full h-full bg-slate-800/50 animate-pulse rounded-lg flex items-center justify-center">
              <p className="text-slate-500">Initializing Chart...</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}