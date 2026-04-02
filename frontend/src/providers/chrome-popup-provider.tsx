"use client";

import { createContext, useCallback, useEffect, useRef, useState } from "react";
import { ChromePopup } from "@/components/chrome/chrome-popup";
import { useVncStatus } from "@/hooks/use-vnc-status";
import { useScraperStatus } from "@/hooks/use-scraper-status";
import { useSessionStatus } from "@/hooks/use-session-status";
import {
  sendCaptchaNotification,
  requestNotificationPermission,
} from "@/lib/send-notification";

interface ChromePopupContextType {
  open: boolean;
  setOpen: (open: boolean) => void;
  vncAvailable: boolean;
}

export const ChromePopupContext = createContext<ChromePopupContextType | null>(
  null
);

export function ChromePopupProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const { vncAvailable, wsPort } = useVncStatus();
  const { hasCaptcha } = useScraperStatus();
  const { isRenewing } = useSessionStatus();
  const prevCaptcha = useRef(false);
  const permissionRequested = useRef(false);

  // Request notification permission once
  useEffect(() => {
    if (!permissionRequested.current) {
      permissionRequested.current = true;
      requestNotificationPermission();
    }
  }, []);

  // Captcha notification on false→true transition
  useEffect(() => {
    if (!prevCaptcha.current && hasCaptcha) {
      sendCaptchaNotification();
    }
    prevCaptcha.current = hasCaptcha;
  }, [hasCaptcha]);

  // Auto-open when captcha detected or session renewing
  useEffect(() => {
    if ((hasCaptcha || isRenewing) && vncAvailable && wsPort) {
      setOpen(true);
    }
  }, [hasCaptcha, isRenewing, vncAvailable, wsPort]);

  // Auto-close when captcha resolved AND not renewing
  useEffect(() => {
    if (!hasCaptcha && !isRenewing && open) {
      setOpen(false);
    }
  }, [hasCaptcha, isRenewing, open]);

  const handleOpenChange = useCallback((next: boolean) => {
    setOpen(next);
  }, []);

  return (
    <ChromePopupContext.Provider
      value={{ open, setOpen: handleOpenChange, vncAvailable }}
    >
      {children}
      {vncAvailable && wsPort && (
        <ChromePopup open={open} onOpenChange={handleOpenChange} wsPort={wsPort} />
      )}
    </ChromePopupContext.Provider>
  );
}
