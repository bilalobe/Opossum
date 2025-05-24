
import React from 'react';

interface ActionLogProps {
  logs: string[];
}

const ActionLog: React.FC<ActionLogProps> = ({ logs }) => {
  const logEndRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  return (
    <div className="p-4 bg-gray-800 rounded-lg shadow-xl border border-gray-700 h-full flex flex-col">
      <h3 className="text-xl font-semibold mb-3 text-teal-400 border-b border-gray-700 pb-2">Event Log</h3>
      <div className="flex-grow overflow-y-auto space-y-2 pr-2 text-sm">
        {logs.length === 0 && <p className="text-gray-400 italic">No actions yet...</p>}
        {logs.map((log, index) => (
          <p key={index} className="text-gray-300 bg-gray-700 p-2 rounded-md">
            <span className="font-semibold text-sky-400">Turn {index + 1}:</span> {log}
          </p>
        ))}
        <div ref={logEndRef} />
      </div>
    </div>
  );
};

export default ActionLog;
