"use client";

import React from "react";
import HeroSection from "./sections/HeroSection";
import FeaturesSection from "./sections/FeaturesSection";
import HowItWorksSection from "./sections/HowItWorksSection";
import IntegrationsSection from "./sections/IntegrationsSection";
import ArchitectureSection from "./sections/ArchitectureSection";
import CTASection from "./sections/CTASection";
import Footer from "./sections/Footer";

const ContentBox = () => {
  return (
    <div
      className="relative z-0 w-full text-white"
      style={{
        backgroundColor: "#0a0a0b",
        minHeight: "100vh",
        marginTop: "-15vh",
        paddingTop: "10vh",
        borderTopLeftRadius: "3rem",
        borderTopRightRadius: "3rem",
        boxShadow: "0 -30px 80px rgba(0,0,0,0.95)",
      }}
    >
      {/* Subtle dot grid background */}
      <div
        className="absolute inset-0 pointer-events-none opacity-50"
        style={{
          backgroundImage:
            "radial-gradient(circle, rgba(255,255,255,0.04) 1px, transparent 1px)",
          backgroundSize: "48px 48px",
          borderTopLeftRadius: "3rem",
          borderTopRightRadius: "3rem",
        }}
      />

      <div className="relative z-10">
        <HeroSection />
        <FeaturesSection />
        <HowItWorksSection />
        <IntegrationsSection />
        <ArchitectureSection />
        <CTASection />
        <Footer />
      </div>
    </div>
  );
};

export default ContentBox;
