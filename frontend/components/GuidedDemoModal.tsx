"use client";

import React from "react";
import { useDemo, DEMO_STEPS } from "./DemoContext";
import { Sparkles, ArrowRight, ArrowLeft, X, PlayCircle, CheckCircle2, Terminal } from "lucide-react";
import clsx from "clsx";

export function GuidedDemoModal() {
  const { active, currentStep, stepData, stopDemo, nextStep, prevStep, goToStep } = useDemo();

  if (!active) return null;

  return (
    <div className="fixed bottom-6 left-1/2 -translate-x-1/2 w-[92%] max-w-4xl z-50 animate-in fade-in slide-in-from-bottom-5 duration-300">
      <div className="rounded-2xl border border-accent-blue/30 bg-base-900/95 p-5 shadow-2xl backdrop-blur-md ring-1 ring-white/10">
        {/* Step Progress Dots */}
        <div className="flex items-center justify-between mb-4 border-b border-white/10 pb-3">
          <div className="flex items-center gap-2">
            <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-accent-blue/20 text-accent-blue font-bold text-xs border border-accent-blue/30">
              <Sparkles size={14} />
            </span>
            <div>
              <span className="text-xs font-semibold uppercase tracking-wider text-accent-cyan">
                Guided Demonstration Mode
              </span>
              <h2 className="text-sm font-semibold text-white leading-none mt-0.5">
                {stepData.title} <span className="text-slate-400 font-normal">({currentStep} of 9)</span>
              </h2>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="hidden sm:flex items-center gap-1">
              {DEMO_STEPS.map((s) => {
                const isCurrent = s.step === currentStep;
                const isPassed = s.step < currentStep;
                return (
                  <button
                    key={s.step}
                    onClick={() => goToStep(s.step)}
                    title={s.title}
                    className={clsx(
                      "h-2 rounded-full transition-all",
                      isCurrent && "w-6 bg-accent-blue shadow-glow",
                      isPassed && "w-2 bg-severity-low/80",
                      !isCurrent && !isPassed && "w-2 bg-slate-700 hover:bg-slate-500"
                    )}
                  />
                );
              })}
            </div>
            <button
              onClick={stopDemo}
              className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-white/5 transition-colors"
              title="Exit Guided Demo"
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Content Body */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-center">
          <div className="md:col-span-2 flex flex-col gap-1">
            <h3 className="text-sm font-medium text-slate-200">{stepData.subtitle}</h3>
            <p className="text-xs text-slate-300 leading-relaxed">{stepData.description}</p>
            <div className="mt-1 flex items-center gap-1.5 text-[11px] text-accent-cyan font-mono bg-base-800/80 px-2.5 py-1 rounded border border-white/5 w-fit">
              <Terminal size={12} />
              <span>{stepData.technicalNote}</span>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex flex-col gap-2 items-end justify-center border-t md:border-t-0 md:border-l border-white/10 pt-3 md:pt-0 md:pl-4">
            <div className="flex items-center gap-2 w-full justify-end">
              <button
                onClick={prevStep}
                disabled={currentStep === 1}
                className="flex items-center gap-1 px-3 py-1.5 rounded-lg border border-white/10 bg-base-800 text-xs font-medium text-slate-300 hover:bg-white/5 disabled:opacity-30"
              >
                <ArrowLeft size={14} /> Back
              </button>

              {currentStep < 9 ? (
                <button
                  onClick={nextStep}
                  className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg bg-accent-blue text-white text-xs font-semibold hover:bg-blue-500 shadow-glow transition-colors"
                >
                  Next Step <ArrowRight size={14} />
                </button>
              ) : (
                <button
                  onClick={stopDemo}
                  className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg bg-severity-low text-base-950 text-xs font-bold hover:bg-green-400 transition-colors"
                >
                  <CheckCircle2 size={14} /> Finish Demo
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
