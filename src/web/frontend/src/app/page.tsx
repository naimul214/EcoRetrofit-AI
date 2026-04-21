'use client';

import React, { useState, useEffect } from 'react';
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
  Zap
} from 'lucide-react';

interface TelemetryRecord {
  time: string;
  indoor_temp: number | null;
  heating_setpoint: number | null;
  cooling_setpoint: number | null;
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
  
  const [manualIndoor, setManualIndoor] = useState<number>(21.5);
  const [manualOutdoor, setManualOutdoor] = useState<number>(15.0);

  useEffect(() => {
    const fetchEnvironment = async () => {
      try {
        const envRes = await fetch('http://localhost:8010/api/environment');
        if (envRes.ok) {
          const envData = await envRes.json();
          setManualIndoor(envData.indoor_temp);
          setManualOutdoor(envData.outdoor_temp);
        }
      } catch (error) {
        console.error('Environment fetch error:', error);
      }
    };
    
    fetchEnvironment();
  }, []);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [telemetryRes, savingsRes, energyRes] = await Promise.all([
          fetch('http://localhost:8010/api/telemetry/latest'),
          fetch('http://localhost:8010/api/savings_summary'),
          fetch('http://localhost:8010/api/energy/project')
        ]);
        
        if (telemetryRes.ok) {
          const telemetryData: TelemetryRecord[] = await telemetryRes.json();
          setTelemetryHistory(() => telemetryData.slice(-20));
        }

        if (savingsRes.ok) {
          const savingsData: SavingsSummary = await savingsRes.json();
          setSavings(savingsData);
        }

        if (energyRes.ok) {
          const energyData: EnergyProjection = await energyRes.json();
          setProjectedEnergy(energyData.projected_kwh);
        }
      } catch (error) {
        console.error('Data polling error:', error);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 2000);
    return () => clearInterval(interval);
  }, []);

  const handleEnvironmentChange = async (type: 'indoor' | 'outdoor', value: number) => {
    let newIndoor = manualIndoor;
    let newOutdoor = manualOutdoor;

    if (type === 'indoor') {
      newIndoor = value;
      setManualIndoor(value);
    } else {
      newOutdoor = value;
      setManualOutdoor(value);
    }

    try {
      await fetch('http://localhost:8010/api/environment', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          indoor_temp: newIndoor,
          outdoor_temp: newOutdoor
        })
      });
    } catch (e) {
        console.error('Failed to update backend environment', e);
    }
  };

  const latestRecord = telemetryHistory.length > 0 ? telemetryHistory[telemetryHistory.length - 1] : null;

  const formatTime = (timeStr: string) => {
    if (!timeStr) return '';
    const date = new Date(timeStr);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-8 font-sans">
      <header className="mb-8 border-b border-slate-800 pb-4">
        <h1 className="text-3xl font-bold tracking-tight text-white flex items-center gap-3">
          <Activity className="w-8 h-8 text-blue-500" />
          EcoRetrofit Edge BMS
        </h1>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-lg flex items-center gap-4">
          <div className="p-4 bg-slate-800 rounded-lg text-blue-400">
            <Thermometer className="w-8 h-8" />
          </div>
          <div>
            <p className="text-sm text-slate-400 font-medium tracking-wide">Current Indoor Temp</p>
            <p className="text-3xl font-bold text-white mt-1">
              {latestRecord?.indoor_temp != null ? `${latestRecord.indoor_temp.toFixed(1)} C` : '-- C'}
            </p>
          </div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-lg flex items-center gap-4">
          <div className="p-4 bg-slate-800 rounded-lg text-emerald-400">
            <DollarSign className="w-8 h-8" />
          </div>
          <div>
            <p className="text-sm text-slate-400 font-medium tracking-wide">CAD Saved (Daily)</p>
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
            <p className="text-sm text-slate-400 font-medium tracking-wide">Projected Hourly Load</p>
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
            <p className="text-sm text-slate-400 font-medium tracking-wide">System Status</p>
            <p className={`text-2xl font-bold mt-1 ${isAIActive ? 'text-emerald-400' : 'text-amber-400'}`}>
              {isAIActive ? 'AI Active' : 'Manual Override'}
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-8">
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-lg">
          <h3 className="text-lg font-semibold text-slate-200 mb-4">Simulation Controls</h3>
          <p className="text-sm text-slate-400 mb-6">Manually inject temperature anomalies into the simulation parameters to observe AI reaction.</p>
          
          <div className="mb-6">
            <label className="flex justify-between text-sm font-medium text-slate-300 mb-2">
              <span>Indoor Temperature Overlay</span>
              <span>{manualIndoor.toFixed(1)} C</span>
            </label>
            <input 
              type="range" 
              min="15" max="30" step="0.5" 
              value={manualIndoor}
              onChange={(e) => handleEnvironmentChange('indoor', parseFloat(e.target.value))}
              className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
            />
          </div>

          <div>
            <label className="flex justify-between text-sm font-medium text-slate-300 mb-2">
              <span>Outdoor Temperature Overlay</span>
              <span>{manualOutdoor.toFixed(1)} C</span>
            </label>
            <input 
              type="range" 
              min="-10" max="40" step="0.5" 
              value={manualOutdoor}
              onChange={(e) => handleEnvironmentChange('outdoor', parseFloat(e.target.value))}
              className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
            />
          </div>
        </div>
        
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-lg flex flex-col justify-center items-center">
            <div className="text-center">
              <h3 className="text-lg font-semibold text-slate-200">BACnet Control Panel</h3>
              <p className="text-sm text-slate-400 mt-1 mb-8">Manually take over the building management controls and disrupt the ML algorithm.</p>
            </div>
            <button
              onClick={() => setIsAIActive(!isAIActive)}
              className={`px-8 py-4 rounded-xl font-bold tracking-wide transition-colors ${
                isAIActive
                  ? 'bg-amber-500 hover:bg-amber-600 text-amber-950 w-full max-w-sm'
                  : 'bg-emerald-500 hover:bg-emerald-600 text-emerald-950 w-full max-w-sm'
              }`}
            >
              {isAIActive ? 'Engage Manual Override' : 'Re-engage AI Control Layer'}
            </button>
        </div>
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-lg">
        <h2 className="text-xl font-semibold mb-6 tracking-wide text-slate-200">Thermal Control Profile</h2>
        <div className="h-[400px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={telemetryHistory} margin={{ top: 5, right: 20, left: -20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
              <XAxis 
                dataKey="time" 
                stroke="#94a3b8" 
                tickFormatter={formatTime}
                tick={{fill: '#94a3b8', fontSize: 12}}
                dy={10}
              />
              <YAxis 
                stroke="#94a3b8" 
                domain={['auto', 'auto']}
                tick={{fill: '#94a3b8', fontSize: 12}}
                dx={-10}
              />
              <Tooltip 
                contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', color: '#f1f5f9', borderRadius: '8px' }}
                labelFormatter={formatTime}
                itemStyle={{ fontWeight: 500 }}
              />
              <Line 
                type="monotone" 
                dataKey="indoor_temp" 
                name="Indoor Temp." 
                stroke="#f8fafc" 
                strokeWidth={3}
                dot={false}
                isAnimationActive={false}
              />
              <Line 
                type="stepAfter" 
                dataKey="heating_setpoint" 
                name="Heating Setpoint" 
                stroke="#ef4444" 
                strokeWidth={2}
                dot={false}
                isAnimationActive={false}
              />
              <Line 
                type="stepAfter" 
                dataKey="cooling_setpoint" 
                name="Cooling Setpoint" 
                stroke="#3b82f6" 
                strokeWidth={2}
                dot={false}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
