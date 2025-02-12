"use client";

import React, { createContext, useState, useContext } from 'react';

const PatientContext = createContext<any>(null);

export const usePatientContext = () => useContext(PatientContext);

export const PatientProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [patientInfo, setPatientInfo] = useState<any>(null);
  
  return (
    <PatientContext.Provider value={{ patientInfo, setPatientInfo }}>
      {children}
    </PatientContext.Provider>
  );
};
