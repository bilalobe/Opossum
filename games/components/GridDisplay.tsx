import React from 'react';
import { Grid, CellType, OpossumPosition, Trail } from '../types';
import { CELL_REPRESENTATION, CELL_COLORS, TRAIL_VISUALS, TRAIL_DESCRIPTIONS, CELL_DESCRIPTIONS } from '../constants';

interface GridDisplayProps {
  grid: Grid;
  opossumPosition: OpossumPosition;
  opossum2Position?: OpossumPosition | null;
}

const GridDisplay: React.FC<GridDisplayProps> = ({ grid, opossumPosition, opossum2Position }) => {
  return (
    <div className="p-4 bg-gray-800 rounded-lg shadow-xl border border-gray-700">
      <div
        className="grid gap-1"
        style={{
          gridTemplateColumns: `repeat(${grid[0]?.length || 0}, minmax(0, 1fr))`,
        }}
      >
        {grid.map((row, y) =>
          row.map((cell, x) => {
            let displayType = cell.type;
            let baseTitleText = `Cell (${x}, ${y}): `;
            let cellChar = CELL_REPRESENTATION[displayType];
            let cellColor = CELL_COLORS[displayType];
            let borderClasses = "border-2 border-transparent"; // Default no trail border

            const isOpossumHere = opossumPosition.x === x && opossumPosition.y === y;
            const isOpossum2Here = opossum2Position && opossum2Position.x === x && opossum2Position.y === y;

            if (isOpossumHere) {
              displayType = CellType.Opossum;
              cellChar = CELL_REPRESENTATION[CellType.Opossum];
              cellColor = CELL_COLORS[CellType.Opossum];
              baseTitleText += `You (O₁) are here.`;
            } else if (isOpossum2Here) {
              displayType = CellType.Opossum2;
              cellChar = CELL_REPRESENTATION[CellType.Opossum2];
              cellColor = CELL_COLORS[CellType.Opossum2];
              baseTitleText += `NPC Opossum (O₂) is here.`;
            } else {
               baseTitleText += CELL_DESCRIPTIONS[displayType] || displayType;
            }

            if (cell.type === CellType.Food) {
              const quality = cell.foodQuality || 0;
              if (quality < 50) {
                cellColor = "bg-yellow-700 hover:bg-yellow-600"; // Dull color for low quality
              } else if (quality < 80) {
                cellColor = "bg-yellow-600 hover:bg-yellow-500"; // Slightly dull
              }
              baseTitleText += ` (Quality: ${quality}%)`;
            }
            
            if (cell.trail) {
              const trailStyle = TRAIL_VISUALS[cell.trail.type]?.[cell.trail.intensity];
              if (trailStyle) {
                borderClasses = `border-2 ${trailStyle}`;
              }
              baseTitleText += `. Trail: ${TRAIL_DESCRIPTIONS[cell.trail.type](cell.trail.intensity, cell.trail.source)}. Decays in ${cell.trail.decayIn} turns.`;
            }


            return (
              <div
                key={cell.id}
                className={`w-full aspect-square flex items-center justify-center text-xl md:text-2xl font-bold rounded-sm transition-colors duration-150 ${cellColor} ${borderClasses}`}
                title={baseTitleText}
              >
                {cellChar}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};

export default GridDisplay;