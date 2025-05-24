
import React from 'react';
import { OpossumState } from '../types';
import { MAX_HUNGER, MAX_FEAR, MAX_ENERGY } from '../constants';

interface StateDisplayProps {
  opossumState: OpossumState;
}

const ProgressBar: React.FC<{ value: number; max: number; color: string; label: string }> = ({ value, max, color, label }) => {
  const percentage = (value / max) * 100;
  return (
    <div className="mb-3">
      <div className="flex justify-between mb-1">
        <span className="text-sm font-medium text-gray-300">{label}</span>
        <span className="text-sm font-medium text-gray-400">{value.toFixed(1)} / {max}</span>
      </div>
      <div className="w-full bg-gray-700 rounded-full h-2.5">
        <div
          className={`h-2.5 rounded-full transition-all duration-300 ease-out ${color}`}
          style={{ width: `${percentage}%` }}
        ></div>
      </div>
    </div>
  );
};


const StateDisplay: React.FC<StateDisplayProps> = ({ opossumState }) => {
  return (
    <div className="p-4 bg-gray-800 rounded-lg shadow-xl border border-gray-700 h-full">
      <h3 className="text-xl font-semibold mb-4 text-teal-400 border-b border-gray-700 pb-2">Opossum Vitals</h3>
      <ProgressBar value={MAX_ENERGY - opossumState.energy} max={MAX_ENERGY} color="bg-green-500" label="Energy" />
      <ProgressBar value={opossumState.hunger} max={MAX_HUNGER} color="bg-yellow-500" label="Hunger" />
      <ProgressBar value={opossumState.fear} max={MAX_FEAR} color="bg-red-500" label="Fear" />
      
      <div className="mt-4 pt-3 border-t border-gray-700">
        <h4 className="text-md font-semibold text-teal-400 mb-1">Memory:</h4>
        <p className="text-sm text-gray-300 italic bg-gray-700 p-2 rounded-md h-20 overflow-y-auto">
          {opossumState.memory}
        </p>
      </div>
    </div>
  );
};

export default StateDisplay;
