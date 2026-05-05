"use client";

import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Menu, X } from "lucide-react";

const navLinks = [
  { label: "Features", href: "#features" },
  { label: "How It Works", href: "#how-it-works" },
  { label: "Integrations", href: "#integrations" },
  { label: "Architecture", href: "#architecture" },
];

export default function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 50);
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  return (
    <>
      <motion.nav
        initial={{ y: -100, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.8, ease: [0.23, 1, 0.32, 1] }}
        className="fixed top-0 left-0 right-0 z-100 flex justify-center xl:pt-4 xl:px-4"
      >
        <div
          className={`w-full max-w-5xl transition-all duration-500 xl:rounded-2xl border ${
            scrolled
              ? "bg-[#0a0a0b]/90 backdrop-blur-2xl border-white/8 shadow-[0_8px_32px_rgba(0,0,0,0.4)]"
              : "bg-transparent border-transparent"
          }`}
        >
          <div className="px-4 xl:px-6 h-14 flex items-center justify-between">
            <a href="/" className="text-lg font-bold text-white tracking-tight">
              NUMA
            </a>

            {/* Desktop links */}
            <div className="hidden xl:flex items-center gap-1">
              {navLinks.map((link) => (
                <a
                  key={link.label}
                  href={link.href}
                  className="text-[13px] text-gray-400 hover:text-white transition-colors px-3.5 py-1.5 rounded-lg hover:bg-white/6"
                >
                  {link.label}
                </a>
              ))}
              <div className="ml-3">
                <a href="/auth">
                  <Button
                    size="sm"
                    className="bg-white text-black hover:bg-gray-100 font-semibold rounded-lg text-[13px] h-8 px-4 shadow-[0_0_16px_rgba(255,255,255,0.1)]"
                  >
                    Sign In
                  </Button>
                </a>
              </div>
            </div>

            {/* Hamburger - shown below xl (1280px) */}
            <button
              className="xl:hidden text-white p-1"
              onClick={() => setMobileOpen(!mobileOpen)}
            >
              {mobileOpen ? (
                <X className="h-5 w-5" />
              ) : (
                <Menu className="h-5 w-5" />
              )}
            </button>
          </div>
        </div>
      </motion.nav>

      {/* Mobile menu */}
      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 z-200 bg-[#0a0a0b]/95 backdrop-blur-2xl"
          >
            {/* Header strip - same height as navbar */}
            <div className="flex items-center justify-between px-4 h-14 border-b border-white/6">
              <span className="text-lg font-bold text-white tracking-tight">NUMA</span>
              <button
                className="text-white p-1"
                onClick={() => setMobileOpen(false)}
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <motion.div
              initial={{ y: 16, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              exit={{ y: 16, opacity: 0 }}
              transition={{ delay: 0.05, duration: 0.3, ease: [0.23, 1, 0.32, 1] }}
              className="flex flex-col px-6 pt-0"
            >
              {navLinks.map((link, i) => (
                <motion.a
                  key={link.label}
                  href={link.href}
                  onClick={() => setMobileOpen(false)}
                  initial={{ x: -16, opacity: 0 }}
                  animate={{ x: 0, opacity: 1 }}
                  transition={{ delay: 0.1 + i * 0.05 }}
                  className="text-xl font-medium text-white py-4 border-b border-white/6 last:border-0"
                >
                  {link.label}
                </motion.a>
              ))}
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.35 }}
                className="mt-6"
              >
                <a href="/auth" className="w-full">
                  <Button
                    className="bg-white text-black hover:bg-gray-100 font-semibold rounded-xl w-full py-5 text-base"
                    onClick={() => setMobileOpen(false)}
                  >
                    Sign In
                  </Button>
                </a>
              </motion.div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
