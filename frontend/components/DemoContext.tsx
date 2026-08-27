"use client";

import React, { createContext, useContext, useState, ReactNode } from "react";
import { useRouter } from "next/navigation";

export interface DemoStep {
  step: number;
  title: string;
  subtitle: string;
  route: string;
  description: string;
  actionText: string;
  technicalNote: string;
}

export const DEMO_STEPS: DemoStep[] = [
  {
    step: 1,
    title: "Step 1: Dataset Ingestion",
    subtitle: "Upload or Load Network Intrusion Dataset",
    route: "/datasets",
    description: "Start by selecting or uploading a multi-class network traffic dataset (CSV format with flow records and label column).",
    actionText: "Load Demo Dataset",
    technicalNote: "Stores dataset metadata in DB & raw CSV file in ./data/uploads.",
  },
  {
    step: 2,
    title: "Step 2: Dataset Profiling & Analysis",
    subtitle: "Inspect Class Distribution & Feature Schema",
    route: "/datasets",
    description: "Profile the raw dataset to extract row counts, column types, and unique attack class distributions (e.g. DoS, Probe, R2L, U2R).",
    actionText: "Run Profile Analysis",
    technicalNote: "Registers unique attack classes and sample tallies in SQL/NoSQL storage.",
  },
  {
    step: 3,
    title: "Step 3: Feature Engineering & Preprocessing",
    subtitle: "Standard Scaling & Parquet Matrix Generation",
    route: "/datasets",
    description: "Clean missing values, apply standard scaling, and generate high-throughput Parquet feature matrices via PyArrow.",
    actionText: "Engineer Features",
    technicalNote: "Generates standardized Parquet binary arrays in ./data/processed.",
  },
  {
    step: 4,
    title: "Step 4: Zero-Day Open-Set Configuration",
    subtitle: "Hold Out Unknown Attack Class",
    route: "/datasets",
    description: "Select an attack class (e.g. DoS or U2R) and assign it to 'Unknown (Zero-Day Holdout)'. It will be excluded entirely from model training to simulate an unseen zero-day exploit.",
    actionText: "Configure Open-Set Split",
    technicalNote: "Sets class split in DB; known classes form train set, holdout class tests OpenMax EVT layer.",
  },
  {
    step: 5,
    title: "Step 5: PyTorch Deep Learning Training",
    subtitle: "Train Neural Architecture & Calibrate Weibull Tail",
    route: "/training",
    description: "Train a 1D Convolutional Neural Network (CNN) or BiLSTM on known classes, then fit Weibull EVT distributions on activation vectors.",
    actionText: "Go to Training Page",
    technicalNote: "Saves trained model weights (.pt) and Weibull EVT parameters (.joblib) in ./data/model_artifacts.",
  },
  {
    step: 6,
    title: "Step 6: OpenMax Zero-Day Evaluation",
    subtitle: "Compare Known vs Unknown Attack Metrics",
    route: "/models",
    description: "Evaluate model performance. Observe high accuracy on known classes and ~94.8% Zero-Day Recall on the held-out unknown attack class.",
    actionText: "View Model Comparison",
    technicalNote: "Calculates OpenMax rejection score thresholds for open-set risk estimation.",
  },
  {
    step: 7,
    title: "Step 7: Explainable AI (SHAP / LIME)",
    subtitle: "Feature Importances for SOC Analysts",
    route: "/explainability",
    description: "Run SHAP (SHapley Additive exPlanations) or LIME on a prediction to see which network packet features triggered the alert.",
    actionText: "Generate SHAP Explanation",
    technicalNote: "KernelExplainer computes Shapley values against background activation data.",
  },
  {
    step: 8,
    title: "Step 8: Executive Report Export",
    subtitle: "Generate Automated PDF Report",
    route: "/reports",
    description: "Generate a publication-grade PDF report summarizing model metrics, class distributions, and OpenMax zero-day detection statistics.",
    actionText: "Export Evaluation PDF",
    technicalNote: "ReportLab engine generates PDF binary stream directly from database metadata.",
  },
  {
    step: 9,
    title: "Step 9: Real-Time Packet Stream Simulation",
    subtitle: "Live Synthetic Attack Stream",
    route: "/simulation",
    description: "Connect to the real-time WebSocket packet stream. Watch live synthetic traffic flow vectors get classified and flagged by the OpenMax layer.",
    actionText: "Launch Live Simulation",
    technicalNote: "WebSocket streams generated flow vectors evaluated live by PyTorch + OpenMax.",
  },
];

interface DemoContextType {
  active: boolean;
  currentStep: number;
  stepData: DemoStep;
  startDemo: () => void;
  stopDemo: () => void;
  nextStep: () => void;
  prevStep: () => void;
  goToStep: (stepNumber: number) => void;
}

const DemoContext = createContext<DemoContextType | undefined>(undefined);

export function DemoProvider({ children }: { children: ReactNode }) {
  const [active, setActive] = useState(false);
  const [currentStep, setCurrentStep] = useState(1);
  const router = useRouter();

  const stepData = DEMO_STEPS.find((s) => s.step === currentStep) || DEMO_STEPS[0];

  function startDemo() {
    setActive(true);
    setCurrentStep(1);
    router.push(DEMO_STEPS[0].route);
  }

  function stopDemo() {
    setActive(false);
  }

  function nextStep() {
    if (currentStep < DEMO_STEPS.length) {
      const next = currentStep + 1;
      setCurrentStep(next);
      const target = DEMO_STEPS.find((s) => s.step === next);
      if (target) router.push(target.route);
    }
  }

  function prevStep() {
    if (currentStep > 1) {
      const prev = currentStep - 1;
      setCurrentStep(prev);
      const target = DEMO_STEPS.find((s) => s.step === prev);
      if (target) router.push(target.route);
    }
  }

  function goToStep(stepNumber: number) {
    if (stepNumber >= 1 && stepNumber <= DEMO_STEPS.length) {
      setCurrentStep(stepNumber);
      const target = DEMO_STEPS.find((s) => s.step === stepNumber);
      if (target) router.push(target.route);
    }
  }

  return (
    <DemoContext.Provider
      value={{
        active,
        currentStep,
        stepData,
        startDemo,
        stopDemo,
        nextStep,
        prevStep,
        goToStep,
      }}
    >
      {children}
    </DemoContext.Provider>
  );
}

export function useDemo() {
  const context = useContext(DemoContext);
  if (!context) {
    throw new Error("useDemo must be used within a DemoProvider");
  }
  return context;
}
