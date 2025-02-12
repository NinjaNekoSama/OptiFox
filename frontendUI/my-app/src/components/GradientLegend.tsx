import React from "react";

const GradientLegend = () => {
  const legendGradient = `
    <linearGradient id="simpleGradient" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="hsl(120, 100%, 50%)" />   {/* Green for low risk */}
      <stop offset="100%" stop-color="hsl(0, 100%, 50%)" />   {/* Red for high risk */}
    </linearGradient>
  `;

  return (
    <div>
      <svg width="300px" height="20px">
        <defs dangerouslySetInnerHTML={{ __html: legendGradient }} />
        <rect width="100%" height="100%" fill="url(#simpleGradient)" />
      </svg>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          width: "300px",
          marginTop: "5px",
        }}
      >
        <span style={{ fontSize: "12px" }}>Low Risk</span>
        <span style={{ fontSize: "12px" }}>High Risk</span>
      </div>
    </div>
  );
};

export default GradientLegend;
