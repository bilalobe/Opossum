
import React from 'react';

interface FactModalProps {
  fact: string;
  onClose: () => void;
  onNewFact: () => void;
}

const FactModal: React.FC<FactModalProps> = ({ fact, onClose, onNewFact }) => {
  // Handle Escape key press
  React.useEffect(() => {
    const handleEsc = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose();
      }
    };
    window.addEventListener('keydown', handleEsc);
    return () => {
      window.removeEventListener('keydown', handleEsc);
    };
  }, [onClose]);

  return (
    <div 
      className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center p-4 z-50 transition-opacity duration-300 ease-in-out"
      onClick={onClose} // Close on overlay click
      role="dialog"
      aria-modal="true"
      aria-labelledby="factModalTitle"
    >
      <div 
        className="bg-gray-800 p-6 rounded-lg shadow-2xl max-w-md w-full border border-teal-500 transform transition-all duration-300 ease-in-out scale-95 opacity-0 animate-modalshow"
        onClick={(e) => e.stopPropagation()} // Prevent closing when clicking inside modal content
      >
        <div className="flex justify-between items-center mb-4">
          <h2 id="factModalTitle" className="text-2xl font-bold text-teal-400">Opossum Wisdom 💡</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-200 text-2xl leading-none"
            aria-label="Close fact modal"
          >
            &times;
          </button>
        </div>
        <p className="text-gray-200 mb-6 text-lg leading-relaxed">
          {fact}
        </p>
        <div className="flex flex-col sm:flex-row gap-3">
          <button
            onClick={onNewFact}
            className="flex-1 bg-sky-600 hover:bg-sky-500 text-white font-semibold py-2 px-4 rounded-lg shadow-md transition-colors duration-150"
          >
            Show Another Fact
          </button>
          <button
            onClick={onClose}
            className="flex-1 bg-red-600 hover:bg-red-500 text-white font-semibold py-2 px-4 rounded-lg shadow-md transition-colors duration-150"
          >
            Close
          </button>
        </div>
      </div>
      {/* Fix: Removed non-standard 'jsx' and 'global' attributes from the <style> tag to resolve TypeScript error. The styles effectively remain global. */}
      <style>
        {`
        @keyframes modalshow {
          from {
            opacity: 0;
            transform: scale(0.95) translateY(-20px);
          }
          to {
            opacity: 1;
            transform: scale(1) translateY(0);
          }
        }
        .animate-modalshow {
          animation: modalshow 0.3s ease-out forwards;
        }
      `}
      </style>
    </div>
  );
};

export default FactModal;
