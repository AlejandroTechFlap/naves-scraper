import { useContext } from "react";
import { ChromePopupContext } from "@/providers/chrome-popup-provider";

export function useChromePopup() {
  const ctx = useContext(ChromePopupContext);
  if (!ctx) {
    throw new Error("useChromePopup must be used within ChromePopupProvider");
  }
  return ctx;
}
