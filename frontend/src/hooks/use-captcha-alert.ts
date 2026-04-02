import { useEffect, useRef } from "react";
import {
  sendCaptchaNotification,
  requestNotificationPermission,
} from "@/lib/send-notification";

export function useCaptchaAlert(hasCaptcha: boolean) {
  const prevRef = useRef(false);
  const permissionRequested = useRef(false);

  // Request notification permission once on mount
  useEffect(() => {
    if (!permissionRequested.current) {
      permissionRequested.current = true;
      requestNotificationPermission();
    }
  }, []);

  // Detect false→true transition and fire notification
  useEffect(() => {
    const isNewCaptcha = !prevRef.current && hasCaptcha;
    prevRef.current = hasCaptcha;

    if (isNewCaptcha) {
      sendCaptchaNotification();
    }
  }, [hasCaptcha]);

  return { showModal: hasCaptcha };
}
