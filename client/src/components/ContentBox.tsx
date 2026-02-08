"use client";
import React from "react";

const ContentBox = () => {
  return (
    <div
      className="relative z-0 w-full bg-black text-white"
      style={{
        minHeight: "100vh",
        marginTop: "-15vh", // Pull up to overlap with the laser area
        paddingTop: "15vh", // Compensate for the negative margin
        borderTopLeftRadius: "3rem",
        borderTopRightRadius: "3rem",
        borderTop: "1px solid rgba(255, 255, 255, 0.2)",
        borderLeft: "1px solid rgba(255, 255, 255, 0.1)",
        borderRight: "1px solid rgba(255, 255, 255, 0.1)",
        boxShadow: "0 -20px 50px rgba(0,0,0,0.8)", // Shadow to blend
        backgroundImage: `
          radial-gradient(circle, rgba(255,255,255,0.1) 1px, transparent 1px)
        `,
        backgroundSize: "40px 40px",
      }}
    >
      <div className="max-w-7xl mx-auto px-6 py-12">
        <h2 className="text-4xl font-bold mb-6">Welcome to NUMA</h2>
        <p className="text-lg text-gray-400 max-w-2xl">
          Experience the next generation of digital interaction. scroll down to
          explore more.
        </p>

        {/* Placeholder content for demonstration */}
        <div className="mt-12 grid grid-cols-1 md:grid-cols-2 gap-8">
          <div className="h-64 rounded-xl border border-white/10 bg-white/5 p-6">
            <div className="h-full w-full flex items-center justify-center text-white/20">
              Content Block 1
            </div>
          </div>
          <div className="h-64 rounded-xl border border-white/10 bg-white/5 p-6">
            <div className="h-full w-full flex items-center justify-center text-white/20">
              Content Block 2
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ContentBox;
