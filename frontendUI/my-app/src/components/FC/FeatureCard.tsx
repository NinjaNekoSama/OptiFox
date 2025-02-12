import React from "react";
import Accordion from "./Accordion";

// Define the props interface for the FeatureCard component
interface FeatureCardProps {
  featureDetails: Record<string, Record<string, number | null>>; // Data for the accordion
  stay_id: number; // Identifier for the patient's stay
}

// FeatureCard component displays an accordion of feature details
const FeatureCard: React.FC<FeatureCardProps> = ({
  featureDetails,
  stay_id,
}) => {
  return (
    // Container with full height and scrollable content
    <div style={{ height: "100%", overflow: "auto" }}>
      {/* Render the Accordion component with the provided feature details */}
      <Accordion details={featureDetails} />
    </div>
  );
};

export default FeatureCard;
