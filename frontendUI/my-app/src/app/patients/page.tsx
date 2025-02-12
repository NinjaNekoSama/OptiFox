import React from "react";
import PatientDetail from "@/components/PatientDetail";

// Function to fetch the list of current patients from the API
async function fetchPatients() {
  const res = await fetch(
    `http://0.0.0.0:3000/api/v1/current-patients/2157-11-20%2019:18:02`
  );
  if (!res.ok) {
    throw new Error("Failed to fetch data"); // Handle error if the fetch fails
  }
  const data = await res.json();
  return data;
}

const PatientsPage = async () => {
  // Fetch patients' data before rendering the component
  const patients = await fetchPatients();

  return (
    <div>
      <div className="relative overflow-x-auto">
        {/* Render the patient details using the fetched data */}
        <PatientDetail patients={patients} />
      </div>
    </div>
  );
};

export default PatientsPage;
