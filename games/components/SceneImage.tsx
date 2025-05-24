
import React from 'react';
import LoadingSpinner from './LoadingSpinner';

interface SceneImageProps {
  imageUrl: string | null;
  isLoading: boolean;
  actionDescription: string | null;
}

const SceneImage: React.FC<SceneImageProps> = ({ imageUrl, isLoading, actionDescription }) => {
  return (
    <div className="p-4 bg-gray-800 rounded-lg shadow-xl border border-gray-700 flex flex-col items-center justify-center h-full">
      <h3 className="text-xl font-semibold mb-3 text-teal-400 w-full text-center border-b border-gray-700 pb-2">Opossum's View</h3>
      <div className="w-full aspect-square bg-gray-700 rounded flex items-center justify-center overflow-hidden">
        {isLoading && <LoadingSpinner text="Generating scene..." />}
        {!isLoading && imageUrl && (
          <img src={imageUrl} alt={actionDescription || "Generated scene"} className="w-full h-full object-cover pixelated" />
        )}
        {!isLoading && !imageUrl && (
          <div className="text-gray-400 p-4 text-center">
            <p className="text-4xl mb-2">🎨</p>
            <p>The world unfolds with each step...</p>
            {actionDescription && <p className="mt-2 text-sm italic">Last thought: "{actionDescription}"</p>}
          </div>
        )}
      </div>
    </div>
  );
};

export default SceneImage;
