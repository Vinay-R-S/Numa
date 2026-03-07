"use client";

import React from "react";

const footerLinks = {
  Product: ["Features", "Integrations", "Architecture", "Pricing"],
  Resources: ["Documentation", "API Reference", "Changelog", "Status"],
  Company: ["About", "Blog", "Careers", "Contact"],
  Legal: ["Privacy Policy", "Terms of Service", "Cookie Policy"],
};

export default function Footer() {
  return (
    <footer className="relative pt-16 pb-10">
      <div className="max-w-7xl mx-auto px-6">
        <div className="grid grid-cols-2 md:grid-cols-5 gap-8 mb-14">
          {/* Brand */}
          <div className="col-span-2 md:col-span-1">
            <h3 className="text-lg font-semibold text-white mb-3 tracking-tight">
              NUMA
            </h3>
            <p className="text-[13px] text-gray-500 leading-relaxed max-w-50">
              Connect all your apps. Let AI agents handle the rest.
            </p>
          </div>

          {/* Link columns */}
          {Object.entries(footerLinks).map(([category, links]) => (
            <div key={category}>
              <h4 className="text-[11px] font-semibold text-gray-400 mb-4 uppercase tracking-[0.2em]">
                {category}
              </h4>
              <ul className="space-y-2.5">
                {links.map((link) => (
                  <li key={link}>
                    <a
                      href="/under-construction"
                      className="text-[13px] text-gray-500 hover:text-white transition-colors duration-200"
                    >
                      {link}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="h-px bg-white/4 mb-8" />

        <div className="flex flex-col md:flex-row items-center justify-between gap-4">
          <p className="text-xs text-gray-600">
            &copy; {new Date().getFullYear()} NUMA. All rights reserved.
          </p>
          <div className="flex items-center gap-6">
            <a
              href="/under-construction"
              className="text-xs text-gray-600 hover:text-gray-400 transition-colors duration-200"
            >
              Privacy
            </a>
            <a
              href="/under-construction"
              className="text-xs text-gray-600 hover:text-gray-400 transition-colors duration-200"
            >
              Terms
            </a>
            <a
              href="/under-construction"
              className="text-xs text-gray-600 hover:text-gray-400 transition-colors duration-200"
            >
              Cookies
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
}
